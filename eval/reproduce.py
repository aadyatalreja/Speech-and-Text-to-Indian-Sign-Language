"""One-command offline tables, figures, blank review packet and study scaffold."""

import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from eval.ablation import run, markdown, configuration  # noqa: E402
from eval.review_packet import create_packet, write_packet_html, validate_packet  # noqa: E402
from eval.study import export_study  # noqa: E402
from tools.coverage_report import build_report, markdown as coverage_markdown  # noqa: E402
from models.translation import TranslationRequest  # noqa: E402
from services.gloss_service import translate  # noqa: E402


async def regenerate(output):
    from paper.figures import generate

    output.mkdir(parents=True, exist_ok=True)
    reports = ROOT / "eval/reports"
    reports.mkdir(parents=True, exist_ok=True)
    with configuration("mock", "code", False):
        corpora = {}
        for code, suffix in (("en", ""), ("hi", "_hi"), ("kn", "_kn")):
            lines = (
                (ROOT / "eval" / f"domain_sentences{suffix}.txt")
                .read_text(encoding="utf-8")
                .splitlines()
            )
            corpora[code] = [line for line in lines if line.strip() and not line.startswith("#")]
            report = build_report(lines, source_language=code + "-IN")
            if report["error_count"]:
                raise ValueError("Coverage measurement failed; figures refused")
            (reports / f"{code}.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            (reports / f"{code}.md").write_text(coverage_markdown(report), encoding="utf-8")
        # Actual deterministic application response, not an invented pose/gloss.
        expression = await translate(TranslationRequest(text="Where is the hospital?"))
        (output / "expression_response.json").write_text(
            expression.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        packet = output / "reviewer_packet"
        if packet.exists():
            validate_packet(packet)  # Never overwrite a packet or returned human forms.
        else:
            batch = [corpora["en"][i] for i in (0, 12, 24, 36, 48)]
            await create_packet(batch, packet)
            subprocess.run(
                ["node", str(ROOT / "paper/render_avatar.mjs"), "--packet", str(packet)],
                check=True,
                cwd=ROOT,
            )
            write_packet_html(packet, compact=True)
        study = output / "study_scaffold"
        if not study.exists():
            export_study(packet, study, 5, 3, 2)
    ablation = await run()
    (reports / "ablation.json").write_text(
        json.dumps(ablation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (reports / "ablation.md").write_text(markdown(ablation), encoding="utf-8")
    (output / "environment-lock.json").write_text(
        json.dumps(ablation["environment"], indent=2) + "\n", encoding="utf-8"
    )
    generate(reports, output)
    subprocess.run(
        [
            "node",
            str(ROOT / "paper/render_avatar.mjs"),
            "--input",
            str(output / "expression_response.json"),
            "--output",
            str(output / "expressions.svg"),
        ],
        check=True,
        cwd=ROOT,
    )
    from paper.svg_raster import rasterize

    rasterize(output / "expressions.svg", output / "expressions.png")
    readiness = {
        "status": "NO_VERIFIED_ROWS"
        if all(c["metrics_status"] == "NO_VERIFIED_ROWS" for c in ablation["cells"])
        else "SEE_VERIFIED_SCORES",
        "scores_fabricated": False,
        "human_judgements": "NONE GENERATED",
        "ablation_table": "eval/reports/ablation.md",
        "disclaimer": ablation["disclaimer"],
    }
    (output / "readiness.json").write_text(json.dumps(readiness, indent=2) + "\n", encoding="utf-8")
    print(markdown(ablation).replace("−", "-"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "paper/generated")
    args = parser.parse_args(argv)
    asyncio.run(regenerate(args.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
