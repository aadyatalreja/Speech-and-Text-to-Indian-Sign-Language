"""Rebuild publication figures from executed coverage reports, never invented scores."""

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / "paper/.cache/matplotlib"))
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
import numpy as np  # noqa: E402

DOMAINS = ("Campus", "Hospital", "Travel", "Shopping", "Family")
LANGUAGES = ("English", "Hindi", "Kannada")
CAPTIONS = {
    "architecture": "Actual application data flow. Speech is browser recognition; English preprocessing prefers the configured API and otherwise uses the unverified demo glossary. Understand uses the configured API or deterministic fallback. Markers and renderer outputs are demo/unverified unless individually reviewed. This schematic measures no accuracy and is NOT verified ISL grammar or comprehension evidence.",
    "coverage_languages": "Executed deterministic offline pipeline on 60 aligned inputs per language; token-weighted repository-membership coverage (including demo signs) and explicit FS-gloss-token rate. No live-model numbers. These are complementary engineering measures, NOT verified-asset coverage, ISL accuracy, or comprehension. Hindi/Kannada translations and glossary are machine-assembled, pending native-speaker review.",
    "coverage_domains": "Executed offline coverage reports, grouped by the committed 12-sentence blocks for campus/hospital/travel/shopping/family. Cells show repository-membership coverage and FS-token rate, weighted by emitted gloss-token counts. No estimates or human judgements are added. Demos and lexical translation remain unverified; this is NOT ISL accuracy or comprehension.",
    "expressions": "Same executed sentence, same sign and midpoint pose, with nonmanual channels suppressed (left) versus the configured demo channels (right). SVG projection uses the actual AvatarRig, mergeNmm and pose sampling code; the camera is cropped to the head for inspection, without idle motion. This is a rendering comparison, NOT verified ISL facial grammar, motion timing, signer comprehension or publication of a reviewed sign.",
}


def save(fig, output, name):
    fig.savefig(
        output / f"{name}.svg",
        bbox_inches="tight",
        metadata={"Date": None, "Description": CAPTIONS[name]},
    )
    fig.savefig(
        output / f"{name}.png",
        bbox_inches="tight",
        dpi=220,
        metadata={"Description": CAPTIONS[name]},
    )
    plt.close(fig)


