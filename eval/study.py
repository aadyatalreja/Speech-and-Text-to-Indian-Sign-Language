"""Seeded overlapping assignments; exports BLANK responses, never judgements."""

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
import random
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]


def assign(item_ids, n, reviewers, overlap, seed=20261103):
    if not 1 <= n <= len(item_ids) or not 1 <= overlap <= reviewers:
        raise ValueError("Require 1 <= N <= available items and 1 <= overlap <= R")
    if len(set(item_ids)) != len(item_ids):
        raise ValueError("Item IDs must be unique")
    rng = random.Random(seed)
    selected = rng.sample(list(item_ids), n)
    names = [f"R{i + 1:02d}" for i in range(reviewers)]
    rng.shuffle(names)
    allocations = {name: [] for name in sorted(names)}
    for i, item in enumerate(selected):
        for j in range(overlap):
            allocations[names[(i * overlap + j) % reviewers]].append(item)
    for items in allocations.values():
        rng.shuffle(items)
    return allocations


def export_study(packet, output, n, reviewers, overlap, seed=20261103):
    from eval.review_packet import validate_packet

    packet, output = Path(packet), Path(output)
    if output.exists():
        raise ValueError("Refusing to overwrite an existing study")
    manifest_path = packet / "manifest.json"
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    manifest = validate_packet(packet)
    by_id = {item["item_id"]: item for item in manifest["items"]}
    allocations = assign(list(by_id), n, reviewers, overlap, seed)
    output.mkdir(parents=True)
    (output / "stimuli").mkdir()
    for ident in {i for assigned in allocations.values() for i in assigned}:
        # Remove printed gloss labels for a blinded still-frame pilot.
        if "blinded_strip" in by_id[ident]:
            shutil.copyfile(
                packet / by_id[ident]["blinded_strip"], output / "stimuli" / f"{ident}.png"
            )
            continue
        source = (packet / by_id[ident]["frame_strip"]).read_text(encoding="utf-8")
        import re

        source = re.sub(r"<text\b[^>]*>.*?</text>", "", source, flags=re.S)
        (output / "stimuli" / f"{ident}.svg").write_text(source, encoding="utf-8")
    fields = [
        "reviewer_id",
        "item_id",
        "manifest_sha256",
        "meaning_response",
        "comprehension",
        "comments",
    ]
    for reviewer, ids in allocations.items():
        with (output / f"{reviewer}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(
                {"reviewer_id": reviewer, "item_id": ident, "manifest_sha256": digest}
                for ident in ids
            )
        page = '<!doctype html><html lang="en"><meta charset="utf-8"><h1>Blinded frame-strip pilot</h1><p>Unverified demo renderer. Interpret the images, record meaning_response and comprehension (1–5) in the response CSV. No correct answer is supplied. Still-frame interpretation is NOT signing comprehension; replace with approved full-motion stimuli before a comprehension study.</p>'
        for ident in ids:
            extension = "png" if "blinded_strip" in by_id[ident] else "svg"
            page += f'<section><h2>{html.escape(ident)}</h2><img style="width:100%" alt="Unverified demo stimulus; no source/gloss hint" src="stimuli/{ident}.{extension}"></section>'
        (output / f"{reviewer}.html").write_text(page + "</html>", encoding="utf-8")
    design = {
        "seed": seed,
        "N": n,
        "R": reviewers,
        "overlap": overlap,
        "packet_sha256": digest,
        "assignments": allocations,
        "presentation": "blinded still-frame pilot; full-motion, signer-approved stimuli required for comprehension study",
        "judgements": "NONE COLLECTED",
        "limitations": "Assignment scaffold only. No ISL/comprehension accuracy or human agreement results.",
    }
    (output / "design.json").write_text(json.dumps(design, indent=2) + "\n", encoding="utf-8")
    return design


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--reviewers", type=int, required=True)
    parser.add_argument("--overlap", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20261103)
    args = parser.parse_args(argv)
    export_study(args.packet, args.output, args.n, args.reviewers, args.overlap, args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
