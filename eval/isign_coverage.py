"""Measure SignAI vocabulary coverage on a locally acquired iSign transcript CSV."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tools.coverage_report import build_report  # noqa: E402

UID = re.compile(r"(?P<video>.+)-[0-9]+")
SPLITS = ("train", "dev", "test")


def video_split(video_id):
    bucket = int.from_bytes(hashlib.sha256(video_id.encode("utf-8")).digest()[:8], "big") % 100
    return "train" if bucket < 80 else "dev" if bucket < 90 else "test"


def load_transcripts(path, uid_column, text_column, split, limit=None):
    selected = []
    video_ids, seen = set(), set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if uid_column == text_column or not {uid_column, text_column}.issubset(
            reader.fieldnames or []
        ):
            raise ValueError(
                f"Expected distinct UID and text columns. Found {reader.fieldnames or []}"
            )
        for row in reader:
            uid = (row.get(uid_column) or "").strip()
            text = (row.get(text_column) or "").strip()
            match = UID.fullmatch(uid)
            if not match or not text or text.startswith("#"):
                raise ValueError(f"Invalid UID or English text at CSV line {reader.line_num}")
            if uid in seen:
                raise ValueError(f"Duplicate UID at CSV line {reader.line_num}")
            seen.add(uid)
            video_id = match["video"]
            if split == "all" or video_split(video_id) == split:
                video_ids.add(video_id)
                selected.append(text)
                if limit is not None and len(selected) == limit:
                    break
    return selected, len(video_ids)


def coverage(path, uid_column, text_column, split, limit=None, report_builder=build_report):
    sentences, video_count = load_transcripts(path, uid_column, text_column, split, limit)
    if not sentences:
        raise ValueError("No rows selected. Try another split or --split all.")
    report = report_builder(sentences)
    # Keep the report local and aggregate. Source sentences and generated glosses are omitted.
    return {
        "dataset": "Exploration-Lab/iSign",
        "measurement": "Offline English lookup coverage. No ISL translation accuracy scores.",
        "split": split,
        "split_strategy": "Project-specific SHA-256 video-ID split (80/10/10)",
        "row_limit": limit,
        "distinct_source_videos": video_count,
        **{
            key: report[key]
            for key in (
                "sentence_count",
                "error_count",
                "total_gloss_tokens",
                "fs_count",
                "fs_rate",
                "top_oov_words",
            )
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--uid-column", default="uid")
    parser.add_argument(
        "--text-column", required=True, help="English transcript column from the CSV header"
    )
    parser.add_argument("--split", choices=(*SPLITS, "all"), default="test")
    parser.add_argument(
        "--limit", type=int, help="Measure the first N selected rows as a smoke test"
    )
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    try:
        report = coverage(args.csv, args.uid_column, args.text_column, args.split, args.limit)
    except (ValueError, OSError, csv.Error) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return int(report["error_count"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
