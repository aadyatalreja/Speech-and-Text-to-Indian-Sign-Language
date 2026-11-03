"""Offline English/coverage ablation, NOT an ISL-accuracy/model benchmark."""

import argparse
import asyncio
from contextlib import contextmanager
import importlib.metadata
from itertools import product
import json
import platform
from pathlib import Path
import random
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from config import settings  # noqa: E402
from eval.metrics import content_coverage, DISCLAIMER  # noqa: E402
from eval.review_packet import snapshot_paths  # noqa: E402
from eval.run_eval import load_rows, evaluate  # noqa: E402
from services import llm_service  # noqa: E402
from services.gloss_service import translate  # noqa: E402
from services.indic_service import language_code  # noqa: E402
from services.sign_repository import get_repository  # noqa: E402
from models.translation import TranslationRequest  # noqa: E402

SEED = 20261103
DOMAINS = ("campus", "hospital", "travel", "shopping", "family")


class OfflineTransport:
    """SDK-shaped local simulation. NO model inference or network calls.

    emit_english reuses the demo glossary; emit_gloss reuses real lexical lookup
    with grammar disabled, returning input order. Thus 'model ordering' means
    an input-order fixture, not an independently evaluated model's ordering.
    """

    def __init__(self):
        self.messages = self

    async def create(self, **request):
        text = request["messages"][0]["content"]
        name = request["tool_choice"]["name"]
        if name == "emit_english":
            language = "kn-IN" if any("\u0c80" <= c <= "\u0cff" for c in text) else "hi-IN"
            english, _ = llm_service.demo_english_input(text, language)
            payload = {"text": english}
        elif name == "emit_gloss":
            original = llm_service.active_rules
            try:
                llm_service.active_rules = lambda: []
                result = llm_service.mock_transform(text)
            finally:
                llm_service.active_rules = original
            payload = {"intent": result.intent, "gloss": result.flat_gloss, "confidence": 0.0}
        else:
            raise ValueError("Unsupported simulated tool")
        return SimpleNamespace(
            content=[SimpleNamespace(type="tool_use", name=name, input=payload)],
            stop_reason="tool_use",
        )


@contextmanager
def configuration(provider, ordering, synonym):
    names = (
        "LLM_PROVIDER",
        "LLM_ORDERING",
        "ENABLE_SYNONYM_FALLBACK",
        "ENABLE_DEMO_INDIC_GLOSSARY",
        "LLM_API_KEY",
    )
    before = {name: getattr(settings, name) for name in names}
    client, constructor = llm_service._client, llm_service.AsyncAnthropic
    try:
        settings.LLM_PROVIDER = "api" if provider == "simulated_api" else "mock"
        settings.LLM_ORDERING = ordering
        settings.ENABLE_SYNONYM_FALLBACK = synonym
        settings.ENABLE_DEMO_INDIC_GLOSSARY = True
        settings.LLM_API_KEY = "OFFLINE-TRANSPORT-NO-NETWORK"
        llm_service._client = OfflineTransport() if provider == "simulated_api" else None

        def forbidden(**kwargs):
            raise RuntimeError("Network client construction forbidden in offline ablation")

        llm_service.AsyncAnthropic = forbidden
        llm_service.response_cache.clear()
        yield
    finally:
        for name, value in before.items():
            setattr(settings, name, value)
        llm_service._client, llm_service.AsyncAnthropic = client, constructor
        llm_service.response_cache.clear()


