"""SYNTHETIC attestations only; no real signer, study or ISL results."""

import asyncio
import csv
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from eval import review_packet  # noqa: E402
from eval.ablation import run  # noqa: E402
from eval.metrics import cohen_kappa, fleiss_kappa, reviewer_agreement, content_coverage  # noqa: E402
from eval.run_eval import load_rows, evaluate  # noqa: E402
from eval.study import assign  # noqa: E402
from models.translation import TranslationResponse  # noqa: E402
from services.sign_repository import get_repository  # noqa: E402
from config import settings  # noqa: E402


def test_kappa_known_counts_and_undefined():
    assert (
        cohen_kappa([("yes", "yes"), ("yes", "yes"), ("no", "no"), ("no", "yes")])["kappa"] == 0.5
    )
    assert fleiss_kappa([["yes"] * 3, ["no"] * 3])["kappa"] == 1
    assert cohen_kappa([("yes", "yes")])["kappa"] is None
    assert fleiss_kappa([])["kappa"] is None
    with pytest.raises(ValueError):
        fleiss_kappa([["yes", "no"], ["yes", "no", "yes"]])


def test_synthetic_reviewed_fixture_metrics_and_gate():
    rows = load_rows(Path(__file__).parent / "fixtures/metrics_reviewed.synthetic.jsonl")
    report = asyncio.run(evaluate(rows))
    assert report["gloss_word_error_rate"] == 0 and report["gloss_token_accuracy"] == 1
    assert report["content_word_coverage"] == 0.75
    assert "not comprehension accuracy" in report["limitations"]
    agreement = reviewer_agreement(rows)
    assert agreement["gloss_acceptable"]["pairwise_cohen"][0]["kappa"] == 1
    rows[0].review_status = "unverified"
    assert reviewer_agreement(rows)["gloss_acceptable"]["pairwise_cohen"][0]["kappa"] is None
    with pytest.raises(ValueError, match="NO_VERIFIED_ROWS"):
        asyncio.run(evaluate([rows[0]]))
    rows[1].judgements.append(rows[1].judgements[0])
    with pytest.raises(ValueError, match="Duplicate"):
        reviewer_agreement(rows)


def test_content_coverage_counts_source_occurrences_and_partial_numbers():
    result = content_coverage("the water water quantum", get_repository())
    assert result["content_words"] == 3 and result["content_word_coverage"] == pytest.approx(2 / 3)


@pytest.fixture
def packet(tmp_path, monkeypatch):
    monkeypatch.setattr(review_packet, "ROOT", tmp_path)
    source = tmp_path / "source.json"
    source.write_text("{}")
    monkeypatch.setattr(
        review_packet, "snapshot_paths", lambda: {"source.json": review_packet.file_hash(source)}
    )

    async def synthetic(request):
        return TranslationResponse(
            original_text=request.text,
            english_text=request.text,
            target_sign_language="ISL",
            intent="statement",
            entities=[],
            gloss=["WATER"],
            sequence=[],
            unknown_signs=[],
            confidence=0,
            engine="SYNTHETIC",
        )

    directory = tmp_path / "packet"
    manifest = asyncio.run(
        review_packet.create_packet(["SYNTHETIC"], directory, translator=synthetic)
    )
    (directory / "frames").mkdir()
    (directory / "frames/item-001.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><text>SYNTHETIC ONLY</text></svg>'
    )
    review_packet.write_packet_html(directory)
    return directory, manifest, source


def fill(packet, **changes):
    directory, manifest, _ = packet
    path = directory / "returned.csv"
    row = {
        "item_id": "item-001",
        "stimulus_sha256": manifest["items"][0]["stimulus_sha256"],
        **changes,
    }
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=review_packet.PACKET_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    return path


