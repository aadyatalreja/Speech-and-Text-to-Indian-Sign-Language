import asyncio

import httpx
import pytest

from config import Settings, DEFAULT_LLM_MODEL, settings
from tools.check_model import check_model


def test_documented_default_and_environment_override():
    assert Settings({}).LLM_MODEL == DEFAULT_LLM_MODEL == "claude-sonnet-5-5"
    assert Settings({"LLM_MODEL": "claude-sonnet-4-5-20250929"}).LLM_MODEL == "claude-sonnet-4-5-20250929"


@pytest.mark.parametrize("env", [{"LLM_PROVIDER": "unknown"}, {"LLM_MODEL": ""}, {"LLM_MODEL": "invented id"},
    {"INTER_SIGN_PAUSE": "-1"}, {"INTER_SIGN_PAUSE": "nan"}, {"AVATAR_TRANSITION_SECONDS": "2"}, {"LLM_MAX_TOKENS": "0"}])
def test_invalid_configuration(env):
    with pytest.raises(ValueError): Settings(env)


def test_optional_model_availability_uses_read_only_request(monkeypatch):
    monkeypatch.setattr(settings, "LLM_API_KEY", "synthetic-key")
    def handler(request):
        assert request.method == "GET" and request.url.path == "/v1/models/" + settings.LLM_MODEL
        assert request.headers["x-api-key"] == "synthetic-key"
        return httpx.Response(200, json={"id": settings.LLM_MODEL})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await check_model(client)
    assert asyncio.run(run())["resolved_id"] == settings.LLM_MODEL
