"""Synthetic landmark fixtures only. No MediaPipe/video dataset required in CI."""
import csv
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from models.sign import Sign
from services.sequence_service import SignSequenceService
from services.sign_repository import JsonSignRepository
from test_mediapipe_to_clip import frames, hand
from tools import bulk_import as bulk
from tools.validate_signs import validate_signs


SOURCE = "synthetic test fixture, not real ISL"


def fixture_data(both=True):
    return frames(30, lambda t: hand(t, at=(-0.3, t * 0.3, 0.4)),
                  (lambda t: hand(0.2, right=False, at=(0.3, 0, 0.4))) if both else None)


def setup_batch(tmp_path, count=1):
    manifest = tmp_path / "manifest.csv"
    rows = []
    for i in range(count):
        (tmp_path / f"fixture_{i}.json").write_text(json.dumps(fixture_data()), encoding="utf-8")
        (tmp_path / f"fixture_{i}.mp4").write_bytes(b"Synthetic video stub; not a decodable recording")
        rows.append({"gloss": f"FIXTURE_{i}", "aliases": f"fixture alias {i}", "category": "test",
            "video_path": f"fixture_{i}.mp4", "source": SOURCE, "licence": "synthetic-test-only",
            "signer": "synthetic", "landmarks_path": f"fixture_{i}.json"})
    write_rows(manifest, rows)
    permissions = tmp_path / "permissions.json"
    bulk.atomic_json(permissions, {SOURCE: {"licence": "synthetic-test-only", "intended_use": "software-tests",
        "allow_processing": True, "allow_redistribution": True, "reviewer": "test fixture author",
        "evidence": "Generated synthetic landmarks; no human recording or ISL assertion"}})
    return manifest, permissions, tmp_path / "signs", rows


def write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(batch, **options):
    manifest, permissions, output, _ = batch
    return bulk.import_manifest(manifest, output, permissions, "software-tests", **options)


def test_five_sample_imports_produce_valid_clips_metadata_and_idempotent_rerun(tmp_path):
    batch = setup_batch(tmp_path, count=5)
    summary = run(batch, copy_video=True, max_keys=12)
    assert len(summary["imported"]) == 5 and summary["errors"] == []
    database = batch[2] / "signs.json"
    assert validate_signs(database) == []
    repo = JsonSignRepository(database)
    for gloss in summary["imported"]:
        sign = repo.get_sign(gloss)
        assert sign.review_status == "unverified" and sign.source == SOURCE
        assert sign.qa.frame_count == 30 and sign.qa.key_count == 12
        assert sign.qa.both_hands_fraction == 1 and sign.qa.duration > 0
        clip = bulk.read_json(batch[2] / sign.clip)
        assert clip["version"] == 1 and clip["kind"] == "dataset" and len(clip["keys"]) == 12
        assert "R" in clip["keys"][0] and "L" in clip["keys"][0]
        assert clip["source"] == SOURCE and clip["review_status"] == "unverified"
        assert (batch[2] / sign.video).read_bytes().startswith(b"Synthetic")
        sequence, unknown = SignSequenceService(repo).build([gloss])
        assert not unknown and sequence[0].review_status == "unverified" and sequence[0].source == SOURCE
    before = database.read_bytes()
    again = run(batch, copy_video=True, max_keys=12)
    assert len(again["skipped"]) == 5 and again["imported"] == []
    assert database.read_bytes() == before


def test_verified_entry_is_protected_and_force_demotes_to_unverified(tmp_path):
    batch = setup_batch(tmp_path)
    run(batch)
    database = batch[2] / "signs.json"
    data = bulk.read_json(database)
    data["FIXTURE_0"]["review_status"] = "verified"
    bulk.atomic_json(database, data)
    before = database.read_bytes()
    assert run(batch)["protected"] == ["FIXTURE_0"]
    assert database.read_bytes() == before
    assert run(batch, force=True)["imported"] == ["FIXTURE_0"]
    assert bulk.read_json(database)["FIXTURE_0"]["review_status"] == "unverified"


@pytest.mark.parametrize("updates", [{"allow_processing": False}, {"allow_redistribution": False},
    {"intended_use": "different"}, {"licence": "different"}, {"evidence": ""}])
def test_permissions_block_processing_before_extraction_or_publication(tmp_path, updates):
    batch = setup_batch(tmp_path)
    data = bulk.read_json(batch[1])
    data[SOURCE].update(updates)
    bulk.atomic_json(batch[1], data)
    called = []
    result = run(batch, extractor=lambda path: called.append(path))
    assert result["errors"] and not called
    assert not (batch[2] / "signs.json").exists()
    assert not (batch[2] / "landmarks").exists()


def test_partial_batch_can_resume_after_failed_row_is_fixed(tmp_path):
    batch = setup_batch(tmp_path, count=2)
    broken = tmp_path / "fixture_1.json"
    broken.write_text("{}")
    first = run(batch)
    assert first["imported"] == ["FIXTURE_0"] and len(first["errors"]) == 1
    broken.write_text(json.dumps(fixture_data()))
    second = run(batch)
    assert second["skipped"] == ["FIXTURE_0"] and second["imported"] == ["FIXTURE_1"]
    assert validate_signs(batch[2] / "signs.json") == []


def test_video_extraction_is_cached_when_conversion_fails(tmp_path, monkeypatch):
    batch = setup_batch(tmp_path)
    batch[3][0]["landmarks_path"] = ""
    write_rows(batch[0], batch[3])
    calls = []
    def extractor(path):
        calls.append(path)
        return fixture_data()
    original = bulk.converter.convert
    with monkeypatch.context() as patch:
        patch.setattr(bulk.converter, "convert", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("interrupted fixture")))
        assert run(batch, extractor=extractor)["errors"]
    assert bulk.converter.convert is original
    assert run(batch, extractor=extractor)["imported"] == ["FIXTURE_0"]
    assert len(calls) == 1


