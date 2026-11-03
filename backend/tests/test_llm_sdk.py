import asyncio
import logging
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient

from fake_llm import install_fake_api
from config import Settings, settings
from main import app
from models.translation import LLMResult, TranslationRequest
from services import llm_service, marker_service, grammar_service
from services.gloss_service import translate
from services.response_cache import ResponseCache
from services.sign_repository import get_repository
from services.vocabulary_service import select_vocabulary


def test_forced_tool_and_prompt_cache_blocks(monkeypatch, caplog):
    client, requests = install_fake_api(monkeypatch, gloss=["HELLO", "INVENTED_SIGN", "FS:PRIYA"])
    with caplog.at_level(logging.DEBUG, logger="signai.llm"):
        result = asyncio.run(llm_service.api_transform("hello"))
    request = requests[0]
    assert request["tool_choice"] == {"type": "tool", "name": "emit_gloss"}
    schema = request["tools"][0]["input_schema"]["$defs"]["GlossToken"]["properties"]["gloss"]
    assert schema["anyOf"][0]["enum"] == select_vocabulary("hello", get_repository())
    assert schema["anyOf"][1]["pattern"].startswith("^FS:")
    assert request["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "English word order" in request["system"][0]["text"]
    assert request["system"][1]["text"].startswith("Allowed repository glosses")
    assert "cache_read=64 cache_creation=128" in caplog.text
    assert result.flat_gloss == ["HELLO", "FS:INVENTED_SIGN", "FS:PRIYA"]
    assert result.gloss[1].fs_reason == "model_unknown"
    assert result.gloss[2].fs_reason == "explicit"
    client.messages.create.assert_awaited_once()


@pytest.mark.parametrize("failure", ["timeout", "429", "malformed", "truncated", "no_tool"])
def test_errors_preserve_fallback_and_never_log_key(monkeypatch, caplog, failure):
    request = httpx.Request("POST", "https://example.invalid")
    error = (
        anthropic.APITimeoutError(request=request)
        if failure == "timeout"
        else anthropic.RateLimitError(
            "fake-test-key must never be logged",
            response=httpx.Response(429, request=request),
            body=None,
        )
        if failure == "429"
        else None
    )
    client, _ = install_fake_api(monkeypatch, gloss=[{"wrong": "shape"}], error=error)
    if failure == "truncated":
        client.messages.create.side_effect = None
        client.messages.create.return_value = SimpleNamespace(content=[], stop_reason="max_tokens")
    if failure == "no_tool":
        client.messages.create.side_effect = None
        client.messages.create.return_value = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="{}")], stop_reason="end_turn"
        )
    result, engine, notice = asyncio.run(llm_service.understand("hello"))
    assert result.flat_gloss == ["HELLO"] and engine == "mock-fallback"
    assert "AI translation is temporarily unavailable. Switching to fallback mode." in notice
    assert "fake-test-key" not in caplog.text
    assert not llm_service.response_cache.items


def test_shared_sdk_client_created_and_closed_by_lifespan(monkeypatch):
    client = SimpleNamespace(close=AsyncMock())
    constructor = Mock(return_value=client)
    monkeypatch.setattr(llm_service, "AsyncAnthropic", constructor)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "api")
    monkeypatch.setattr(settings, "LLM_API_KEY", "fake-test-key")
    monkeypatch.setattr(settings, "LLM_TIMEOUT_SECONDS", 7)
    monkeypatch.setattr(settings, "LLM_MAX_RETRIES", 3)
    with TestClient(app):
        llm_service.start_client()
        assert llm_service._client is client
        constructor.assert_called_once_with(api_key="fake-test-key", timeout=7, max_retries=3)
    client.close.assert_awaited_once()
    assert llm_service._client is None


def test_sdk_client_closed_even_if_later_startup_work_fails(monkeypatch):
    import main

    client = SimpleNamespace(close=AsyncMock())
    monkeypatch.setattr(llm_service, "_client", client)
    monkeypatch.setattr(
        main, "cleanup_generated", Mock(side_effect=RuntimeError("fixture startup failure"))
    )
    with pytest.raises(RuntimeError, match="fixture startup failure"):
        with TestClient(app):
            pass
    client.close.assert_awaited_once()
    assert llm_service._client is None


@pytest.mark.parametrize(
    "text, gloss",
    [
        ("I need help", ["I", "NEED", "HELP"]),
        ("I go to college tomorrow", ["I", "GO", "FS:TO", "COLLEGE", "TOMORROW"]),
        ("hello and water", ["HELLO", "FS:AND", "WATER"]),
    ],
)
def test_api_and_mock_share_code_ordering_and_markers(monkeypatch, text, gloss):
    expected = llm_service.mock_transform(text)
    install_fake_api(monkeypatch, gloss=gloss)
    actual = asyncio.run(llm_service.api_transform(text))
    assert actual.flat_gloss == expected.flat_gloss
    assert actual.grammar_rules == expected.grammar_rules
    api_response = asyncio.run(translate(TranslationRequest(text=text)))
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    mock_response = asyncio.run(translate(TranslationRequest(text=text)))
    assert api_response.gloss == mock_response.gloss
    assert api_response.sentence == mock_response.sentence
    assert [token.nmm for token in api_response.gloss_detail] == [
        token.nmm for token in mock_response.gloss_detail
    ]


