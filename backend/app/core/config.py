from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseModel):
    app_name: str = "BuildTwin Vision"
    api_prefix: str = "/api/v1"
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{REPO_ROOT / 'backend' / 'buildtwin.db'}")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-only-change-me-use-32-bytes-minimum-secret")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 480
    media_root: Path = Path(os.getenv("MEDIA_ROOT", str(REPO_ROOT / "sample_data")))
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", str(100 * 1024 * 1024)))

settings = Settings()