def test_packet_import_requires_explicit_named_signoff_and_keeps_identity_private(packet, tmp_path):
    sheet = fill(
        packet,
        gloss_acceptable="no",
        nmm_correct="uncertain",
        comprehension="2",
        comments="SYNTHETIC only",
        decision="in_review",
    )
    output = tmp_path / "results.jsonl"
    rows = review_packet.import_packet(packet[0], sheet, output, reviewer_id="synthetic-R01")
    assert rows[0].review_status == "in_review"
    assert not rows[0].judgements[0].signed_off
    sheet = fill(
        packet, reviewed_gloss="WATER", expected_nmm="[{}]", decision="verified", signed_off="yes"
    )
    with pytest.raises(ValueError, match="Named reviewer"):
        review_packet.import_packet(packet[0], sheet, output, reviewer_id="synthetic-R02")
    rows = review_packet.import_packet(
        packet[0],
        sheet,
        output,
        reviewer="SYNTHETIC NAME",
        reviewer_id="synthetic-R02",
        evidence="PRIVATE SYNTHETIC EVIDENCE",
    )
    assert rows[0].review_status == "verified" and rows[0].review_history[-1]["signed_off"]
    assert (
        "SYNTHETIC NAME" not in output.read_text()
        and "PRIVATE SYNTHETIC EVIDENCE" not in output.read_text()
    )
    assert output.with_suffix(".identities.private.json").exists()
    with pytest.raises(ValueError, match="already rated"):
        review_packet.import_packet(
            packet[0],
            sheet,
            output,
            reviewer="SYNTHETIC NAME",
            reviewer_id="synthetic-R02",
            evidence="PRIVATE SYNTHETIC EVIDENCE",
        )


def test_packet_refuses_changed_source_frames_and_target(packet, tmp_path):
    directory, _, source = packet
    sheet = fill(packet, comments="SYNTHETIC observation")
    output = tmp_path / "results.jsonl"
    source.write_text('{"changed":true}')
    with pytest.raises(ValueError, match="Stale export"):
        review_packet.import_packet(directory, sheet, output, reviewer_id="synthetic-R01")
    source.write_text("{}")
    frame = directory / "frames/item-001.svg"
    before = frame.read_text()
    frame.write_text("changed")
    with pytest.raises(ValueError, match="Stale rendered"):
        review_packet.import_packet(directory, sheet, output, reviewer_id="synthetic-R01")
    frame.write_text(before)
    review_packet.import_packet(directory, sheet, output, reviewer_id="synthetic-R01")
    output.write_text(output.read_text() + "\n")
    with pytest.raises(ValueError, match="Stale or unbound"):
        review_packet.import_packet(directory, sheet, output, reviewer_id="synthetic-R02")


def test_packet_refuses_changed_configuration_and_unsigned_verification(
    packet, tmp_path, monkeypatch
):
    sheet = fill(packet, reviewed_gloss="WATER", expected_nmm="[{}]", decision="verified")
    with pytest.raises(ValueError, match="explicit signed_off"):
        review_packet.import_packet(
            packet[0],
            sheet,
            tmp_path / "rows.jsonl",
            reviewer="SYNTHETIC name",
            reviewer_id="synthetic-R01",
            evidence="SYNTHETIC evidence",
        )
    monkeypatch.setattr(settings, "LLM_ORDERING", "model")
    with pytest.raises(ValueError, match="configuration changed"):
        review_packet.validate_packet(packet[0])


def test_overlap_assignment_is_seeded_balanced_and_never_duplicates_a_reviewer():
    ids = [f"item-{i}" for i in range(20)]
    first = assign(ids, 12, 3, 2)
    assert first == assign(ids, 12, 3, 2)
    assert all(len(items) == len(set(items)) == 8 for items in first.values())
    counts = {}
    for items in first.values():
        for ident in items:
            counts[ident] = counts.get(ident, 0) + 1
    assert len(counts) == 12 and set(counts.values()) == {2}


def test_simulated_transport_is_labelled_offline_and_restores_configuration():
    before = settings.LLM_PROVIDER, settings.LLM_ORDERING, settings.ENABLE_SYNONYM_FALLBACK
    result = asyncio.run(
        run(
            {"en-IN": ["water quantum"], "hi-IN": ["मुझे मदद चाहिए"]},
            axes=[("simulated_api", "code", False)],
        )
    )
    assert "NOT ISL" in result["label"] and "No live model calls" in result["simulation"]
    assert len(result["cells"]) == 2
    assert result["cells"][0]["fs_rate"] == 0.5
    assert all(
        cell["metrics_status"] == "NO_VERIFIED_ROWS" and cell["verified_scores"] is None
        for cell in result["cells"]
    )
    assert before == (
        settings.LLM_PROVIDER,
        settings.LLM_ORDERING,
        settings.ENABLE_SYNONYM_FALLBACK,
    )
