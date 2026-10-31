import json

import pytest
import yaml

from services.sequence_service import SignSequenceService
from services.sign_repository import JsonSignRepository
from tools.bulk_import import atomic_json, read_json
from tools.review_assets import export_review, apply_review, main


def fixture(tmp_path):
    root = tmp_path / "signs"
    (root / "clips").mkdir(parents=True)
    clip = {"version": 1, "id": "fixture", "gloss": "FIXTURE", "kind": "dataset",
        "source": "synthetic fixture only", "licence": "synthetic-test-only", "signer": "synthetic",
        "keys": [{"t": 0, "R": {"p": [0, 0, 0]}}, {"t": 1, "R": {"p": [0, 1, 0]}}]}
    atomic_json(root / "clips/fixture.json", clip)
    atomic_json(root / "signs.json", {"FIXTURE": {"id": "fixture", "gloss": "FIXTURE", "clip": "clips/fixture.json",
        "asset_type": "dataset", "review_status": "unverified", "source": clip["source"], "licence": clip["licence"], "signer": clip["signer"]}})
    grammar = tmp_path / "rules.yaml"
    grammar.write_text(yaml.safe_dump({"version": 1, "grammar": [{"id": "synthetic", "source": "synthetic fixture, not ISL",
        "review_status": "unverified", "enabled": True, "operation": "move_category", "category": "time"}]}))
    return root, grammar


def decide(form, decision="verified"):
    return {**form, "decision": decision, "reviewer": "Synthetic fixture reviewer, not a real signer",
            "comments": "Software fixture only; not an ISL correctness claim", "evidence": "Generated test fixture"}


def test_sign_review_writes_status_comments_and_asset_hash_evidence(tmp_path):
    root, grammar = fixture(tmp_path)
    form = export_review("sign", "FIXTURE", root, grammar)
    assert form["decision"] is None and form["asset_hashes"]
    apply_review(decide(form), root, grammar)
    record = read_json(root / "signs.json")["FIXTURE"]
    assert record["review_status"] == "verified" and not record["needs_manual_review"]
    assert record["review_history"][0]["comments"] and record["review_history"][0]["asset_hashes"]
    apply_review(decide(export_review("sign", "FIXTURE", root, grammar), "rejected"), root, grammar)
    repo = JsonSignRepository(root / "signs.json")
    sequence, unknown = SignSequenceService(repo).build(["FIXTURE"])
    assert unknown == ["FIXTURE"] and sequence[0].gloss == "FS:FIXTURE"
    assert sequence[0].clip_url is None


def test_stale_asset_and_document_reviews_are_refused(tmp_path):
    root, grammar = fixture(tmp_path)
    form = decide(export_review("sign", "FIXTURE", root, grammar))
    clip = read_json(root / "clips/fixture.json"); clip["notes"] = "changed after export"
    atomic_json(root / "clips/fixture.json", clip)
    with pytest.raises(ValueError, match="Stale review"): apply_review(form, root, grammar)
    assert read_json(root / "signs.json")["FIXTURE"]["review_status"] == "unverified"
    fresh = decide(export_review("rule", "synthetic", root, grammar))
    grammar.write_text(grammar.read_text() + "\n# changed\n")
    with pytest.raises(ValueError, match="Stale review"): apply_review(fresh, root, grammar)


def test_rule_review_status_and_rejection_disable_only_target(tmp_path):
    root, grammar = fixture(tmp_path)
    apply_review(decide(export_review("rule", "synthetic", root, grammar)), root, grammar)
    rule = yaml.safe_load(grammar.read_text())["grammar"][0]
    assert rule["review_status"] == "verified" and rule["reviewer"] and rule["enabled"]
    apply_review(decide(export_review("rule", "synthetic", root, grammar), "rejected"), root, grammar)
    rule = yaml.safe_load(grammar.read_text())["grammar"][0]
    assert rule["review_status"] == "unverified" and not rule["enabled"]
    assert len(rule["review_history"]) == 2


def test_clip_review_does_not_promote_sign_and_rejection_demotes_references(tmp_path):
    root, grammar = fixture(tmp_path)
    apply_review(decide(export_review("clip", "clips/fixture.json", root, grammar)), root, grammar)
    assert read_json(root / "signs.json")["FIXTURE"]["review_status"] == "unverified"
    apply_review(decide(export_review("sign", "FIXTURE", root, grammar)), root, grammar)
    apply_review(decide(export_review("clip", "clips/fixture.json", root, grammar), "rejected"), root, grammar)
    record = read_json(root / "signs.json")["FIXTURE"]
    assert record["review_status"] == "unverified" and record["clip_review_decision"] == "rejected"
    sequence, _ = SignSequenceService(JsonSignRepository(root / "signs.json")).build(["FIXTURE"])
    assert sequence[0].clip_url is None
    with pytest.raises(ValueError, match="Referenced clip is rejected"):
        apply_review(decide(export_review("sign", "FIXTURE", root, grammar)), root, grammar)


def test_demo_and_blank_reviews_cannot_verify(tmp_path):
    root, grammar = fixture(tmp_path)
    data = read_json(root / "signs.json"); data["FIXTURE"]["asset_type"] = "demo"
    atomic_json(root / "signs.json", data)
    form = decide(export_review("sign", "FIXTURE", root, grammar))
    with pytest.raises(ValueError, match="demo"): apply_review(form, root, grammar)
    with pytest.raises(ValueError): apply_review({**form, "reviewer": " "}, root, grammar)


def test_cli_exports_without_changing_target(tmp_path):
    root, grammar = fixture(tmp_path)
    review = tmp_path / "review.json"
    before = (root / "signs.json").read_bytes()
    assert main(["export", str(review), "--kind", "sign", "--id", "FIXTURE", "--root", str(root)]) == 0
    assert review.exists() and (root / "signs.json").read_bytes() == before
    assert main(["apply", str(review), "--root", str(root)]) == 1  # no human decision


def test_alphabet_review_refuses_missing_clip(tmp_path):
    from test_alphabet import missing_manifest
    root, grammar = fixture(tmp_path)
    atomic_json(root / "alphabet/manifest.json", missing_manifest())
    with pytest.raises(ValueError): apply_review(decide(export_review("alphabet", "A", root, grammar)), root, grammar)


def test_clip_review_cannot_target_the_registry_via_parent_path(tmp_path):
    root, grammar = fixture(tmp_path)
    with pytest.raises(ValueError, match="inside clips"):
        export_review("clip", "clips/../signs.json", root, grammar)
