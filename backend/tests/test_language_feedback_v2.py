import asyncio
from datetime import datetime, timezone
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
import pytest

from config import settings
from main import app
from models.markers import NonManualMarkers
from models.translation import TranslationRequest
from services import llm_service
from services.gloss_service import translate
from tools import mediapipe_to_clip as converter
from tools.review_assets import list_feedback, main as review_main
from test_mediapipe_to_clip import frames, hand


def fake_client(monkeypatch, english="I need help"):
    create = AsyncMock(
        return_value=SimpleNamespace(
            content=[
                SimpleNamespace(type="tool_use", name="emit_english", input={"text": english})
            ],
            stop_reason="tool_use",
        )
    )
    monkeypatch.setattr(settings, "LLM_PROVIDER", "api")
    monkeypatch.setattr(settings, "LLM_API_KEY", "fake-test-key")
    monkeypatch.setattr(
        llm_service, "_client", SimpleNamespace(messages=SimpleNamespace(create=create))
    )
    return create


def test_hindi_is_translated_cached_and_only_english_enters_gloss(monkeypatch):
    create = fake_client(monkeypatch)
    seen = []

    async def understand(text):
        seen.append(text)
        return llm_service.mock_transform(text), "mock-test", None

    monkeypatch.setattr(llm_service, "understand", understand)
    request = TranslationRequest(text="मुझे मदद चाहिए", source_language="hi-IN")
    first = asyncio.run(translate(request))
    second = asyncio.run(translate(request))
    assert seen == ["I need help", "I need help"]
    assert first.english_text == second.english_text == "I need help"
    assert first.original_text == request.text
    assert "Machine-translated to English first; not verified." in first.notice
    assert create.await_count == 1
    assert create.call_args.kwargs["tool_choice"]["name"] == "emit_english"


def test_failure_fallback_and_english_never_calls_translation(monkeypatch):
    create = fake_client(monkeypatch)
    create.side_effect = RuntimeError("synthetic failure")
    english, notice = asyncio.run(llm_service.english_input("नमस्ते", "Hindi"))
    assert english == "hello" and "failed" in notice and "demo glossary" in notice
    for language in ("English", "en-IN", "en-US", "en-GB"):
        assert asyncio.run(llm_service.english_input("Hello", language)) == ("Hello", None)
    assert create.await_count == 1


def test_mock_notice_and_websocket_english_intermediate():
    result = asyncio.run(translate(TranslationRequest(text="ನಮಸ್ಕಾರ", source_language="kn-IN")))
    assert result.english_text == "hello" and "demo glossary" in result.notice
    with TestClient(app).websocket_connect("/api/translate/stream") as ws:
        ws.send_json({"text": "नमस्ते", "source_language": "hi-IN"})
        first = ws.receive_json()
        assert first["english_text"] == "hello" and "not verified" in first["notice"]
        while ws.receive_json()["type"] != "done":
            pass


