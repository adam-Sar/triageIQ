import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _get(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


class Settings:
    def __init__(self) -> None:
        self.google_api_key = _get("GOOGLE_API_KEY", "")
        self.gemini_model = _get("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.simulator_url = _get("SIMULATOR_URL", "http://localhost:8001").rstrip("/")
        self.max_tool_steps = int(_get("MAX_TOOL_STEPS", "5"))
        self.tool_timeout_s = int(_get("TOOL_TIMEOUT_S", "10"))


settings = Settings()
