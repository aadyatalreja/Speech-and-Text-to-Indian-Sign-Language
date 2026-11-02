from fastapi.testclient import TestClient
from main import app

c = TestClient(app)


def test_health():
    assert c.get("/api/health").json() == {"status": "ok", "service": "signai"}


def test_translate():
    r = c.post("/api/translate", json={"text": "I need help"})
    assert r.status_code == 200 and r.json()["gloss"] == ["I", "HELP", "NEED"]
    assert r.json()["sequence"][0]["available"] is True


def test_empty():
    assert c.post("/api/translate", json={"text": "   "}).status_code == 422


def test_unknown_sign_api():
    r = c.post("/api/translate", json={"text": "I want quantum"}).json()
    assert "QUANTUM" in r["unknown_signs"] and r["notice"]
    assert "FS:QUANTUM" in r["gloss"]


def test_name_and_digits_api():
    r = c.post("/api/translate", json={"text": "Priya 12"}).json()
    assert r["gloss"] == ["FS:PRIYA", "FS:1", "FS:2"]
    assert r["unknown_signs"] == ["PRIYA", "1", "2"]
    assert "not the ISL alphabet" in r["notice"]


def test_name_and_digits_stream():
    with c.websocket_connect("/api/translate/stream") as ws:
        ws.send_json({"text": "Priya 1"})
        meta = ws.receive_json()
        assert meta["gloss"] == ["FS:PRIYA", "FS:1"]
        assert ws.receive_json()["item"]["gloss"] == "FS:PRIYA"
        assert ws.receive_json()["item"]["gloss"] == "FS:1"
        assert ws.receive_json()["unknown_signs"] == ["PRIYA", "1"]


def test_video_without_assets():
    assert c.post("/api/generate-video", json={"sequence": ["I"]}).status_code == 422


def test_ws():
    with c.websocket_connect("/api/translate/stream") as ws:
        ws.send_json({"text": "Hello"})
        assert [ws.receive_json()["type"] for _ in range(3)] == ["understanding", "sign", "done"]


def test_signs_static_mount_serves_clips(tmp_path):
    from config import settings
    from services.sign_repository import get_repository

    clip = settings.SIGN_DATA_PATH / "clips" / "_pytest_clip.json"
    clip.parent.mkdir(exist_ok=True)
    clip.write_text('{"version":1}')
    sign = get_repository().search("")[0]
    previous = sign.clip
    sign.clip = "clips/_pytest_clip.json"
    try:
        assert c.get("/signs/clips/_pytest_clip.json").json() == {"version": 1}
    finally:
        sign.clip = previous
        clip.unlink()


def test_stream_builds_one_item_after_understanding(monkeypatch):
    import asyncio
    from threading import get_ident
    from api import translation

    events, builds = [], []
    main_thread = get_ident()
    original = translation.SignSequenceService.build

    def build(self, tokens):
        assert len(tokens) == 1
        assert events[0]["type"] == "understanding"
        assert get_ident() != main_thread
        if builds:
            assert events[-1]["type"] == "sign"
        builds.append(tokens[0].gloss)
        return original(self, tokens)

    class Socket:
        client = None

        async def accept(self):
            pass

        async def receive_json(self):
            return {"text": "I need help"}

        async def send_json(self, value):
            events.append(value)

        async def close(self, **kwargs):
            pass

    monkeypatch.setattr(translation.SignSequenceService, "build", build)
    asyncio.run(translation.stream(Socket()))
    assert builds == ["I", "HELP", "NEED"]
    assert [e["type"] for e in events] == ["understanding", "sign", "sign", "sign", "done"]
    assert [e["item"]["sequence_index"] for e in events[1:-1]] == [0, 1, 2]
    assert events[-2]["item"]["pause_after"] == 0
    assert events[1]["item"]["pause_after"] > 0
