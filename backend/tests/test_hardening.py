import asyncio
import json
import os
from threading import BoundedSemaphore
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from api import video
from config import Settings, settings
from main import app
from models.translation import TranslationRequest
from services import gloss_service, grammar_service, marker_service
from services.generated_cleanup import cleanup_generated, cleanup_loop
from services.rate_limit import RateLimiter, limiter
from services.video_service import VideoResult


@pytest.mark.parametrize(
    "env",
    [
        {"CORS_ORIGINS": "*"},
        {"CORS_ORIGINS": "https://example.org/path"},
        {"CORS_ORIGINS": "https://user:pass@example.org"},
        {"CORS_ORIGINS": ""},
        {"CORS_ORIGINS": "https://example.org:bad"},
        {"CORS_ORIGINS": "https://example.org,"},
        {"CORS_ORIGINS": "https://example.org:"},
        {"CORS_ORIGINS": "https://example.org?"},
        {"CORS_ORIGINS": "https://example.org\\path"},
        {"RATE_LIMIT_TRANSLATE_PER_MIN": "0"},
        {"RATE_LIMIT_VIDEO_PER_MIN": "-1"},
        {"MAX_VIDEO_JOBS": "1.2"},
        {"GENERATED_TTL_MINUTES": "0"},
    ],
)
def test_hardening_config_rejects_invalid_values(env):
    with pytest.raises(ValueError):
        Settings(env)


def test_hardening_defaults_and_cors():
    defaults = Settings({})
    assert (
        defaults.RATE_LIMIT_TRANSLATE_PER_MIN,
        defaults.RATE_LIMIT_VIDEO_PER_MIN,
        defaults.MAX_VIDEO_JOBS,
        defaults.GENERATED_TTL_MINUTES,
    ) == (30, 5, 2, 60)
    assert Settings(
        {"CORS_ORIGINS": "https://example.org, http://localhost:5173"}
    ).CORS_ORIGINS == ["https://example.org", "http://localhost:5173"]
    client = TestClient(app)
    assert (
        client.get("/api/health", headers={"Origin": "http://localhost:5173"}).headers[
            "access-control-allow-origin"
        ]
        == "http://localhost:5173"
    )
    assert (
        "access-control-allow-origin"
        not in client.get("/api/health", headers={"Origin": "https://unconfigured.example"}).headers
    )


def test_token_bucket_refills_and_isolates_clients_and_groups():
    clock = Mock(return_value=0)
    bucket = RateLimiter(clock)
    assert bucket.retry_after("a", "translate", 2) == 0
    assert bucket.retry_after("a", "translate", 2) == 0
    assert bucket.retry_after("a", "translate", 2) == 30
    assert bucket.retry_after("b", "translate", 2) == 0
    assert bucket.retry_after("a", "video", 1) == 0
    clock.return_value = 15
    assert bucket.retry_after("a", "translate", 2) == 15
    clock.return_value = 30
    assert bucket.retry_after("a", "translate", 2) == 0
    clock.return_value = 100
    assert bucket.retry_after("c", "video", 1) == 0
    assert set(bucket.buckets) == {("c", "video")}


