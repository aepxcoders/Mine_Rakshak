import os
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE, override=True)


@dataclass(frozen=True)
class Settings:
    app_name: str = "MineRakshak Test Backend"
    device_key: str = os.environ.get("DEVICE_KEY", "MRR-DEVICE-001")
    stale_after_seconds: int = int(os.environ.get("STALE_AFTER_SECONDS", "15"))
    camera_url: str = os.environ.get("CAMERA_URL", "")
    cors_origins: tuple[str, ...] = tuple(
        x.strip()
        for x in os.environ.get(
            "CORS_ORIGINS",
            "http://localhost:8080,http://127.0.0.1:8080,http://172.20.10.6:8080",
        ).split(",")
        if x.strip()
    )


settings = Settings()
