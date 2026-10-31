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

def test_video_without_assets():
    assert c.post("/api/generate-video", json={"sequence": ["I"]}).status_code == 422

def test_ws():
    with c.websocket_connect("/api/translate/stream") as ws:
        ws.send_json({"text": "Hello"})
        assert [ws.receive_json()["type"] for _ in range(3)] == ["understanding", "sign", "done"]

def test_signs_static_mount_serves_clips(tmp_path):
    from config import settings
    clip = settings.SIGN_DATA_PATH / "clips" / "_pytest_clip.json"
    clip.parent.mkdir(exist_ok=True)
    clip.write_text('{"version":1}')
    try:
        assert c.get("/signs/clips/_pytest_clip.json").json() == {"version": 1}
    finally:
        clip.unlink()
