"""Export sentences for human review; no verification is inferred."""

import argparse
import csv
from pathlib import Path

COLUMNS = [
    "english",
    "reviewed_gloss",
    "acceptable_alternatives",
    "nmm_notes",
    "reviewer",
    "signer_dialect",
    "comments",
]
ROOT = Path(__file__).resolve().parents[2]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sentences", type=Path, default=ROOT / "eval/domain_sentences.txt")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        for sentence in args.sentences.read_text(encoding="utf-8").splitlines():
            if sentence.strip() and not sentence.lstrip().startswith("#"):
                writer.writerow({"english": sentence.strip()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
