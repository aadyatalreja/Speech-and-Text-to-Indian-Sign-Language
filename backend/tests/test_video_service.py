import json
from pathlib import Path
import subprocess

import pytest
from fastapi.testclient import TestClient

from main import app
from services import video_service as video
from services.sign_repository import JsonSignRepository


def fixture_repo(tmp_path, monkeypatch):
    source = tmp_path / "signs"
    source.mkdir()
    for name in ("a's clip.mp4", "b.mp4"):
        (source / name).write_bytes(b"synthetic fixture; mocked FFmpeg")
    database = source / "signs.json"
    database.write_text(json.dumps({"A": {"id": "a", "gloss": "A", "video": "a's clip.mp4"},
        "B": {"id": "b", "gloss": "B", "video": "b.mp4"},
        "C": {"id": "c", "gloss": "C", "video": "absent.mp4"},
        "ESCAPE": {"id": "escape", "gloss": "ESCAPE", "video": "../outside.mp4"}}))
    monkeypatch.setattr(video.settings, "SIGN_DATA_PATH", source)
    monkeypatch.setattr(video.settings, "GENERATED_PATH", tmp_path / "generated")
    monkeypatch.setattr(video, "get_repository", lambda: JsonSignRepository(database))
    return source


def test_collection_preserves_order_repeats_and_reports_missing(tmp_path, monkeypatch):
    source = fixture_repo(tmp_path, monkeypatch)
    paths, missing = video.collect_clips(["A", "FS:A", "C", "B", "A", "ESCAPE"])
    assert paths == [source / "a's clip.mp4", source / "b.mp4", source / "a's clip.mp4"]
    assert missing == ["FS:A", "C", "ESCAPE"]
    assert video.concat_list(3) == "file '0000.mp4'\nfile '0001.mp4'\nfile '0002.mp4'\n"


def test_normalization_and_concat_use_uniform_streams_and_return_missing_notice(tmp_path, monkeypatch):
    source = fixture_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(video.shutil, "which", lambda name: "ffmpeg")
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        if "concat" in command:
            playlist = Path(command[command.index("-i") + 1])
            assert playlist.read_text() == video.concat_list(2)
        Path(command[-1]).write_bytes(b"mock mp4")
    monkeypatch.setattr(video.subprocess, "run", run)
    result = video.generate_video_result(["A", "C", "B"])
    assert result.missing_glosses == ["C"] and "C" in result.notice
    assert len(commands) == 3
    assert commands[0][commands[0].index("-i") + 1] == str(source / "a's clip.mp4")
    for command in commands[:2]:
        assert "libx264" in command and "yuv420p" in command
        filters = command[command.index("-vf") + 1]
        assert "640:480" in filters and "fps=25" in filters and "setsar=1" in filters
    assert "tpad" in commands[0][commands[0].index("-vf") + 1]
    assert "tpad" not in commands[1][commands[1].index("-vf") + 1]
    assert not list(video.settings.GENERATED_PATH.glob(".video-*"))


def test_ffmpeg_failure_cleans_partial_output(tmp_path, monkeypatch):
    fixture_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(video.shutil, "which", lambda name: "ffmpeg")
    def fail(command, **kwargs):
        Path(command[-1]).write_bytes(b"partial")
        raise subprocess.CalledProcessError(1, command)
    monkeypatch.setattr(video.subprocess, "run", fail)
    with pytest.raises(video.VideoError):
        video.generate_video_result(["A"])
    assert list(video.settings.GENERATED_PATH.iterdir()) == []


def test_api_keeps_video_url_and_exposes_missing_details(tmp_path, monkeypatch):
    fixture_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(video.shutil, "which", lambda name: "ffmpeg")
    monkeypatch.setattr(video.subprocess, "run", lambda command, **kwargs: Path(command[-1]).write_bytes(b"mock"))
    response = TestClient(app).post("/api/generate-video", json={"sequence": ["A", "C"]})
    assert response.status_code == 200
    assert response.json()["video_url"].startswith("/generated/")
    assert response.json()["missing_glosses"] == ["C"] and response.json()["notice"]


def test_missing_ffmpeg_has_actionable_error(tmp_path, monkeypatch):
    fixture_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(video.shutil, "which", lambda name: None)
    with pytest.raises(video.VideoError, match="FFmpeg is not installed"):
        video.generate_video_result(["A"])


def test_real_ffmpeg_normalizes_mixed_sample_sizes_and_rates(tmp_path, monkeypatch):
    """Synthetic color cards, not signer footage or sign definitions."""
    imageio = pytest.importorskip("imageio_ffmpeg", reason="Optional real FFmpeg smoke test")
    executable = imageio.get_ffmpeg_exe()
    source = fixture_repo(tmp_path, monkeypatch)
    for name, color, size, fps in (("a's clip.mp4", "red", "320x240", 12), ("b.mp4", "blue", "640x360", 30)):
        subprocess.run([executable, "-nostdin", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={size}:r={fps}:d=0.5",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source / name)], check=True, capture_output=True, timeout=30)
    monkeypatch.setattr(video.shutil, "which", lambda name: executable)
    result = video.generate_video_result(["A", "C", "B"])
    output = video.settings.GENERATED_PATH / Path(result.video_url).name
    reader = imageio.read_frames(str(output), pix_fmt="rgb24")
    metadata = next(reader)
    pixels = list(reader)
    assert metadata["size"] == (640, 480) and metadata["fps"] == 25
    assert len(pixels) >= 29  # both half-second cards plus the inter-sign hold
    assert result.missing_glosses == ["C"]
    # Center pixels verify that both source segments survived normalization.
    center = (240 * 640 + 320) * 3
    assert pixels[0][center] > pixels[0][center + 2]
    assert pixels[-1][center + 2] > pixels[-1][center]
    assert sum(frame[center] > frame[center + 2] for frame in pixels) >= 17
    assert sum(frame[center + 2] > frame[center] for frame in pixels) >= 12
