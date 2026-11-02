"""Offline ISL review-set evaluation. Never scores unverified/placeholder rows."""

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# CLI bootstrap must precede imports from the backend source tree.
from models.markers import NonManualMarkers  # noqa: E402
from models.translation import TranslationRequest  # noqa: E402
from services.gloss_service import translate  # noqa: E402
from services.sign_repository import get_repository  # noqa: E402
from services.timing_service import asset_path  # noqa: E402


class EvalRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    english: str = Field(min_length=1)
    expected_gloss: list[str] = Field(default_factory=list)
    acceptable_alternatives: list[list[str]] = Field(default_factory=list)
    intent: Literal["statement", "question", "negation"] = "statement"
    signer_dialect: str = ""
    comments: str = ""
    nmm_notes: str = ""
    expected_nmm: list[NonManualMarkers] = Field(default_factory=list)
    reviewer: str | None = None
    review_status: Literal["unverified", "in_review", "verified"]
    placeholder: bool = False

    @model_validator(mode="after")
    def reviewed_content(self):
        if self.review_status == "verified" and (
            self.placeholder
            or not (self.reviewer or "").strip()
            or not self.expected_gloss
            or any(not token.strip() for token in self.expected_gloss)
            or len(self.expected_nmm) != len(self.expected_gloss)
        ):
            raise ValueError(
                "Verified rows require reviewer, non-placeholder gloss, and one NMM object per token"
            )
        if any(
            not ref or any(not token.strip() for token in ref)
            for ref in self.acceptable_alternatives
        ):
            raise ValueError("Alternative glosses must be nonempty")
        return self