def report():
    return {
        "gloss": "HELLO",
        "sign_id": "hello",
        "sentence": "Hello",
        "note": "Synthetic test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def test_feedback_stores_only_report_fields_and_groups_without_asset_changes(
    tmp_path, monkeypatch, capsys
):
    path = tmp_path / "feedback/reports.jsonl"
    monkeypatch.setattr(settings, "FEEDBACK_PATH", path)
    asset = tmp_path / "signs.json"
    asset.write_text('{"fixture":"unchanged"}')
    before = asset.read_bytes()
    client = TestClient(app)
    for _ in range(2):
        assert client.post("/api/feedback", json=report()).status_code == 204
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert set(rows[0]) == set(report())
    assert asset.read_bytes() == before
    assert {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()} == {
        "signs.json",
        "feedback/reports.jsonl",
    }
    assert list_feedback(path) == [{"gloss": "HELLO", "sign_id": "hello", "count": 2}]
    assert review_main(["feedback", "list", "--file", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)[0]["count"] == 2


def test_feedback_rejects_note_limits_and_storage_cap(tmp_path, monkeypatch):
    path = tmp_path / "reports.jsonl"
    monkeypatch.setattr(settings, "FEEDBACK_PATH", path)
    client = TestClient(app)
    assert client.post("/api/feedback", json={**report(), "note": "x" * 301}).status_code == 422
    assert not path.exists()
    monkeypatch.setattr(settings, "RATE_LIMIT_FEEDBACK_PER_MIN", 1)
    assert client.post("/api/feedback", json=report()).status_code == 204
    saved = path.read_bytes()
    limited = client.post("/api/feedback", json=report())
    assert limited.status_code == 429 and int(limited.headers["Retry-After"]) > 0
    assert path.read_bytes() == saved
    from services.rate_limit import limiter

    limiter.buckets.clear()
    monkeypatch.setattr(settings, "FEEDBACK_MAX_BYTES", len(saved))
    assert client.post("/api/feedback", json=report()).status_code == 507
    assert path.read_bytes() == saved


def test_converter_v2_normalized_smoothed_finger_joints_and_v1_default():
    data = frames(12, lambda t: hand(t), lambda t: hand(t, right=False))
    old = converter.convert(data, "FIXTURE", "fixture")
    new = converter.convert(data, "FIXTURE", "fixture", format=2)
    assert old["version"] == 1 and "fingers" not in old["keys"][0]["R"]
    assert new["version"] == 2 and "monocular depth is noisy" in new["notes"]
    import math

    for key in new["keys"]:
        for side in ("R", "L"):
            assert len(key[side]["fingers"]) == 15
            for q in key[side]["fingers"]:
                assert sum(v * v for v in q) == pytest.approx(1, abs=2e-6)
                assert all(math.isfinite(v) for v in q)
    assert new["keys"][-1]["R"]["fingers"][4][0] > new["keys"][0]["R"]["fingers"][4][0]
    assert new["duration"] == old["duration"]


@pytest.mark.parametrize(
    "value",
    [
        {"gaze": [0, 2]},
        {"gaze": [0, float("nan")]},
        {"mouth_shape": {"round": 1.1}},
        {"mouth_shape": {"wide": -1}},
        {"mouth_shape": {"unknown": 1}},
    ],
)
def test_new_markers_reject_out_of_bounds(value):
    with pytest.raises(ValueError):
        NonManualMarkers(**value)


def test_shipped_markers_remain_demo_and_need_review():
    from services.marker_service import load_rules

    for rule in load_rules():
        assert rule.enabled and rule.nmm.model_dump(exclude_none=True)
        assert rule.review_status == "unverified" and rule.needs_signer_review


def test_non_english_http_uses_intermediate_and_rate_limit_before_second_call(monkeypatch):
    create = fake_client(monkeypatch)

    async def understand(text):
        assert text == "I need help"
        return llm_service.mock_transform(text), "mock-test", None

    monkeypatch.setattr(llm_service, "understand", understand)
    monkeypatch.setattr(settings, "RATE_LIMIT_TRANSLATE_PER_MIN", 1)
    client = TestClient(app)
    payload = {"text": "मुझे मदद चाहिए", "source_language": "hi-IN"}
    response = client.post("/api/translate", json=payload)
    assert response.status_code == 200
    assert response.json()["english_text"] == "I need help"
    assert client.post("/api/translate", json=payload).status_code == 429
    assert create.await_count == 1


def test_converter_cli_format_2(tmp_path):
    data = tmp_path / "landmarks.json"
    output = tmp_path / "clip.json"
    data.write_text(json.dumps(frames(5, lambda t: hand(t))), encoding="utf-8")
    assert converter.main([str(data), str(output), "--gloss", "FIXTURE", "--format", "2"]) == 0
    assert json.loads(output.read_text())["version"] == 2


def test_v2_alphabet_validation_handles_partial_channels_and_rejects_bad_joints(tmp_path):
    from test_alphabet import fixture_manifest
    from tools.validate_signs import validate_alphabet

    path, _, clip = fixture_manifest(tmp_path)
    clip["version"] = 2
    clip["keys"] = [{"t": 0, "R": {"fingers": [[0, 0, 0, 1]] * 15}, "face": {"gaze_x": 0.5}}]
    target = path.parent / "a.json"
    target.write_text(json.dumps(clip))
    assert validate_alphabet(path) == []
    clip["keys"][0]["R"]["fingers"] = [[0, 0, 0, 1]] * 14
    target.write_text(json.dumps(clip))
    assert validate_alphabet(path)
