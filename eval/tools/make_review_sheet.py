"""Export sentences for human review; no verification is inferred."""

import argparse
import csv
from pathlib import Path
import asyncio
import subprocess
import sys

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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sentences", type=Path, default=ROOT / "eval/domain_sentences.txt")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--packet-dir", type=Path)
    parser.add_argument("--source-language", default="English")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    sentences = [
        s.strip()
        for s in args.sentences.read_text(encoding="utf-8").splitlines()
        if s.strip() and not s.lstrip().startswith("#")
    ]
    if args.limit is not None:
        if args.limit < 1:
            parser.error("limit must be positive")
        sentences = sentences[: args.limit]
    if args.packet_dir:
        from eval.review_packet import create_packet, write_packet_html

        asyncio.run(create_packet(sentences, args.packet_dir, args.source_language))
        subprocess.run(
            [
                "node",
                str(ROOT / "paper/render_avatar.mjs"),
                "--packet",
                str(args.packet_dir.resolve()),
            ],
            check=True,
            cwd=ROOT,
        )
        write_packet_html(args.packet_dir, compact=True)
        return 0
    if args.output is None:
        parser.error("--output or --packet-dir is required")
    with args.output.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        for sentence in sentences:
            if sentence.strip() and not sentence.lstrip().startswith("#"):
                writer.writerow({"english": sentence.strip()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
