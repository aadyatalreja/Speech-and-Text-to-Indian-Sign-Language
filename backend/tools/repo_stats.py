"""Report registry counts; optionally reject stale README sign counts."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import string

ROOT = Path(__file__).resolve().parents[2]


def stats(root):
    root = Path(root)
    rows = list(json.loads((root / "signs.json").read_text(encoding="utf-8")).values())
    path = root / "alphabet/manifest.json"
    alphabet = json.loads(path.read_text(encoding="utf-8"))["characters"] if path.exists() else {}
    present = sum(
        bool(alphabet.get(c, {}).get("clip"))
        and (root / "alphabet" / alphabet[c]["clip"]).is_file()
        for c in string.ascii_uppercase + string.digits
    )
    return {
        "total": len(rows),
        "asset_type": dict(Counter(r.get("asset_type", "none") for r in rows)),
        "review_status": dict(Counter(r.get("review_status", "unverified") for r in rows)),
        "video_or_clip": sum(bool(r.get("video") or r.get("clip")) for r in rows),
        "alphabet_present": present,
        "alphabet_missing": 36 - present,
    }


def check_readme(text, report):
    for match in re.finditer(
        r"\b(\d+)\s+(?:(demo|verified|unverified|dataset|real)\s+)?(?:(sign)\s+)?(entries|signs|recordings)\b",
        text,
        re.I,
    ):
        count, kind = int(match[1]), (match[2] or "").lower()
        if not kind and not match[3] and match[4].lower() == "entries":
            continue  # Unqualified counts may describe thresholds or caches.
        expected = (
            report["asset_type"].get(kind, 0)
            if kind in {"demo", "dataset"}
            else report["review_status"].get(kind, 0)
            if kind in {"verified", "unverified"}
            else report["video_or_clip"]
            if kind == "real"
            else report["total"]
        )
        if count != expected:
            raise ValueError(
                f"README sign count {match[0]!r} disagrees with repo_stats ({expected})"
            )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "backend/data/signs")
    parser.add_argument("--check-readme", type=Path)
    args = parser.parse_args(argv)
    report = stats(args.root)
    print(json.dumps(report, indent=2))
    if args.check_readme:
        check_readme(args.check_readme.read_text(encoding="utf-8"), report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
