import os
import math
import re
from urllib.parse import urlsplit
from pathlib import Path
from dotenv import load_dotenv

BASE = Path(__file__).parent
load_dotenv(BASE.parent / ".env", override=False)

DEFAULT_LLM_MODEL = "claude-sonnet-5-5"  # official model overview checked 2026-10-31
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"  # Groq-hosted model ID; confirm in your Groq console


def numeric(env, name, default, low, high):
    value = float(env.get(name, default))
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be finite and within {low}..{high}")
    return value


class Settings:
    def __init__(self, environ=None):
        env = os.environ if environ is None else environ
        self.LLM_PROVIDER = env.get("LLM_PROVIDER", "mock")
        if self.LLM_PROVIDER not in {"mock", "api", "groq"}:
            raise ValueError("LLM_PROVIDER must be mock, api or groq")
        self.LLM_API_KEY = env.get("LLM_API_KEY", "")
        self.LLM_TIMEOUT_SECONDS = numeric(env, "LLM_TIMEOUT_SECONDS", 20, 0.1, 300)
        self.LLM_MAX_RETRIES = int(env.get("LLM_MAX_RETRIES", "2"))
        self.LLM_CACHE_SIZE = int(env.get("LLM_CACHE_SIZE", "256"))
        if not 0 <= self.LLM_MAX_RETRIES <= 10 or self.LLM_CACHE_SIZE < 0:
            raise ValueError("LLM_MAX_RETRIES must be within 0..10 and LLM_CACHE_SIZE nonnegative")
        self.LLM_CACHE_TTL_SECONDS = numeric(env, "LLM_CACHE_TTL_SECONDS", 300, 0.1, 86400)
        self.LLM_ORDERING = env.get("LLM_ORDERING", "code")
        if self.LLM_ORDERING not in {"code", "model"}:
            raise ValueError("LLM_ORDERING must be code or model")
        synonym = env.get("ENABLE_SYNONYM_FALLBACK", "false").strip().lower()
        if synonym not in {"true", "false"}:
            raise ValueError("ENABLE_SYNONYM_FALLBACK must be true or false")
        self.ENABLE_SYNONYM_FALLBACK = synonym == "true"
        indic = env.get("ENABLE_DEMO_INDIC_GLOSSARY", "true").strip().lower()
        if indic not in {"true", "false"}:
            raise ValueError("ENABLE_DEMO_INDIC_GLOSSARY must be true or false")
        self.ENABLE_DEMO_INDIC_GLOSSARY = indic == "true"
        if self.LLM_PROVIDER == "groq":
            # Groq serves open models through an OpenAI-compatible API; LLM_API_KEY holds the Groq key.
            self.LLM_MODEL = env.get("LLM_MODEL", DEFAULT_GROQ_MODEL).strip()
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/:-]*", self.LLM_MODEL):
                raise ValueError("LLM_MODEL must be a Groq model ID, e.g. llama-3.3-70b-versatile")
        else:
            self.LLM_MODEL = env.get("LLM_MODEL", DEFAULT_LLM_MODEL).strip()
            if not re.fullmatch(r"claude-[a-z0-9]+(?:-[a-z0-9]+)*", self.LLM_MODEL):
                raise ValueError(
                    "LLM_MODEL must be a Claude API model ID; see official model overview"
                )
        self.GROQ_BASE_URL = env.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
        self.LLM_MAX_TOKENS = int(env.get("LLM_MAX_TOKENS", "2048"))
        if not 256 <= self.LLM_MAX_TOKENS <= 8192:
            raise ValueError("LLM_MAX_TOKENS must be within 256..8192")
        self.TARGET_SIGN_LANGUAGE = env.get("TARGET_SIGN_LANGUAGE", "ISL")
        self.SIGN_DATA_PATH = Path(env.get("SIGN_DATA_PATH", BASE / "data" / "signs"))
        self.FEEDBACK_PATH = Path(env.get("FEEDBACK_PATH", BASE / "data/feedback/reports.jsonl"))
        self.FEEDBACK_MAX_BYTES = int(
            numeric(env, "FEEDBACK_MAX_BYTES", 5_000_000, 1024, 100_000_000)
        )
        self.RATE_LIMIT_FEEDBACK_PER_MIN = int(
            numeric(env, "RATE_LIMIT_FEEDBACK_PER_MIN", 5, 1, 1000)
        )
        self.GENERATED_PATH = Path(env.get("GENERATED_VIDEO_PATH", BASE / "generated"))
        self.INTER_SIGN_PAUSE = numeric(env, "INTER_SIGN_PAUSE", 0.2, 0, 5)
        self.AVATAR_TRANSITION_SECONDS = numeric(env, "AVATAR_TRANSITION_SECONDS", 0.18, 0, 1)
        self.DEMO_SIGN_DURATION = numeric(env, "DEMO_SIGN_DURATION", 1.2, 0.1, 10)
        self.FFMPEG_BINARY = env.get("FFMPEG_BINARY", "ffmpeg")
        self.FFPROBE_BINARY = env.get("FFPROBE_BINARY", "ffprobe")
        self.CORS_ORIGINS = [
            origin.strip() for origin in env.get("CORS_ORIGINS", "http://localhost:5173").split(",")
        ]
        for origin in self.CORS_ORIGINS:
            parsed = urlsplit(origin)
            try:
                port = parsed.port
            except ValueError as exc:
                raise ValueError("CORS_ORIGINS must contain HTTP(S) origins") from exc
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.path
                or parsed.query
                or parsed.fragment
                or any(ch.isspace() for ch in origin)
                or any(ch in origin for ch in "\\?#")
                or parsed.netloc.endswith(":")
                or port == 0
            ):
                raise ValueError("CORS_ORIGINS must contain HTTP(S) origins without paths")
        for name, default in (
            ("RATE_LIMIT_TRANSLATE_PER_MIN", 30),
            ("RATE_LIMIT_VIDEO_PER_MIN", 5),
            ("MAX_VIDEO_JOBS", 2),
            ("GENERATED_TTL_MINUTES", 60),
        ):
            value = int(env.get(name, default))
            if value < 1:
                raise ValueError(f"{name} must be a positive integer")
            setattr(self, name, value)


settings = Settings()
