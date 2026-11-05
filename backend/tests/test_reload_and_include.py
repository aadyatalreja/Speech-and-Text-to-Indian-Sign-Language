import csv
import json
import subprocess

import pytest

from config import settings
from services import sign_repository as repository
from api import assets
from tools import include_manifest as manifest
from tools import repo_stats
from tools.bulk_import import import_manifest


def test_registry_reload_retains_old_instance_and_bad_update(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(settings, "SIGN_DATA_PATH", tmp_path)
    monkeypatch.setattr(repository, "_repo", None)
    path = tmp_path / "signs.json"
    path.write_text(json.dumps({"A": {"id": "a", "gloss": "A"}}))
    old = repository.get_repository()
    path.write_text(json.dumps({"B": {"id": "b", "gloss": "B"}, "C": {"id": "c", "gloss": "C"}}))
    new = repository.get_repository()
    assert old.get_sign("A") and not old.get_sign("B")
    assert new is not old and new.get_sign("B")
    path.write_text("corrupt")
    assert repository.get_repository() is new
    assert "Cannot reload" in caplog.text


def test_alphabet_reload_and_corruption(tmp_path, monkeypatch, caplog):
    original = json.loads((settings.SIGN_DATA_PATH / "alphabet/manifest.json").read_text())
    monkeypatch.setattr(settings, "SIGN_DATA_PATH", tmp_path)
    monkeypatch.setattr(assets, "_alphabet_file", repository.ReloadingFile())
    path = tmp_path / "alphabet/manifest.json"
    path.parent.mkdir()
    path.write_text(json.dumps(original))
    old = assets.alphabet_manifest()
    original["characters"]["A"]["notes"] = "changed fixture notes"
    path.write_text(json.dumps(original))
    new = assets.alphabet_manifest()
    assert new is not old and new["characters"]["A"]["notes"] == "changed fixture notes"
    path.write_text("{}")
    assert assets.alphabet_manifest() is new
    assert "Cannot reload" in caplog.text


@pytest.fixture
def videos(tmp_path):
    imageio = pytest.importorskip("imageio_ffmpeg")
    root = tmp_path / "dataset"
    for relative in (
        "a/Good-morning/1.mp4",
        "a/Good-morning/2.mp4",
        "b/Good_morning/1.mp4",
        "b/54. Hello/1.mp4",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                imageio.get_ffmpeg_exe(),
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=blue:s=16x16:d=0.12",
                "-pix_fmt",
                "yuv420p",
                str(path),
            ],
            check=True,
            capture_output=True,
        )
    return root


def test_manifest_columns_dry_run_duplicates_permissions(videos, tmp_path, capsys):
    output = tmp_path / "manifest.csv"
    args = [
        str(videos),
        "--licence",
        "fixture",
        "--source",
        "SYNTHETIC",
        "--signer-note",
        "no signer",
        "--output",
        str(output),
    ]
    assert manifest.main(args + ["--dry-run"]) == 0
    assert not output.exists()
    assert list(csv.DictReader(capsys.readouterr().out.splitlines()).fieldnames) == manifest.COLUMNS
    manifest.main(args)
    with output.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [r["gloss"] for r in rows] == ["GOOD_MORNING", "HELLO"]
    assert rows[0]["video_path"].endswith("1.mp4")
    assert manifest.build_rows(videos, "fixture", "SYNTHETIC", "none", 1) == [
        dict(rows[0], signer="none")
    ]
    permissions = tmp_path / "permissions.json"
    permissions.write_text("{}")
    result = import_manifest(output, tmp_path / "output", permissions, "test", copy_video=True)
    assert len(result["errors"]) == 2 and not result["imported"]
    assert not (tmp_path / "output/signs.json").exists()


def test_stats_guard():
    report = repo_stats.stats(settings.SIGN_DATA_PATH)
    assert sum(report["asset_type"].values()) == report["total"]
    assert report["alphabet_present"] + report["alphabet_missing"] == 36
    repo_stats.check_readme(f"{report['total']} signs", report)
    with pytest.raises(ValueError):
        repo_stats.check_readme(f"{report['total'] + 1} signs", report)