def load_rows(path):
    return [
        EvalRow.model_validate(json.loads(line))
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


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
    return bool(
        sign
        and sign.asset_type != "demo"
        and sign.review_status == "verified"
        and all((value or "").strip() for value in (sign.source, sign.licence, sign.signer))
        and sign.review_decision != "rejected"
        and (asset_path(sign.video) or asset_path(sign.clip))
    )


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
        references = [row.expected_gloss, *row.acceptable_alternatives]
        matched = predicted in references
        reference = min(
            references, key=lambda ref: edit_distance(ref, predicted) / max(1, len(ref))
        )
        edits = edit_distance(reference, predicted)
        exact += matched
        distance += edits
        reference_tokens += len(reference)
        generated += len(predicted)
        covered += sum(real_asset(token, repo) for token in predicted)
        # Include missing/rejected rendering fallbacks, not just model FS flags.
        spelled += sum(item.gloss.startswith("FS:") for item in response.sequence)
        nmm_matches += actual_nmm == expected_nmm
        engines.add(response.engine)
        if response.notice:
            notices.add(response.notice)
        details.append(
            {
                "generated_tokens": len(predicted),
                "fingerspelled_tokens": sum(
                    item.gloss.startswith("FS:") for item in response.sequence
                ),
                "oov_tokens": sum(not repo.get_by_text(token) for token in predicted),
                "intent": row.intent,
                "reference_tokens": len(reference),
                "english": row.english,
                "gloss": predicted,
                "exact_match": matched,
                "edit_distance": edits,
            }
        )
    return {
        "verified_rows": len(verified),
        "ignored_rows": len(rows) - len(verified),
        "gloss_word_error_rate": distance / max(1, reference_tokens),
        "out_of_vocabulary_rate": sum(d["oov_tokens"] for d in details) / max(1, generated),
        "per_intent": {
            intent: {
                "rows": len(subset),
                "fingerspell_rate": sum(d["fingerspelled_tokens"] for d in subset)
                / max(1, sum(d["generated_tokens"] for d in subset)),
                "out_of_vocabulary_rate": sum(d["oov_tokens"] for d in subset)
                / max(1, sum(d["generated_tokens"] for d in subset)),
                "exact_match": sum(d["exact_match"] for d in subset) / max(1, len(subset)),
                "wer": sum(d["edit_distance"] for d in subset)
                / max(1, sum(d["reference_tokens"] for d in subset)),
            }
            for intent in ("statement", "question", "negation")
            for subset in [[d for d in details if d["intent"] == intent]]
        },
        "gloss_exact_match": exact / len(verified),
        "gloss_sequence_edit_distance": distance,
        "normalized_gloss_edit_distance": distance / max(1, reference_tokens),
        "vocabulary_coverage": covered / max(1, generated),
        "fingerspell_rate": spelled / max(1, generated),
        "nmm_exact_match": nmm_matches / len(verified),
        "engines": sorted(engines),
        "notices": sorted(notices),
        "coverage_definition": "Fraction of predicted gloss tokens with existing verified non-demo assets",
        "nmm_definition": "Per-sentence exact match of aligned per-token configured numeric channels",
        "fingerspell_definition": "Fraction of sequence items explicitly marked FS; browser-only demo fallback is not measured",
        "limitations": "Gloss/NMM agreement and asset coverage do not establish signer comprehension or natural ISL quality.",
        "rows": details,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--testset", type=Path, default=ROOT / "eval" / "isl_testset.jsonl")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="SYNTHETIC software fixtures only; never CI reporting",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--baseline", type=Path, default=ROOT / "eval/baseline.json")
    parser.add_argument("--tolerance", type=float, default=0.0)
    args = parser.parse_args(argv)
    if args.tolerance < 0:
        parser.error("tolerance must be nonnegative")
    if args.fixture and args.check:
        parser.error("SYNTHETIC fixtures cannot be used for regression acceptance")
    try:
        rows = (
            load_rows(args.testset)
            if not args.fixture
            else [
                EvalRow(
                    english="SYNTHETIC",
                    expected_gloss=["SYNTHETIC"],
                    expected_nmm=[{}],
                    reviewer="SYNTHETIC software fixture",
                    review_status="verified",
                )
            ]
        )

        async def fixture_translator(req):
            from models.translation import TranslationResponse
            from models.markers import GlossToken
            from models.sign import SignSequenceItem

            return TranslationResponse(
                original_text=req.text,
                target_sign_language="ISL",
                intent="statement",
                entities=[],
                gloss=["FS:SYNTHETIC"],
                gloss_detail=[GlossToken(gloss="FS:SYNTHETIC")],
                sequence=[
                    SignSequenceItem(
                        gloss="FS:SYNTHETIC", sign_id=None, available=False, duration=1
                    )
                ],
                unknown_signs=["SYNTHETIC"],
                confidence=0,
                engine="SYNTHETIC",
            )

        # Fail readiness before opening an event loop or any service connection.
        if not any(row.review_status == "verified" and not row.placeholder for row in rows):
            raise ValueError(
                "NO_VERIFIED_ROWS: no signer-reviewed evaluation rows; no scores produced"
            )
        report = asyncio.run(evaluate(rows, fixture_translator if args.fixture else translate))
        report["synthetic"] = args.fixture
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2 if "NO_VERIFIED_ROWS" in str(exc) else 1
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    label = " SYNTHETIC" if args.fixture else ""
    first = f"Verified rows: {report['verified_rows']}{label}"
    warning = (
        "WARNING: fewer than 20 verified rows; these numbers are not reliable."
        if report["verified_rows"] < 20
        else ""
    )
    markdown = first + "\n\n" + warning + "\n\n```json\n" + rendered + "\n```\n"
    if args.markdown_output:
        args.markdown_output.write_text(markdown, encoding="utf-8")
    elif args.output:
        args.output.with_suffix(".md").write_text(markdown, encoding="utf-8")
    print(first)
    if warning:
        print(warning)
    print(rendered)
    if args.check:
        try:
            baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
            if (
                baseline.get("gloss_exact_match") is None
                or baseline.get("gloss_word_error_rate") is None
            ):
                raise ValueError(
                    "No accepted baseline; signer review and explicit baseline acceptance required"
                )
            return int(
                report["gloss_exact_match"] < baseline["gloss_exact_match"] - args.tolerance
                or report["gloss_word_error_rate"]
                > baseline["gloss_word_error_rate"] + args.tolerance
            )
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
