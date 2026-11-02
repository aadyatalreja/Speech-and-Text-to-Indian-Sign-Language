"""Build an import manifest from a local category/word/video tree. No network."""

import argparse
import csv
import io
from pathlib import Path
import re

COLUMNS = [
    "gloss",
    "aliases",
    "category",
    "video_path",
    "source",
    "licence",
    "signer",
    "landmarks_path",
]
EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}


def build_rows(root, licence, source, signer_note, limit=None):
    if limit is not None and limit < 0:
        raise ValueError("limit must be nonnegative")
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("Dataset root must be a local directory")
    rows, seen = [], set()
    for video in sorted(root.glob("*/*/*"), key=lambda p: p.as_posix()):
        if not video.is_file() or video.suffix.lower() not in EXTENSIONS:
            continue
        word = video.parent.name.strip()
        gloss = re.sub(r"[^A-Z0-9]+", "_", word.upper()).strip("_")
        if not gloss or gloss in seen:
            continue
        seen.add(gloss)
        # Only spelling separators are obvious variants; never invent synonyms.
        alias = " ".join(word.replace("_", " ").replace("-", " ").split()).lower()
        rows.append(
            dict(
                zip(
                    COLUMNS,
                    [
                        gloss,
                        alias if "_" in word or "-" in word else "",
                        video.parent.parent.name,
                        str(video.resolve()),
                        source,
                        licence,
                        signer_note,
                        "",
                    ],
                )
            )
        )
    return rows if limit is None else rows[:limit]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, default=Path("include_manifest.csv"))
    for name in ("licence", "source", "signer-note"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    rows = build_rows(args.root, args.licence, args.source, args.signer_note, args.limit)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    if args.dry_run:
        print(stream.getvalue(), end="")
    else:
        args.output.write_text(stream.getvalue(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