def environment():
    try:
        node = subprocess.check_output(["node", "--version"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        node = "unavailable"
    packages = {}
    for name in ("nltk", "pydantic", "anthropic", "matplotlib"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "unavailable"
    import nltk
    import hashlib

    try:
        corpus = Path(str(nltk.data.find("corpora/wordnet.zip")))
        wordnet_hash = hashlib.sha256(corpus.read_bytes()).hexdigest()
    except LookupError:
        wordnet_hash = "unavailable"
    return {
        "python": platform.python_version(),
        "node": node,
        "platform": platform.platform(),
        "packages": packages,
        "model_id_configured_not_called": settings.LLM_MODEL,
        "seed": SEED,
        "wordnet_zip_sha256": wordnet_hash,
    }


async def run(sentences_by_language=None, axes=None):
    random.seed(SEED)
    corpora = sentences_by_language or {
        code: [
            line
            for line in (ROOT / "eval" / f"domain_sentences{suffix}.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.startswith("#")
        ]
        for code, suffix in (("en-IN", ""), ("hi-IN", "_hi"), ("kn-IN", "_kn"))
    }
    axes = axes or list(product(("mock", "simulated_api"), ("code", "model"), (False, True)))
    evaluation_rows = load_rows(ROOT / "eval/isl_testset.jsonl")
    repo = get_repository()
    cells = []
    for provider, ordering, synonyms in axes:
        with configuration(provider, ordering, synonyms):
            for language, sentences in corpora.items():
                rows = []
                for index, source in enumerate(sentences):
                    response = await translate(
                        TranslationRequest(text=source, source_language=language)
                    )
                    rows.append(
                        {
                            "source": source,
                            "english": response.english_text,
                            "domain": DOMAINS[index // 12] if len(sentences) == 60 else "fixture",
                            "gloss": response.gloss,
                            "fs_count": sum(t.startswith("FS:") for t in response.gloss),
                            "token_count": len(response.gloss),
                            **content_coverage(response.english_text or source, repo),
                        }
                    )
                total = sum(row["token_count"] for row in rows)
                fs = sum(row["fs_count"] for row in rows)
                content = sum(row["content_words"] for row in rows)
                covered = sum(row["resolved_content_words"] for row in rows)
                eligible = [
                    r
                    for r in evaluation_rows
                    if r.review_status == "verified"
                    and not r.placeholder
                    and language_code(r.source_language) == language_code(language)
                ]
                scores = await evaluate(eligible) if eligible else None
                cells.append(
                    {
                        "provider": provider,
                        "ordering": ordering,
                        "synonyms": synonyms,
                        "source_language": language,
                        "sentences": len(rows),
                        "tokens": total,
                        "fs_tokens": fs,
                        "coverage": (total - fs) / total if total else None,
                        "fs_rate": fs / total if total else None,
                        "content_word_coverage": covered / content if content else None,
                        "metrics_status": "SCORED_VERIFIED_ROWS"
                        if eligible
                        else "NO_VERIFIED_ROWS",
                        "verified_scores": scores,
                        "rows": rows,
                    }
                )
    return {
        "label": "English/coverage pipeline ablation, NOT ISL accuracy or a live-model benchmark",
        "simulation": "simulated_api is an SDK transport fixture, using the demo glossary and real deterministic lookup in input order. No live model calls/numbers. mock ignores LLM_ORDERING; model ordering in simulated_api is a fixture, not model reasoning.",
        "disclaimer": DISCLAIMER,
        "environment": environment(),
        "source_hashes": snapshot_paths(),
        "cells": cells,
    }


def markdown(report):
    text = f"# Coverage pipeline ablation\n\n{report['label']}\n\n{report['simulation']}\n\n{report['disclaimer']}\n\nCoverage here is 1 − FS-token rate (repository membership, including demos), not verified-asset coverage. Content coverage uses the documented English function-word heuristic.\n\n"
    text += "| Path | Ordering | Synonyms | Language | Tokens | Coverage | FS rate | Content coverage | Verified metrics |\n|---|---|---|---|---:|---:|---:|---:|---|\n"

    def percent(value):
        return f"{value:.2%}" if value is not None else "N/A"

    for cell in report["cells"]:
        text += f"| {cell['provider']} | {cell['ordering']} | {cell['synonyms']} | {cell['source_language']} | {cell['tokens']} | {percent(cell['coverage'])} | {percent(cell['fs_rate'])} | {percent(cell['content_word_coverage'])} | {cell['metrics_status']} |\n"
    return (
        text
        + "\nEnvironment (configured model ID is not a called model):\n```json\n"
        + json.dumps(report["environment"], indent=2)
        + "\n```\n"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "eval/reports/ablation.json")
    args = parser.parse_args(argv)
    report = asyncio.run(run())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    args.output.with_suffix(".md").write_text(markdown(report), encoding="utf-8")
    print(markdown(report).replace("−", "-"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
