import asyncio
import json
from types import SimpleNamespace

import httpx
from fastapi import HTTPException

import isign_worker
from models.translation import TranslationRequest
from services import isign
from services.gloss_service import translate


def test_private_worker_to_translation(monkeypatch, tmp_path):
    uid = "example-video-2"
    pose = tmp_path / f"{uid}.pose"
    pose.touch()
    csv = tmp_path / "examples.csv"
    csv.write_text(f"uid,English\n{uid},Hello there.\nmissing-1,Unknown.\n", encoding="utf-8")
    monkeypatch.setenv("SIGN_AI_ISIGN_CSV", str(csv))
    monkeypatch.setenv("SIGN_AI_ISIGN_POSES", str(tmp_path))
    monkeypatch.setenv("SIGN_AI_ISIGN_TEXT_COLUMN", "English")
    monkeypatch.setenv("SIGN_AI_ISIGN_TOKEN", "x" * 32)
    monkeypatch.setenv("SIGN_AI_ISIGN_URL", "http://localhost")
    isign_worker.index.cache_clear()

    def decode(match_uid, path):
        assert (match_uid, path) == (uid, pose.resolve())
        return {
            "id": uid,
            "version": 2,
            "kind": "dataset",
            "gloss": "ISIGN_SEQUENCE",
            "duration": 1,
            "keys": [{"t": 0, "R": {"p": [-0.2, 0, 0.5]}}, {"t": 1}],
        }

    monkeypatch.setattr(isign_worker, "decode", decode)
    client = httpx.AsyncClient

    def worker_transport(request):
        assert request.url.path == "/retrieve"
        try:
            payload = isign_worker.retrieve(
                TranslationRequest.model_validate(json.loads(request.content)),
                request.headers.get("Authorization", ""),
            )
        except HTTPException as exc:
            return httpx.Response(exc.status_code)
        return httpx.Response(200, json=payload)

    async def exercise():
        transport = httpx.MockTransport(worker_transport)
        async with client(transport=transport, base_url="http://localhost") as direct:
            assert (await direct.post("/retrieve", json={"text": "Hello there"})).status_code == 401
        monkeypatch.setattr(
            isign.httpx, "AsyncClient", lambda **kwargs: client(transport=transport, **kwargs)
        )
        result = await translate(TranslationRequest(text="  HELLO THERE! "))
        assert result.engine == "isign-exact"
        assert result.sequence[0].inline_clip["id"] == uid
        assert result.unknown_signs == []
        assert await isign.retrieve_isign(TranslationRequest(text="Unknown")) is None

    try:
        asyncio.run(exercise())
    finally:
        isign_worker.index.cache_clear()


def test_pose_adapter_keeps_sides_and_confidence():
    import pytest

    np = pytest.importorskip("numpy")
    components = [
        SimpleNamespace(name=name, points=range(size))
        for name, size in isign_worker.COMPONENTS.values()
    ]
    coords = np.zeros((2, 1, 75, 3))
    scores = np.ones((2, 1, 75))
    coords[:, 0, 33] = [60, 25, -10]
    coords[:, 0, 54] = [30, 20, -5]
    scores[1, 0, 54] = 0
    pose = SimpleNamespace(
        header=SimpleNamespace(
            components=components, dimensions=SimpleNamespace(width=100, height=50)
        ),
        body=SimpleNamespace(data=coords, confidence=scores, fps=25),
    )
    adapted = isign_worker.landmark_frames(pose)
    assert adapted["fps"] == 25
    assert adapted["frames"][0]["left_hand"][0] == [0.6, 0.5, -0.1, 1]
    assert adapted["frames"][0]["right_hand"][0] == [0.3, 0.4, -0.05, 1]
    assert "right_hand" not in adapted["frames"][1]
