"""Mechanical demo coverage tests; no native-speaker or ISL correctness claims."""

import asyncio
import json
import re
from pathlib import Path

import pytest

from config import settings
from fake_llm import install_fake_api
from models.translation import TranslationRequest
from services import llm_service
from services.gloss_service import translate
from services.indic_service import GLOSSARY_NOTICE, LEXICON_DIR, romanize
from services.sign_repository import get_repository
from tools.coverage_report import build_report, main


@pytest.mark.parametrize(
    "language,text,expected",
    [
        ("hi-IN", "मुझे मदद चाहिए", "me help need"),
        ("kn-IN", "ನನಗೆ ಸಹಾಯ ಬೇಕು", "me help need"),
    ],
)
def test_fully_mapped_sentence(language, text, expected):
    english, notice = asyncio.run(llm_service.english_input(text, language))
    assert english == expected and GLOSSARY_NOTICE in notice
    assert "Machine-translated to English first; not verified." in notice
    assert "Unmapped tokens" not in notice


def test_unmapped_preserved_then_romanized():
    text = "मुझे नमस्तिका चाहिए"
    english, notice = asyncio.run(llm_service.english_input(text, "Hindi"))
    assert english == "me नमस्तिका need"
    assert "Unmapped tokens preserved: नमस्तिका" in notice
    result = asyncio.run(translate(TranslationRequest(text=text, source_language="hi-IN")))
    assert result.original_text == text and result.english_text == english
    fs = next(token for token in result.gloss_detail if token.fs)
    assert fs.gloss == "FS:NAMASTIKAA" and fs.fs_reason == "oov"
    assert "romanized/transliterated" in result.notice and "not the ISL alphabet" in result.notice


def test_api_precedence_and_cache(monkeypatch):
    client, requests = install_fake_api(
        monkeypatch, payload={"text": "I want help"}, tool_name="emit_english"
    )
    for _ in range(2):
        english, notice = asyncio.run(llm_service.english_input("मुझे मदद चाहिए", "hi-IN"))
        assert english == "I want help" and GLOSSARY_NOTICE not in notice
    assert client.messages.create.await_count == 1
    assert requests[0]["tool_choice"] == {"type": "tool", "name": "emit_english"}


def test_api_failure_uses_glossary(monkeypatch):
    install_fake_api(monkeypatch, error=RuntimeError("fixture"))
    english, notice = asyncio.run(llm_service.english_input("ನನಗೆ ಸಹಾಯ ಬೇಕು", "kn-IN"))
    assert english == "me help need" and "failed" in notice and GLOSSARY_NOTICE in notice


def test_glossary_optional(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DEMO_INDIC_GLOSSARY", False)
    english, notice = asyncio.run(llm_service.english_input("नमस्ते", "hi-IN"))
    assert english == "नमस्ते" and "disabled" in notice


@pytest.mark.parametrize(
    "word,expected",
    [
        ("नमस्ते", "NAMASTE"),
        ("मदद", "MADADA"),
        ("पानी", "PAANII"),
        ("ಕನ್ನಡ", "KANNADA"),
        ("ನಮಸ್ಕಾರ", "NAMASKAARA"),
        ("ನೀರು", "NIIRU"),
    ],
)
def test_romanization(word, expected):
    assert romanize(word) == expected
    result = llm_service.mock_transform(word)
    assert all(re.fullmatch(r"FS:[A-Z0-9_]+", token.gloss) for token in result.gloss)


def test_glossary_targets_and_parallel_files():
    repo = get_repository()
    for code in ("hi", "kn"):
        data = json.loads((LEXICON_DIR / f"{code}_en.json").read_text(encoding="utf-8"))
        assert data["review_status"] == "unverified" and data["notes"] == GLOSSARY_NOTICE
        assert len(data["entries"]) < 100
        assert all(repo.get_by_text(word) for word in data["entries"].values())
        lines = (
            (Path(__file__).parents[2] / f"eval/domain_sentences_{code}.txt")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        assert "pending native-speaker review" in lines[0]
        assert len([line for line in lines if line and not line.startswith("#")]) == 60


def test_coverage_is_offline_and_preserves_unmapped(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "api")
    report = build_report(
        ["# ignored", "मुझे मदद चाहिए", "मुझे नमस्तिका चाहिए"], source_language="hi-IN"
    )
    assert report["error_count"] == 0 and report["sentence_count"] == 2 and report["fs_count"] == 1
    assert "नमस्तिका" in report["sentences"][1]["english_text"]
    assert "Unmapped tokens preserved" in report["sentences"][1]["notice"]
    assert (
        main(
            [
                str(tmp_path / "missing"),
                "--strict",
                "--source-language",
                "kn-IN",
                "--json-output",
                str(tmp_path / "r.json"),
                "--markdown-output",
                str(tmp_path / "r.md"),
            ]
        )
        == 1
    )