def test_translate_limit_shared_with_websocket_and_untrusted_headers(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_TRANSLATE_PER_MIN", 1)
    client = TestClient(app)
    assert client.post("/api/translate", json={"text": "hello"}).status_code == 200
    response = client.post(
        "/api/translate", json={"text": "hello"}, headers={"X-Forwarded-For": "fake"}
    )
    assert response.status_code == 429 and int(response.headers["Retry-After"]) > 0
    with client.websocket_connect("/api/translate/stream") as ws:
        event = ws.receive_json()
        assert set(event) == {"type", "error"} and event["type"] == "error"
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 1008
    # Exhaustion from WebSocket also applies to HTTP.
    limiter.buckets.clear()
    with client.websocket_connect("/api/translate/stream") as ws:
        ws.send_json({"text": "hello"})
        assert [ws.receive_json()["type"] for _ in range(3)] == ["understanding", "sign", "done"]
    assert client.post("/api/translate", json={"text": "hello"}).status_code == 429


def test_video_limits_and_semaphore_release(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_VIDEO_PER_MIN", 2)
    semaphore = BoundedSemaphore(1)
    monkeypatch.setattr(video, "video_jobs", semaphore)
    generate = Mock(return_value=VideoResult(video_url="/generated/test.mp4", missing_glosses=[]))
    monkeypatch.setattr(video, "generate_video_result", generate)
    client = TestClient(app)
    semaphore.acquire()
    response = client.post("/api/generate-video", json={"sequence": ["HELLO"]})
    assert response.status_code == 429 and "busy" in response.json()["detail"]
    assert response.headers["Retry-After"] == "1"
    generate.assert_not_called()
    semaphore.release()
    assert client.post("/api/generate-video", json={"sequence": ["HELLO"]}).status_code == 200
    assert semaphore.acquire(blocking=False)
    semaphore.release()
    response = client.post("/api/generate-video", json={"sequence": ["HELLO"]})
    assert response.status_code == 429 and "Retry-After" in response.headers


def test_video_semaphore_released_on_failure(monkeypatch):
    from services.video_service import VideoError

    semaphore = BoundedSemaphore(1)
    monkeypatch.setattr(video, "video_jobs", semaphore)
    monkeypatch.setattr(
        video, "generate_video_result", Mock(side_effect=VideoError("fixture failure"))
    )
    assert (
        TestClient(app).post("/api/generate-video", json={"sequence": ["HELLO"]}).status_code == 422
    )
    assert semaphore.acquire(blocking=False)
    semaphore.release()


@pytest.mark.parametrize(
    "sequence",
    [[], ["A"] * 51, ["A" * 65], ["../file"], ["FS:"], ["A B"], ["A\n"], ["A/B"], [1], ["A:BAD"]],
)
def test_video_input_caps(sequence):
    assert (
        TestClient(app).post("/api/generate-video", json={"sequence": sequence}).status_code == 422
    )


def test_video_caps_accept_boundary_and_fs(monkeypatch):
    generate = Mock(return_value=VideoResult(video_url="/generated/test.mp4", missing_glosses=[]))
    monkeypatch.setattr(video, "generate_video_result", generate)
    sequence = ["A" * 64, "FS:O'NEIL", "FS:12", "HELLO-WORLD"] + ["HELLO"] * 46
    assert (
        TestClient(app).post("/api/generate-video", json={"sequence": sequence}).status_code == 200
    )
    generate.assert_called_once_with(sequence)


def test_expiry_with_fake_mtimes_and_startup(tmp_path, monkeypatch):
    for name, mtime in (
        ("old.mp4", 100),
        ("fresh.mp4", 4000),
        ("boundary.mp4", 400),
        (".gitkeep", 0),
    ):
        path = tmp_path / name
        path.write_text("fixture")
        os.utime(path, (mtime, mtime))
    directory = tmp_path / ".video-active"
    directory.mkdir()
    (directory / "active.mp4").write_text("fixture")
    cleanup_generated(tmp_path, 60, now=4000)
    assert not (tmp_path / "old.mp4").exists()
    assert (tmp_path / "fresh.mp4").exists() and (tmp_path / "boundary.mp4").exists()
    assert (tmp_path / ".gitkeep").exists() and (directory / "active.mp4").exists()
    monkeypatch.setattr(settings, "GENERATED_PATH", tmp_path)
    with TestClient(app):
        assert not (tmp_path / "fresh.mp4").exists()
    assert (tmp_path / ".gitkeep").exists()


def test_periodic_cleanup_and_cancellation(tmp_path, monkeypatch):
    from services import generated_cleanup

    calls = []

    async def sleep(seconds):
        calls.append(seconds)
        if len(calls) == 2:
            raise asyncio.CancelledError

    cleanup = Mock()
    monkeypatch.setattr(generated_cleanup.asyncio, "sleep", sleep)
    monkeypatch.setattr(generated_cleanup, "cleanup_generated", cleanup)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(cleanup_loop(tmp_path, 60))
    assert calls == [600, 600]
    cleanup.assert_called_once_with(tmp_path, 60)


def test_sign_asset_allowlist_and_sanitized_manifest(tmp_path, monkeypatch):
    from models.sign import Sign
    from api import assets

    monkeypatch.setattr(settings, "SIGN_DATA_PATH", tmp_path)
    (tmp_path / "alphabet").mkdir()
    (tmp_path / "clips").mkdir()
    sign = Sign(id="fixture", gloss="FIXTURE", clip="clips/fixture.json", video="fixture.mp4")
    repo = Mock()
    repo.search.return_value = [sign]
    monkeypatch.setattr(assets, "get_repository", lambda: repo)
    entry = {
        "clip": "a.json",
        "source": "synthetic fixture",
        "licence": "test-only",
        "signer": "synthetic",
        "review_status": "unverified",
        "duration": 1,
        "reviewer": "private-fixture",
        "review_history": [{"private": True}],
        "import_hash": "private",
        "evidence": "private",
    }
    (tmp_path / "alphabet/manifest.json").write_text(
        json.dumps(
            {
                "version": 1,
                "characters": {
                    "A": entry,
                    "B": {**entry, "clip": "b.json", "review_decision": "rejected"},
                },
            }
        )
    )
    for relative in (
        "signs.json",
        "clips/fixture.json",
        "fixture.mp4",
        "alphabet/a.json",
        "alphabet/b.json",
        "clips/unlisted.json",
        "permissions.json",
    ):
        (tmp_path / relative).write_text("{}")
    client = TestClient(app)
    for relative in (
        "signs.json",
        "alphabet/manifest.json",
        "clips/unlisted.json",
        "permissions.json",
        "alphabet/b.json",
    ):
        assert client.get(f"/signs/{relative}").status_code == 404
    for relative in ("clips/fixture.json", "fixture.mp4", "alphabet/a.json"):
        assert client.get(f"/signs/{relative}").status_code == 200
    public = client.get("/api/alphabet").json()
    assert public == {
        "version": 1,
        "characters": {"A": {key: entry[key] for key in assets.PUBLIC_FIELDS}},
    }
    private_clip = {
        "version": 1,
        "keys": [],
        "reviewer": "private-fixture",
        "review_history": [{"evidence": "private"}],
        "import_hash": "private",
        "evidence": "private",
    }
    (tmp_path / "alphabet/a.json").write_text(json.dumps(private_clip))
    assert client.get("/signs/alphabet/a.json").json() == {"version": 1, "keys": []}
    (tmp_path / "alphabet/a.json").write_text(
        json.dumps({**private_clip, "review_decision": "rejected"})
    )
    assert client.get("/signs/alphabet/a.json").status_code == 404
    sign.clip_review_decision = "rejected"
    assert client.get("/signs/clips/fixture.json").status_code == 404
    sign.review_decision = "rejected"
    assert client.get("/signs/fixture.mp4").status_code == 404
    sign.review_decision = None
    sign.video = "../outside.mp4"
    assert client.get("/signs/%2e%2e/outside.mp4").status_code == 404


def test_sequence_build_runs_off_event_loop(monkeypatch):
    import threading

    original = gloss_service.SignSequenceService.build
    main_thread = threading.get_ident()
    seen = []

    def build(self, gloss):
        seen.append(threading.get_ident())
        return original(self, gloss)

    monkeypatch.setattr(gloss_service.SignSequenceService, "build", build)
    asyncio.run(gloss_service.translate(TranslationRequest(text="hello")))
    assert seen and seen[0] != main_thread


def test_yaml_cache_hit_reload_and_mutation_isolation(tmp_path, monkeypatch):
    path = tmp_path / "rules.yaml"
    path.write_text("version: 1\nrules: []\ngrammar: []\n")
    parse = Mock(wraps=marker_service.yaml.safe_load)
    monkeypatch.setattr(marker_service.yaml, "safe_load", parse)
    first = marker_service.load_config(path)
    first.rules.append("request mutation")
    assert marker_service.load_config(path).rules == []
    assert parse.call_count == 1
    before = path.stat().st_mtime_ns
    path.write_text("version: 2\nrules: []\ngrammar: []\n")
    os.utime(path, ns=(before + 1_000_000, before + 1_000_000))
    with pytest.raises(ValueError):
        marker_service.load_config(path)
    assert parse.call_count == 2


def test_examples_cache_hit_reload_and_allowed_filter(tmp_path, monkeypatch):
    path = tmp_path / "examples.jsonl"
    row = {"english": "synthetic fixture", "gloss": ["HELLO"], "review_status": "unverified"}
    path.write_text(json.dumps(row) + "\n")
    parse = Mock(wraps=grammar_service.json.loads)
    monkeypatch.setattr(grammar_service.json, "loads", parse)
    assert grammar_service.verified_examples(["HELLO"], path) == []
    assert grammar_service.verified_examples([], path) == []
    assert parse.call_count == 1
    before = path.stat().st_mtime_ns
    # Invalid content must be revalidated; no fabricated signer verification.
    path.write_text("{invalid}\n")
    os.utime(path, ns=(before + 1_000_000, before + 1_000_000))
    with pytest.raises(ValueError):
        grammar_service.verified_examples(["HELLO"], path)
    assert parse.call_count == 2
