import asyncio
import importlib.util
from pathlib import Path
import sys

import pytest

from config import settings
from models.markers import GlossToken
from models.sign import SignSequenceItem
from models.translation import TranslationResponse
from services.sign_repository import JsonSignRepository
from tools.bulk_import import atomic_json

spec = importlib.util.spec_from_file_location("signai_eval", Path(__file__).resolve().parents[2] / "eval/run_eval.py")
evaluation = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = evaluation
spec.loader.exec_module(evaluation)


def test_bundled_placeholder_set_refuses_to_produce_scores(tmp_path, capsys):
    output = tmp_path / "scores.json"
    assert evaluation.main(["--output", str(output)]) == 2
    assert "NO_VERIFIED_ROWS" in capsys.readouterr().err
    assert not output.exists()


def test_edit_distance_counts_sequence_changes():
    assert evaluation.edit_distance(["I", "GO"], ["I", "FS:UNKNOWN", "GO"]) == 1
    assert evaluation.edit_distance(["I", "GO"], ["GO", "I"]) == 2
    assert evaluation.edit_distance([], ["I"]) == 1


def test_metrics_on_synthetic_reviewed_fixture_only(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SIGN_DATA_PATH", tmp_path)
    (tmp_path / "fixture.json").write_text('{"version":1}')
    atomic_json(tmp_path / "signs.json", {
        "A": {"id": "a", "gloss": "A", "asset_type": "dataset", "clip": "fixture.json", "review_status": "verified",
              "source": "synthetic fixture", "licence": "test only", "signer": "synthetic"},
        "B": {"id": "b", "gloss": "B", "asset_type": "demo", "review_status": "verified"}})
    rows = [evaluation.EvalRow(english="Synthetic software fixture", expected_gloss=["A", "B"],
        expected_nmm=[{}, {}], reviewer="Synthetic test fixture, not signer data", review_status="verified"),
        evaluation.EvalRow(english="Ignored placeholder", review_status="unverified", placeholder=True)]
    async def translator(request):
        return TranslationResponse(original_text=request.text, target_sign_language="ISL", intent="statement", entities=[],
            gloss=["A", "FS:X"], gloss_detail=[GlossToken(gloss="A"), GlossToken(gloss="FS:X")],
            sequence=[SignSequenceItem(gloss="A", sign_id="a", available=True, duration=1),
                      SignSequenceItem(gloss="FS:X", sign_id=None, available=False, duration=1)],
            unknown_signs=["X"], confidence=0.1, engine="synthetic-test")
    report = asyncio.run(evaluation.evaluate(rows, translator, JsonSignRepository(tmp_path / "signs.json")))
    assert report["verified_rows"] == 1 and report["ignored_rows"] == 1
    assert report["gloss_exact_match"] == 0 and report["gloss_sequence_edit_distance"] == 1
    assert report["vocabulary_coverage"] == 0.5 and report["fingerspell_rate"] == 0.5
    assert report["nmm_exact_match"] == 1


def test_verified_rows_require_actual_review_content():
    with pytest.raises(ValueError): evaluation.EvalRow(english="TODO", review_status="verified", placeholder=True)
