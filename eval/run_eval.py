"""Offline ISL review-set evaluation. Never scores unverified/placeholder rows."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal
from models.markers import NonManualMarkers
from models.translation import TranslationRequest
from services.gloss_service import translate
from services.sign_repository import get_repository
from services.timing_service import asset_path


class EvalRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    english: str = Field(min_length=1)
    expected_gloss: list[str] = Field(default_factory=list)
    expected_nmm: list[NonManualMarkers] = Field(default_factory=list)
    reviewer: str | None = None
    review_status: Literal["unverified", "in_review", "verified"]
    placeholder: bool = False

    @model_validator(mode="after")
    def reviewed_content(self):
        if self.review_status == "verified" and (self.placeholder or not (self.reviewer or "").strip()
                or not self.expected_gloss or any(not token.strip() for token in self.expected_gloss)
                or len(self.expected_nmm) != len(self.expected_gloss)):
            raise ValueError("Verified rows require reviewer, non-placeholder gloss, and one NMM object per token")
        return self


def load_rows(path):
    return [EvalRow.model_validate(json.loads(line)) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def edit_distance(a, b):
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (x != y)))
        previous = current
    return previous[-1]


def real_asset(token, repo):
    if token.startswith("FS:"):
        return False
    sign = repo.get_sign(token)
    return bool(sign and sign.asset_type != "demo" and sign.review_status == "verified" and
                all((value or "").strip() for value in (sign.source, sign.licence, sign.signer)) and
                sign.review_decision != "rejected" and (asset_path(sign.video) or asset_path(sign.clip)))


async def evaluate(rows, translator=translate, repo=None):
    verified = [row for row in rows if row.review_status == "verified" and not row.placeholder]
    if not verified:
        raise ValueError("NO_VERIFIED_ROWS: no signer-reviewed evaluation rows; no scores produced")
    repo = repo or get_repository()
    exact = distance = reference_tokens = generated = covered = spelled = nmm_matches = 0
    engines, notices = set(), set()
    details = []
    for row in verified:
        response = await translator(TranslationRequest(text=row.english))
        predicted = response.gloss
        actual_nmm = [item.nmm.model_dump(exclude_none=True) for item in response.gloss_detail]
        expected_nmm = [item.model_dump(exclude_none=True) for item in row.expected_nmm]
        matched = predicted == row.expected_gloss
        edits = edit_distance(row.expected_gloss, predicted)
        exact += matched; distance += edits; reference_tokens += len(row.expected_gloss)
        generated += len(predicted)
        covered += sum(real_asset(token, repo) for token in predicted)
        # Include missing/rejected rendering fallbacks, not just model FS flags.
        spelled += sum(item.gloss.startswith("FS:") for item in response.sequence)
        nmm_matches += actual_nmm == expected_nmm
        engines.add(response.engine)
        if response.notice: notices.add(response.notice)
        details.append({"english": row.english, "gloss": predicted, "exact_match": matched, "edit_distance": edits})
    return {"verified_rows": len(verified), "ignored_rows": len(rows) - len(verified),
        "gloss_exact_match": exact / len(verified), "gloss_sequence_edit_distance": distance,
        "normalized_gloss_edit_distance": distance / max(1, reference_tokens),
        "vocabulary_coverage": covered / max(1, generated), "fingerspell_rate": spelled / max(1, generated),
        "nmm_exact_match": nmm_matches / len(verified), "engines": sorted(engines), "notices": sorted(notices),
        "coverage_definition": "Fraction of predicted gloss tokens with existing verified non-demo assets",
        "nmm_definition": "Per-sentence exact match of aligned per-token configured numeric channels",
        "fingerspell_definition": "Fraction of sequence items explicitly marked FS; browser-only demo fallback is not measured",
        "limitations": "Gloss/NMM agreement and asset coverage do not establish signer comprehension or natural ISL quality.",
        "rows": details}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--testset", type=Path, default=ROOT / "eval" / "isl_testset.jsonl")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        rows = load_rows(args.testset)
        # Fail readiness before opening an event loop or any service connection.
        if not any(row.review_status == "verified" and not row.placeholder for row in rows):
            raise ValueError("NO_VERIFIED_ROWS: no signer-reviewed evaluation rows; no scores produced")
        report = asyncio.run(evaluate(rows))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2 if "NO_VERIFIED_ROWS" in str(exc) else 1
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
