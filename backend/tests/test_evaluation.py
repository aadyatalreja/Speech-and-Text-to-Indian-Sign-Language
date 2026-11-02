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

spec = importlib.util.spec_from_file_location(
    "signai_eval", Path(__file__).resolve().parents[2] / "eval/run_eval.py"
)
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
    atomic_json(
        tmp_path / "signs.json",
        {
            "A": {
                "id": "a",
                "gloss": "A",
                "asset_type": "dataset",
                "clip": "fixture.json",
                "review_status": "verified",
                "source": "synthetic fixture",
                "licence": "test only",
                "signer": "synthetic",
            },
            "B": {"id": "b", "gloss": "B", "asset_type": "demo", "review_status": "verified"},
        },
    )
    rows = [
        evaluation.EvalRow(
            english="Synthetic software fixture",
            expected_gloss=["A", "B"],
            expected_nmm=[{}, {}],
            reviewer="Synthetic test fixture, not signer data",
            review_status="verified",
        ),
        evaluation.EvalRow(
            english="Ignored placeholder", review_status="unverified", placeholder=True
        ),
    ]

    async def translator(request):
        return TranslationResponse(
            original_text=request.text,
            target_sign_language="ISL",
            intent="statement",
            entities=[],
            gloss=["A", "FS:X"],
            gloss_detail=[GlossToken(gloss="A"), GlossToken(gloss="FS:X")],
            sequence=[
                SignSequenceItem(gloss="A", sign_id="a", available=True, duration=1),
                SignSequenceItem(gloss="FS:X", sign_id=None, available=False, duration=1),
            ],
            unknown_signs=["X"],
            confidence=0.1,
            engine="synthetic-test",
        )

    report = asyncio.run(
        evaluation.evaluate(rows, translator, JsonSignRepository(tmp_path / "signs.json"))
    )
    assert report["verified_rows"] == 1 and report["ignored_rows"] == 1
    assert report["gloss_exact_match"] == 0 and report["gloss_sequence_edit_distance"] == 1
    assert report["vocabulary_coverage"] == 0.5 and report["fingerspell_rate"] == 0.5
    assert report["nmm_exact_match"] == 1


def test_verified_rows_require_actual_review_content():
    with pytest.raises(ValueError):
        evaluation.EvalRow(english="TODO", review_status="verified", placeholder=True)


def test_synthetic_cli_json_markdown_and_regression_guard(tmp_path, capsys):
    output = tmp_path / "fixture.json"
    assert evaluation.main(["--fixture", "--output", str(output)]) == 0
    text = capsys.readouterr().out
    assert text.startswith("Verified rows: 1 SYNTHETIC")
    assert "not reliable" in text
    assert output.with_suffix(".md").exists()
    import json

    report = json.loads(output.read_text())
    assert report["synthetic"] is True
    assert report["gloss_word_error_rate"] == 1
    assert report["out_of_vocabulary_rate"] == 1
    assert report["per_intent"]["statement"]["rows"] == 1


def test_multiple_references_match(tmp_path):
    row = evaluation.EvalRow(
        english="fixture",
        expected_gloss=["A"],
        acceptable_alternatives=[["B"]],
        expected_nmm=[{}],
        reviewer="synthetic",
        review_status="verified",
    )

    async def translator(req):
        return TranslationResponse(
            original_text=req.text,
            target_sign_language="ISL",
            intent="statement",
            entities=[],
            gloss=["B"],
            gloss_detail=[GlossToken(gloss="B")],
            sequence=[],
            unknown_signs=[],
            confidence=0,
            engine="synthetic",
        )

    (tmp_path / "signs.json").write_text("{}")
    report = asyncio.run(
        evaluation.evaluate([row], translator, JsonSignRepository(tmp_path / "signs.json"))
    )
    assert report["gloss_exact_match"] == 1
    assert report["gloss_word_error_rate"] == 0


def test_review_sheet_round_trip_reviewer_required(tmp_path):
    import csv
    import json

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "eval/tools"))
    import make_review_sheet
    import import_review_sheet

    sentences = tmp_path / "sentences.txt"
    sentences.write_text("Hello.\nWhere?\n")
    sheet = tmp_path / "review.csv"
    make_review_sheet.main(["--sentences", str(sentences), "--output", str(sheet)])
    with sheet.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert list(rows[0]) == make_review_sheet.COLUMNS
    for row in rows:
        row["reviewed_gloss"] = "HELLO"
    rows[0]["reviewer"] = "Synthetic fixture reviewer"
    rows[0]["acceptable_alternatives"] = "HI | WELCOME"
    with sheet.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=make_review_sheet.COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    output = tmp_path / "rows.jsonl"
    import_review_sheet.main([str(sheet), "--output", str(output)])
    result = [json.loads(line) for line in output.read_text().splitlines()]
    assert [r["review_status"] for r in result] == ["verified", "unverified"]
    assert result[0]["acceptable_alternatives"] == [["HI"], ["WELCOME"]]
    rows[0]["reviewed_gloss"] = ""
    with sheet.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=make_review_sheet.COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="empty reviewed gloss"):
        import_review_sheet.convert(sheet)


@pytest.mark.parametrize("exact,wer,expected", [(0.5, 0.5, 1), (0.99, 0.01, 0)])
def test_check_tolerance(tmp_path, monkeypatch, exact, wer, expected):
    import json

    row = evaluation.EvalRow(
        english="synthetic",
        expected_gloss=["A"],
        expected_nmm=[{}],
        reviewer="synthetic",
        review_status="verified",
    )
    monkeypatch.setattr(evaluation, "load_rows", lambda path: [row])

    async def fake_evaluate(rows, translator):
        return {"verified_rows": 1, "gloss_exact_match": exact, "gloss_word_error_rate": wer}

    monkeypatch.setattr(evaluation, "evaluate", fake_evaluate)
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"gloss_exact_match": 1, "gloss_word_error_rate": 0}))
    assert (
        evaluation.main(["--check", "--baseline", str(baseline), "--tolerance", "0.02"]) == expected
    )
