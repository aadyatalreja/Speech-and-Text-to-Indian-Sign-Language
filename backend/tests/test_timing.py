import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from config import settings
from models.sign import Sign
from services.sequence_service import SignSequenceService
from services.sign_repository import JsonSignRepository
from services import timing_service as timing


def test_clip_file_duration_and_configured_pause(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SIGN_DATA_PATH", tmp_path)
    monkeypatch.setattr(settings, "INTER_SIGN_PAUSE", 0.35)
    (tmp_path / "clip.json").write_text(json.dumps({"version": 1, "duration": 2.75}))
    database = tmp_path / "signs.json"
    database.write_text(json.dumps({"HELLO": {"id": "hello", "gloss": "HELLO", "clip": "clip.json"}}))
    sequence, _ = SignSequenceService(JsonSignRepository(database)).build(["HELLO", "HELLO"], speed=0.5)
    assert sequence[0].duration == 5.5 and sequence[0].timing_source == "clip"
    assert sequence[0].clip_duration == 5.5 and sequence[0].pause_after == 0.7
    assert sequence[1].pause_after == 0 and sequence[1].sequence_index == 1
    (tmp_path / "clip.json").write_text(json.dumps({"version": 1, "duration": 3.12345}))
    assert timing.item_timing(Sign(id="h", gloss="HELLO", clip="clip.json"), "HELLO")[0] == 3.12345


def test_video_probe_and_metadata_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SIGN_DATA_PATH", tmp_path)
    (tmp_path / "sample.mp4").write_bytes(b"fixture")
    monkeypatch.setattr(timing.shutil, "which", lambda binary: "fake-ffprobe")
    calls = []
    def probe(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(stdout='{"streams":[{"duration":"4.25"}],"format":{"duration":"5.0"}}')
    monkeypatch.setattr(timing.subprocess, "run", probe)
    sign = Sign(id="h", gloss="HELLO", video="sample.mp4", video_duration=2)
    assert timing.item_timing(sign, "HELLO")[:2] == (4.25, "video")
    assert timing.item_timing(sign, "HELLO")[0] == 4.25 and len(calls) == 1
    monkeypatch.setattr(timing.shutil, "which", lambda binary: None)
    assert timing.item_timing(sign, "HELLO")[:2] == (2, "video")


def test_only_spelling_uses_length_formula():
    assert timing.item_timing(None, "FS:PRIYA")[:2] == (1.1, "spelling_estimate")
    short = timing.item_timing(Sign(id="a", gloss="A"), "A")
    long = timing.item_timing(Sign(id="b", gloss="VERY_LONG_GLOSS"), "VERY_LONG_GLOSS")
    assert short[:2] == long[:2] == (settings.DEMO_SIGN_DURATION, "demo_estimate")


@pytest.mark.parametrize("speed", [0, -1, float("nan"), float("inf")])
def test_bad_speed_is_rejected(speed):
    with pytest.raises(ValueError): SignSequenceService().build(["HELLO"], speed=speed)
