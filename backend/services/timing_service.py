"""Measured asset timing with explicit, non-linguistic fallback estimates."""
import json
import logging
import math
from pathlib import Path
import shutil
import subprocess
from functools import lru_cache

from config import settings

log = logging.getLogger("signai.timing")


def positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def asset_path(relative):
    if not relative:
        return None
    root = settings.SIGN_DATA_PATH.resolve()
    path = (root / relative).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


@lru_cache(maxsize=512)
def _clip_duration(path, mtime, size):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        duration = data.get("duration")
        return float(duration) if data.get("version") == 1 and positive(duration) else None
    except (OSError, ValueError, AttributeError):
        return None


@lru_cache(maxsize=512)
def _video_duration(path, mtime, size, probe):
    try:
        result = subprocess.run([probe, "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=duration:format=duration", "-of", "json", path], capture_output=True, text=True, check=True, timeout=10)
        data = json.loads(result.stdout)
        candidates = [stream.get("duration") for stream in data.get("streams", [])] + [data.get("format", {}).get("duration")]
        for value in candidates:
            try:
                duration = float(value)
                if positive(duration):
                    return duration
            except (ValueError, TypeError):
                continue
    except (OSError, ValueError, subprocess.SubprocessError):
        log.warning("Video duration probe failed; using disclosed fallback")
    return None


def durations(sign):
    clip = asset_path(sign.clip) if sign else None
    video = asset_path(sign.video) if sign else None
    clip_seconds, video_seconds = None, None
    if clip:
        stat = clip.stat()
        clip_seconds = _clip_duration(str(clip), stat.st_mtime_ns, stat.st_size)
        if clip_seconds is None and positive(sign.duration):
            clip_seconds = float(sign.duration)
    if video and (probe := shutil.which(settings.FFPROBE_BINARY)):
        stat = video.stat()
        video_seconds = _video_duration(str(video), stat.st_mtime_ns, stat.st_size, probe)
    if video_seconds is None and video and positive(sign.video_duration):
        video_seconds = float(sign.video_duration)
    return clip_seconds, video_seconds


def item_timing(sign, gloss):
    clip, video = durations(sign)
    if clip is not None:
        return clip, "clip", clip, video
    if video is not None:
        return video, "video", clip, video
    if gloss.upper().startswith("FS:"):
        return 0.6 + 0.1 * len(gloss[3:]), "spelling_estimate", clip, video
    return settings.DEMO_SIGN_DURATION, "demo_estimate", clip, video
