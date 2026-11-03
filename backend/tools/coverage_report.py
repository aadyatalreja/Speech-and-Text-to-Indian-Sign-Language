"""Measure English vocabulary gaps locally. Never calls a model or certifies ISL."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.llm_service import mock_transform, demo_english_input, result_notice


def build_report(sentences, transform=mock_transform, source_language="English"):
    rows, gaps = [], Counter()
    total_fs = total_tokens = 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or sentence.startswith("#"):
            continue
        try:
            english, input_notice = demo_english_input(sentence, source_language)
            result = transform(english)
            count = sum(token.fs for token in result.gloss)
            total_fs += count
            total_tokens += len(result.gloss)
            gaps.update(
                (token.gloss[3:].casefold(), token.lemma_tried)
                for token in result.gloss
                if token.fs and token.fs_reason == "oov"
            )
            rows.append(
                {
                    "sentence": sentence,
                    "english_text": english,
                    "notice": " ".join(
                        filter(None, [input_notice, result_notice(result, english)])
                    ),
                    "gloss": result.flat_gloss,
                    "fs_count": count,
                    "gloss_detail": [
                        token.model_dump(
                            include={"gloss", "fs_reason", "lemma_tried", "synonym_from"}
                        )
                        for token in result.gloss
                    ],
                    "error": None,
                }
            )
        except Exception as exc:
            # A failed measurement is disclosed, never disguised as zero gaps.
            rows.append(
                {
                    "sentence": sentence,
                    "gloss": None,
                    "fs_count": None,
                    "gloss_detail": [],
                    "error": type(exc).__name__,
                }
            )
    return {
        "source_language": source_language,
        "pipeline": "Deterministic offline Indic-to-English demo glossary then English lookup/gloss; no model calls.",
        "description": "English repository coverage and translation pipeline only; not ISL grammar, accuracy or signer evaluation.",
        "definition": "FS tokens / emitted gloss tokens in successfully measured sentences. OOV ranking excludes name_heuristic and explicit tokens.",
        "sentences": rows,
        "sentence_count": len(rows),
        "error_count": sum(row["error"] is not None for row in rows),
        "total_gloss_tokens": total_tokens,
        "fs_count": total_fs,
        "fs_rate": total_fs / total_tokens if total_tokens else None,
        "top_oov_words": [
            {"word": word, "frequency": frequency, "lemma_tried": lemma}
            for (word, lemma), frequency in sorted(
                gaps.items(), key=lambda item: (-item[1], item[0][0], item[0][1] or "")
            )
        ],
    }


def markdown(report):
    def escape(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    rate = f"{report['fs_rate']:.1%}" if report["fs_rate"] is not None else "not measurable"
    lines = [
        "## English vocabulary coverage",
        "",
        report["description"],
        f"Source language: {report['source_language']}. {report['pipeline']}",
        "",
        f"Sentences: {report['sentence_count']}; measurement errors: {report['error_count']}; FS: {report['fs_count']}/{report['total_gloss_tokens']} ({rate}).",
        "",
        report["definition"],
        "",
        "| Source sentence | English intermediate | Gloss | FS count | Notice |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in report["sentences"]:
        lines.append(
            f"| {escape(row['sentence'])} | {escape(row.get('english_text', ''))} | {escape(' '.join(row['gloss']) if row['gloss'] is not None else 'Measurement error: ' + row['error'])} | {row['fs_count'] if row['fs_count'] is not None else 'N/A'} | {escape(row.get('notice', ''))} |"
        )
    lines += [
        "",
        "### Out-of-vocabulary words",
        "",
        "| Word | Frequency | Lemma tried |",
        "| --- | ---: | --- |",
    ]
    lines.extend(
        f"| {escape(item['word'])} | {item['frequency']} | {escape(item['lemma_tried'] or 'not attempted')} |"
        for item in report["top_oov_words"]
    )
    substitutions = [
        f"{token['synonym_from']} -> {token['gloss']}"
        for row in report["sentences"]
        for token in row["gloss_detail"]
        if token.get("synonym_from")
    ]
    if substitutions:
        lines += [
            "",
            "English WordNet synonym/hypernym fallback: meaning may drift; not ISL grammar.",
            "",
            ", ".join(escape(item) for item in substitutions),
        ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="One sentence per line; # headers ignored")
    parser.add_argument(
        "--source-language",
        default="English",
        choices=["English", "Hindi", "Kannada", "en-IN", "hi-IN", "kn-IN"],
    )
    parser.add_argument(
        "--strict", action="store_true", help="CI: exit nonzero on measurement/input/output errors"
    )
    parser.add_argument("--json-output", type=Path, default=Path("coverage-report.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("coverage-report.md"))
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 0
    try:
        sentences = args.input.read_text(encoding="utf-8").splitlines()
        report = build_report(sentences, source_language=args.source_language)
    except Exception as exc:
        report = build_report([], source_language=args.source_language)
        report.update(error_count=1, input_error=type(exc).__name__)
    write_errors = 0
    for path, content in (
        (args.json_output, json.dumps(report, indent=2) + "\n"),
        (args.markdown_output, markdown(report)),
    ):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            write_errors += 1
            print(f"Could not write {path.name}: {type(exc).__name__}", file=sys.stderr)
    print(
        json.dumps(
            {key: report[key] for key in ("sentence_count", "fs_count", "fs_rate", "error_count")}
        )
    )
    return int(args.strict and (report["error_count"] > 0 or write_errors > 0))


if __name__ == "__main__":
    raise SystemExit(main())
