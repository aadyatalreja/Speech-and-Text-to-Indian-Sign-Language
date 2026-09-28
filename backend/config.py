import os
from pathlib import Path

BASE = Path(__file__).parent

class Settings:
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")  # mock | api
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5")
    TARGET_SIGN_LANGUAGE = os.getenv("TARGET_SIGN_LANGUAGE", "ISL")
    SIGN_DATA_PATH = Path(os.getenv("SIGN_DATA_PATH", BASE / "data" / "signs"))
    GENERATED_PATH = Path(os.getenv("GENERATED_VIDEO_PATH", BASE / "generated"))

settings = Settings()
