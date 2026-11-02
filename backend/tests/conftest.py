import pytest

from services.rate_limit import limiter
from services import llm_service


@pytest.fixture(autouse=True)
def isolate_rate_buckets():
    limiter.buckets.clear()
    yield
    limiter.buckets.clear()


@pytest.fixture(autouse=True)
def isolate_llm_state(monkeypatch):
    # Even an accidentally configured local key must never reach a real SDK call.
    monkeypatch.setattr(llm_service.settings, "LLM_PROVIDER", "mock")
    monkeypatch.setattr(llm_service.settings, "LLM_ORDERING", "code")
    monkeypatch.setattr(llm_service.settings, "ENABLE_SYNONYM_FALLBACK", False)
    monkeypatch.setattr(llm_service, "_client", None)

    def forbidden_client(**kwargs):
        raise AssertionError("Tests must install a fake Anthropic client")

    monkeypatch.setattr(llm_service, "AsyncAnthropic", forbidden_client)
    llm_service.response_cache.clear()
    yield
    llm_service.response_cache.clear()