def generate(reports, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "svg.hashsalt": "signai-paper-20261103",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    data = [
        json.loads((Path(reports) / f"{code}.json").read_text(encoding="utf-8"))
        for code in ("en", "hi", "kn")
    ]
    for report in data:
        if report["error_count"] or report["sentence_count"] != 60:
            raise ValueError("Figures require three error-free, aligned 60-sentence reports")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = np.arange(3)
    fs = [r["fs_rate"] * 100 for r in data]
    coverage = [100 - v for v in fs]
    for offset, values, label, color in (
        (-0.18, coverage, "Repository coverage (demos included)", "#216779"),
        (0.18, fs, "FS gloss-token rate", "#bc643b"),
    ):
        bars = ax.bar(x + offset, values, 0.34, label=label, color=color)
        ax.bar_label(bars, labels=[f"{value:.2f}%" for value in values], padding=4, fontsize=10)
    ax.set(
        xticks=x,
        xticklabels=[
            f"{name}\nn={r['total_gloss_tokens']} tokens" for name, r in zip(LANGUAGES, data)
        ],
        ylim=(0, 110),
        ylabel="Emitted gloss tokens (%)",
        title="Offline lexical coverage — 60 parallel sentences per language",
    )
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    fig.text(
        0.01,
        -0.04,
        "Coverage ≠ verified sign assets, ISL accuracy or comprehension. Indic inputs/glossaries pending native-speaker review.",
        fontsize=9,
    )
    save(fig, output, "coverage_languages")
    domain_fs = np.zeros((5, 3))
    counts = []
    for language, report in enumerate(data):
        column = []
        for domain in range(5):
            rows = report["sentences"][domain * 12 : (domain + 1) * 12]
            tokens = sum(len(row["gloss"]) for row in rows)
            spelled = sum(row["fs_count"] for row in rows)
            domain_fs[domain, language] = spelled / tokens * 100
            column.append({"domain": DOMAINS[domain], "tokens": tokens, "fs_tokens": spelled})
        counts.append(column)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), layout="constrained")
    for ax, matrix, title in zip(
        axes, (100 - domain_fs, domain_fs), ("Repository coverage (%)", "FS gloss-token rate (%)")
    ):
        image = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=100, aspect="auto")
        ax.set(
            xticks=np.arange(3),
            xticklabels=LANGUAGES,
            yticks=np.arange(5),
            yticklabels=DOMAINS,
            title=title,
        )
        for i in range(5):
            for j in range(3):
                ax.text(
                    j,
                    i,
                    f"{matrix[i, j]:.1f}",
                    ha="center",
                    va="center",
                    color="white" if matrix[i, j] > 60 else "#142d3b",
                )
    fig.colorbar(image, ax=axes, shrink=0.8, label="Percent of emitted gloss tokens")
    fig.suptitle("Per-domain offline coverage — 12 sentences/domain/language")
    fig.supxlabel(
        "Demo repository membership; NOT verified ISL accuracy or comprehension", fontsize=9
    )
    save(fig, output, "coverage_domains")
    (output / "domain_counts.json").write_text(
        json.dumps(
            {"languages": LANGUAGES, "counts": counts, "disclaimer": CAPTIONS["coverage_domains"]},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    fig, ax = plt.subplots(figsize=(13, 5.8))
    ax.set(xlim=(0, 13), ylim=(0, 6))
    ax.axis("off")
    boxes = [
        (0.2, 3.5, "Text / browser speech\nselected source locale"),
        (2.8, 3.5, "english_input\nAPI preferred\nDemo glossary fallback"),
        (5.4, 3.5, "understand\nAPI / deterministic lookup"),
        (8.0, 3.5, "apply_markers\nconfigured demo rules"),
        (8.0, 1.0, "SignSequenceService\nasset lookup + FS + timing"),
        (10.6, 1.0, "Avatar / video\nclip, demo, spelling fallback"),
    ]
    for x0, y0, text in boxes:
        ax.add_patch(
            FancyBboxPatch(
                (x0, y0),
                2.2,
                1.0,
                boxstyle="round,pad=0.1",
                facecolor="#edf4f7",
                edgecolor="#236375",
                linewidth=1.5,
            )
        )
        ax.text(x0 + 1.1, y0 + 0.5, text, ha="center", va="center", fontsize=9)
    for start, end in (
        ((2.45, 4), (2.65, 4)),
        ((5.05, 4), (5.25, 4)),
        ((7.65, 4), (7.85, 4)),
        ((9.1, 3.35), (9.1, 2.15)),
        ((10.25, 1.5), (10.45, 1.5)),
    ):
        ax.add_patch(
            FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=16, color="#236375")
        )
    ax.text(
        3.9,
        2.8,
        "Editable English intermediate\nuser correction → rerun in English",
        ha="center",
        fontsize=10,
        color="#8e4b2f",
    )
    ax.add_patch(
        FancyArrowPatch(
            (3.9, 2.95), (3.9, 3.35), arrowstyle="->", mutation_scale=14, color="#8e4b2f"
        )
    )
    ax.text(
        6.5,
        5.4,
        "Application architecture — actual configured data flow",
        ha="center",
        fontsize=15,
        weight="bold",
    )
    ax.text(
        6.5,
        0.1,
        "Schematic only. Demo glossary, markers, assets and engine interpolation are NOT verified ISL or comprehension evidence.",
        ha="center",
        fontsize=9,
    )
    save(fig, output, "architecture")
    (output / "captions.md").write_text(
        "# Figure captions\n\n"
        + "\n\n".join(f"**{name}.svg** — {caption}" for name, caption in CAPTIONS.items())
        + "\n",
        encoding="utf-8",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=ROOT / "eval/reports")
    parser.add_argument("--output", type=Path, default=ROOT / "paper/generated")
    args = parser.parse_args(argv)
    generate(args.reports, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