def test_missing_output_is_rebuilt_and_source_changes_update_without_duplicates(tmp_path):
    batch = setup_batch(tmp_path)
    run(batch)
    db = batch[2] / "signs.json"
    old = bulk.read_json(db)["FIXTURE_0"]
    (batch[2] / old["clip"]).unlink()
    assert run(batch)["imported"] == ["FIXTURE_0"]
    data = fixture_data(both=False)
    (tmp_path / "fixture_0.json").write_text(json.dumps(data))
    assert run(batch)["imported"] == ["FIXTURE_0"]
    current = bulk.read_json(db)
    assert len(current) == 1 and current["FIXTURE_0"]["import_fingerprint"] != old["import_fingerprint"]
    assert current["FIXTURE_0"]["needs_manual_review"]
    assert current["FIXTURE_0"]["qa"]["both_hands_fraction"] == 0


def test_jitter_penalizes_noisy_input():
    clean = fixture_data()
    noisy = fixture_data()
    for i, frame in enumerate(noisy["frames"]):
        frame["right_hand"][0][0] += 0.2 if i % 2 else -0.2
    clip = bulk.converter.convert(clean, "FIXTURE", "fixture")
    clean_qa, noisy_qa = bulk.clip_qa(clean, clip), bulk.clip_qa(noisy, clip)
    assert noisy_qa.jitter > clean_qa.jitter and noisy_qa.score < clean_qa.score


def test_alias_conflicts_do_not_replace_registry(tmp_path):
    batch = setup_batch(tmp_path, count=2)
    batch[3][1]["aliases"] = batch[3][0]["aliases"]
    write_rows(batch[0], batch[3])
    result = run(batch)
    assert result["imported"] == ["FIXTURE_0"] and result["errors"]
    assert list(bulk.read_json(batch[2] / "signs.json")) == ["FIXTURE_0"]


def test_registry_change_during_extraction_is_not_overwritten(tmp_path):
    batch = setup_batch(tmp_path)
    batch[3][0]["landmarks_path"] = ""
    write_rows(batch[0], batch[3])
    database = batch[2] / "signs.json"
    def extractor(path):
        bulk.atomic_json(database, {"OTHER": {"id": "other", "gloss": "OTHER", "review_status": "verified"}})
        return fixture_data()
    result = run(batch, extractor=extractor)
    assert result["errors"] and "Database changed" in result["errors"][0]["error"]
    assert list(bulk.read_json(database)) == ["OTHER"]


def test_duplicate_gloss_and_bad_settings_are_explicit(tmp_path):
    batch = setup_batch(tmp_path, count=2)
    batch[3][1]["gloss"] = batch[3][0]["gloss"]
    write_rows(batch[0], batch[3])
    result = run(batch)
    assert len(result["imported"]) == 1 and "Duplicate gloss" in result["errors"][0]["error"]
    with pytest.raises(ValueError, match="max_keys"):
        run(batch, max_keys=1)


def test_swap_hand_option_reaches_converter(tmp_path):
    batch = setup_batch(tmp_path)
    (tmp_path / "fixture_0.json").write_text(json.dumps(fixture_data(both=False)))
    assert run(batch, swap_hands=True)["imported"] == ["FIXTURE_0"]
    entry = bulk.read_json(batch[2] / "signs.json")["FIXTURE_0"]
    clip = bulk.read_json(batch[2] / entry["clip"])
    assert "L" in clip["keys"][0] and "R" not in clip["keys"][0]


def test_cli_help_and_failure_status(tmp_path):
    batch = setup_batch(tmp_path)
    assert bulk.main([str(batch[0]), "--output", str(batch[2]), "--permissions", str(batch[1]),
                      "--intended-use", "software-tests"]) == 0
    assert bulk.main([str(batch[0]), "--output", str(batch[2]), "--permissions", str(batch[1]),
                      "--intended-use", "not-authorized"]) == 1


def test_holistic_adapter_with_stubbed_optional_modules(monkeypatch):
    fixture = fixture_data()["frames"][0]
    def landmarks(points):
        return SimpleNamespace(landmark=[SimpleNamespace(x=p[0], y=p[1], z=p[2], visibility=p[3] if len(p) > 3 else 1) for p in points])
    result = SimpleNamespace(pose_landmarks=landmarks(fixture["pose"]),
        left_hand_landmarks=landmarks(fixture["left_hand"]), right_hand_landmarks=landmarks(fixture["right_hand"]))
    class Capture:
        index = 0
        released = False
        def isOpened(self): return True
        def get(self, key): return {1: 25, 2: 100, 3: 100, 4: 2}[key]
        def read(self):
            self.index += 1
            return self.index <= 2, "image"
        def release(self): self.released = True
    capture = Capture()
    class Holistic:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def process(self, image): return result
    monkeypatch.setitem(sys.modules, "cv2", SimpleNamespace(VideoCapture=lambda path: capture,
        CAP_PROP_FPS=1, CAP_PROP_FRAME_WIDTH=2, CAP_PROP_FRAME_HEIGHT=3, CAP_PROP_FRAME_COUNT=4,
        COLOR_BGR2RGB=5, cvtColor=lambda image, flag: image))
    monkeypatch.setitem(sys.modules, "mediapipe", SimpleNamespace(solutions=SimpleNamespace(holistic=SimpleNamespace(Holistic=Holistic))))
    data = bulk.extract_video(Path("synthetic.mp4"))
    assert data["fps"] == 25 and len(data["frames"]) == 2
    assert data["frames"][0]["pose"] == fixture["pose"] and capture.released