def test_only_actual_code_rules_reported_and_model_ordering_opt_in(monkeypatch):
    install_fake_api(monkeypatch, gloss=["I", "GO", "COLLEGE", "TOMORROW"])
    result = asyncio.run(llm_service.api_transform("I go college tomorrow"))
    assert result.flat_gloss == ["TOMORROW", "I", "COLLEGE", "GO"]
    assert "legacy_function_word_filter" not in {rule.id for rule in result.grammar_rules}
    monkeypatch.setattr(settings, "LLM_ORDERING", "model")
    old = asyncio.run(llm_service.api_transform("I go college tomorrow"))
    assert old.flat_gloss == ["I", "GO", "COLLEGE", "TOMORROW"]
    assert "llm_ordering_not_signer_reviewed" in {rule.id for rule in old.grammar_rules}


def test_response_cache_hit_copies_and_disable(monkeypatch):
    client, _ = install_fake_api(monkeypatch, gloss=["HELLO"])
    first = asyncio.run(llm_service.api_transform(" hello "))
    first.gloss[0].gloss = "MUTATED"
    assert asyncio.run(llm_service.api_transform("hello")).flat_gloss == ["HELLO"]
    client.messages.create.assert_awaited_once()
    monkeypatch.setattr(settings, "LLM_CACHE_SIZE", 0)
    asyncio.run(llm_service.api_transform("hello"))
    asyncio.run(llm_service.api_transform("hello"))
    assert client.messages.create.await_count == 3


def test_response_cache_ttl_and_lru(monkeypatch):
    monkeypatch.setattr(settings, "LLM_CACHE_SIZE", 2)
    monkeypatch.setattr(settings, "LLM_CACHE_TTL_SECONDS", 10)
    clock = Mock(return_value=0)
    cache = ResponseCache(clock)
    value = LLMResult(gloss=["HELLO"])
    cache.put("a", value)
    cache.put("b", value)
    assert cache.get("a") is not None
    cache.put("c", value)
    assert cache.get("b") is None
    clock.return_value = 10
    assert cache.get("a") is None and cache.get("c") is None


def test_cache_key_changes_with_rules_examples_model_vocabulary_and_order(monkeypatch, tmp_path):
    rules = tmp_path / "rules.yaml"
    examples = tmp_path / "examples.jsonl"
    rules.write_text(marker_service.RULES_PATH.read_text())
    examples.write_text(grammar_service.EXAMPLES_PATH.read_text())
    monkeypatch.setattr(marker_service, "RULES_PATH", rules)
    monkeypatch.setattr(grammar_service, "EXAMPLES_PATH", examples)
    client, _ = install_fake_api(monkeypatch, gloss=["HELLO"])

    def run():
        asyncio.run(llm_service.api_transform("hello"))

    run()
    run()
    assert client.messages.create.await_count == 1
    for path in (rules, examples):
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
        run()
    monkeypatch.setattr(settings, "LLM_MODEL", "claude-test-fixture")
    run()
    monkeypatch.setattr(settings, "LLM_ORDERING", "model")
    run()
    monkeypatch.setattr(llm_service, "select_vocabulary", lambda text, repo: ["HELLO"])
    run()
    assert client.messages.create.await_count == 6


@pytest.mark.parametrize(
    "env",
    [
        {"LLM_TIMEOUT_SECONDS": "nan"},
        {"LLM_TIMEOUT_SECONDS": "0"},
        {"LLM_MAX_RETRIES": "-1"},
        {"LLM_MAX_RETRIES": "11"},
        {"LLM_CACHE_SIZE": "-1"},
        {"LLM_CACHE_TTL_SECONDS": "0"},
        {"LLM_ORDERING": "invented"},
        {"ENABLE_SYNONYM_FALLBACK": "maybe"},
    ],
)
def test_new_settings_are_validated(env):
    with pytest.raises(ValueError):
        Settings(env)


def test_new_settings_defaults():
    config = Settings({})
    assert (
        config.LLM_TIMEOUT_SECONDS,
        config.LLM_MAX_RETRIES,
        config.LLM_CACHE_SIZE,
        config.LLM_CACHE_TTL_SECONDS,
        config.LLM_ORDERING,
        config.ENABLE_SYNONYM_FALLBACK,
    ) == (20, 2, 256, 300, "code", False)
