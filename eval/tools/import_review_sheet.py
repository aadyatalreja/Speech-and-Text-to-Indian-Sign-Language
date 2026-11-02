"""Convert a returned signer CSV to JSONL. Empty glosses are rejected."""

import argparse
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_eval import EvalRow


def convert(path):
    rows = []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        for number, row in enumerate(csv.DictReader(stream), 2):
            gloss = row["reviewed_gloss"].split()
            if not gloss:
                raise ValueError(f"CSV line {number}: empty reviewed gloss")
            reviewer = row["reviewer"].strip()
            alternatives = [
                part.split()
                for part in row.get("acceptable_alternatives", "").split("|")
                if part.strip()
            ]
            english = row["english"].strip()
            intent = (
                "negation"
                if any(
                    w in english.lower().split() for w in ("not", "never", "no", "don't", "cannot")
                )
                else "question"
                if english.endswith("?")
                else "statement"
            )
            rows.append(
                EvalRow(
                    english=english,
                    expected_gloss=gloss,
                    acceptable_alternatives=alternatives,
                    expected_nmm=[{} for _ in gloss],
                    reviewer=reviewer or None,
                    review_status="verified" if reviewer else "unverified",
                    signer_dialect=row.get("signer_dialect", ""),
                    comments=row.get("comments", ""),
                    nmm_notes=row.get("nmm_notes", ""),
                    intent=intent,
                ).model_dump(mode="json")
            )
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sheet", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).resolve().parents[1] / "isl_testset.jsonl"
    )
    args = parser.parse_args(argv)
    rows = convert(args.sheet)
    args.output.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
