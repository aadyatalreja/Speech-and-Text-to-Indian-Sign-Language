import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from main import app
from models.translation import LLMResult
from services import llm_service
from services.sign_repository import JsonSignRepository, get_repository
from services.vocabulary_service import select_vocabulary, validate_vocabulary


def make_repo(tmp_path, extra=None, count=0):
    entries = {f"UNRELATED_{i}": {"id": f"unrelated_{i}", "gloss": f"UNRELATED_{i}"}
               for i in range(count)}
    entries.update(extra or {})
    path = tmp_path / "signs.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return JsonSignRepository(path)


def mock_api(monkeypatch, gloss):
    requests = []
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"content": [{"type": "text", "text": json.dumps({
            "intent": "statement", "gloss": gloss, "confidence": 0.8})}]})
    client = httpx.AsyncClient
    monkeypatch.setattr(llm_service.httpx, "AsyncClient",
                        lambda **kwargs: client(transport=httpx.MockTransport(handler), **kwargs))
    monkeypatch.setattr(llm_service.settings, "LLM_API_KEY", "fake-test-key")
    monkeypatch.setattr(llm_service.settings, "LLM_PROVIDER", "api")
    return requests


def test_small_repository_sends_all_glosses():
    repo = get_repository()
    assert select_vocabulary("anything", repo) == sorted(repo.list_glosses())


def test_shortlist_uses_alias_lemma_and_core_without_unrelated_entries(tmp_path):
    repo = make_repo(tmp_path, {
        "I": {"id": "i", "gloss": "I"},
        "NOT": {"id": "not", "gloss": "NOT"},
        "CUSTOM_FUNCTION": {"id": "function", "gloss": "CUSTOM_FUNCTION", "category": "function"},
        "CAMPUS": {"id": "campus", "gloss": "CAMPUS", "aliases": ["college"]},
        "LEARN": {"id": "learn", "gloss": "LEARN", "lemma": "study"},
    }, count=301)
    assert select_vocabulary("studied at colleges", repo) == ["CAMPUS", "CUSTOM_FUNCTION", "I", "LEARN", "NOT"]
    assert select_vocabulary("xyzunknown", repo) == ["CUSTOM_FUNCTION", "I", "NOT"]


def test_shortlist_ranking_limit_and_determinism(tmp_path):
    repo = make_repo(tmp_path, {
        "I": {"id": "i", "gloss": "I"},
        "EXACT": {"id": "exact", "gloss": "EXACT", "aliases": ["red apple"]},
        "PARTIAL": {"id": "partial", "gloss": "PARTIAL", "aliases": ["apple tree"]},
        "OTHER": {"id": "other", "gloss": "OTHER"},
    })
    assert select_vocabulary("red apple", repo, limit=2) == ["EXACT", "I"]
    assert select_vocabulary("red apple", repo, limit=2) == select_vocabulary("red apple", repo, limit=2)
    with pytest.raises(ValueError, match="positive"):
        select_vocabulary("apple", repo, limit=0)


def test_validation_canonicalizes_aliases_and_never_resolves_explicit_fs(tmp_path):
    repo = make_repo(tmp_path, {"HELLO": {"id": "hello", "gloss": "HELLO", "aliases": ["hi there"]},
                                "GO": {"id": "go", "gloss": "GO"}})
    result = LLMResult(gloss=["hi_there", "made up", "FS:HELLO", "GO", "fs:priya"])
    checked = validate_vocabulary(result, repo, ["HELLO"])
    assert checked.flat_gloss == ["HELLO", "FS:MADE_UP", "FS:HELLO", "FS:GO", "FS:PRIYA"]
    assert result.flat_gloss[0] == "hi_there"  # caller's result isn't mutated


@pytest.mark.parametrize("token", ["", "???", "FS:", "FS:??", "FS:FS:HELLO"])
def test_invalid_tokens_are_rejected(token):
    with pytest.raises(ValueError):
        validate_vocabulary(LLMResult(gloss=[token]), get_repository(), ["HELLO"])


def test_mocked_api_invention_is_caught_and_prompt_contains_vocabulary(monkeypatch, tmp_path):
    repo = make_repo(tmp_path, {"HELLO": {"id": "hello", "gloss": "HELLO", "aliases": ["hi there"]}})
    requests = mock_api(monkeypatch, ["hi there", "INVENTED_SIGN", "FS:PRIYA"])
    result = asyncio.run(llm_service.api_transform("Hi there Priya", repo))
    assert result.flat_gloss == ["HELLO", "FS:INVENTED_SIGN", "FS:PRIYA"]
    assert 'Allowed repository glosses (JSON): ["HELLO"]' in requests[0]["system"]
    assert "FS:<WORD>" in requests[0]["system"]
    assert requests[0]["messages"][0]["content"] == "Hi there Priya"


def test_large_api_prompt_excludes_unrelated_glosses(monkeypatch, tmp_path):
    repo = make_repo(tmp_path, {"HELLO": {"id": "hello", "gloss": "HELLO"}}, count=301)
    requests = mock_api(monkeypatch, ["HELLO", "UNRELATED_0"])
    result = asyncio.run(llm_service.api_transform("hello", repo))
    assert 'Allowed repository glosses (JSON): ["HELLO"]' in requests[0]["system"]
    assert "UNRELATED_0" not in requests[0]["system"]
    assert result.flat_gloss == ["HELLO", "FS:UNRELATED_0"]


@pytest.mark.parametrize("gloss", [["FS:"], ["???"], [{"invented": "object"}]])
def test_malformed_api_output_uses_existing_fallback(monkeypatch, gloss):
    mock_api(monkeypatch, gloss)
    result, engine, notice = asyncio.run(llm_service.understand("hello"))
    assert result.flat_gloss == ["HELLO"]
    assert engine == "mock-fallback" and notice


def test_corrected_api_tokens_reach_rest_and_stream(monkeypatch):
    mock_api(monkeypatch, ["HELLO", "INVENTED_SIGN", "FS:PRIYA"])
    client = TestClient(app)
    response = client.post("/api/translate", json={"text": "Hello Priya"})
    assert response.status_code == 200
    body = response.json()
    expected = ["HELLO", "FS:INVENTED_SIGN", "FS:PRIYA"]
    assert body["engine"] == "api" and body["gloss"] == expected
    assert [item["gloss"] for item in body["sequence"]] == expected
    assert body["unknown_signs"] == ["INVENTED_SIGN", "PRIYA"]
    assert "placeholder fingerspelling" in body["notice"]
    with client.websocket_connect("/api/translate/stream") as ws:
        ws.send_json({"text": "Hello Priya"})
        assert ws.receive_json()["gloss"] == expected
        assert [ws.receive_json()["item"]["gloss"] for _ in expected] == expected
        assert ws.receive_json()["unknown_signs"] == ["INVENTED_SIGN", "PRIYA"]
