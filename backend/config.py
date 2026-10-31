import os
import math
import re
from pathlib import Path
from dotenv import load_dotenv

BASE = Path(__file__).parent
load_dotenv(BASE.parent / ".env", override=False)

DEFAULT_LLM_MODEL = "claude-sonnet-5-5"  # official model overview checked 2026-10-31


def numeric(env, name, default, low, high):
    value = float(env.get(name, default))
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be finite and within {low}..{high}")
    return value

class Settings:
    def __init__(self, environ=None):
        env = os.environ if environ is None else environ
        self.LLM_PROVIDER = env.get("LLM_PROVIDER", "mock")
        if self.LLM_PROVIDER not in {"mock", "api"}:
            raise ValueError("LLM_PROVIDER must be mock or api")
        self.LLM_API_KEY = env.get("LLM_API_KEY", "")
        self.LLM_MODEL = env.get("LLM_MODEL", DEFAULT_LLM_MODEL).strip()
        if not re.fullmatch(r"claude-[a-z0-9]+(?:-[a-z0-9]+)*", self.LLM_MODEL):
            raise ValueError("LLM_MODEL must be a Claude API model ID; see official model overview")
        self.LLM_MAX_TOKENS = int(env.get("LLM_MAX_TOKENS", "2048"))
        if not 256 <= self.LLM_MAX_TOKENS <= 8192:
            raise ValueError("LLM_MAX_TOKENS must be within 256..8192")
        self.TARGET_SIGN_LANGUAGE = env.get("TARGET_SIGN_LANGUAGE", "ISL")
        self.SIGN_DATA_PATH = Path(env.get("SIGN_DATA_PATH", BASE / "data" / "signs"))
        self.GENERATED_PATH = Path(env.get("GENERATED_VIDEO_PATH", BASE / "generated"))
        self.INTER_SIGN_PAUSE = numeric(env, "INTER_SIGN_PAUSE", 0.2, 0, 5)
        self.AVATAR_TRANSITION_SECONDS = numeric(env, "AVATAR_TRANSITION_SECONDS", 0.18, 0, 1)
        self.DEMO_SIGN_DURATION = numeric(env, "DEMO_SIGN_DURATION", 1.2, 0.1, 10)
        self.FFMPEG_BINARY = env.get("FFMPEG_BINARY", "ffmpeg")
        self.FFPROBE_BINARY = env.get("FFPROBE_BINARY", "ffprobe")

settings = Settings()
