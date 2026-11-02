"""SDK-shaped test doubles only; no real network or paid API calls."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from services import llm_service


def install_fake_api(monkeypatch, gloss=None, payload=None, error=None):
    requests = []

    async def create(**kwargs):
        requests.append(kwargs)
        if error:
            raise error
        return SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="tool_use",
                    name="emit_gloss",
                    input=payload
                    if payload is not None
                    else {"intent": "statement", "gloss": gloss, "confidence": 0.8},
                )
            ],
            stop_reason="tool_use",
            usage=SimpleNamespace(cache_read_input_tokens=64, cache_creation_input_tokens=128),
        )

    client = SimpleNamespace(
        messages=SimpleNamespace(create=AsyncMock(side_effect=create)), close=AsyncMock()
    )
    monkeypatch.setattr(llm_service, "_client", client)
    monkeypatch.setattr(llm_service.settings, "LLM_API_KEY", "fake-test-key")
    monkeypatch.setattr(llm_service.settings, "LLM_PROVIDER", "api")
    return client, requests


def system_text(request):
    return "\n".join(block["text"] for block in request["system"])
