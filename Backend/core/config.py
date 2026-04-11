"""
app/core/config.py
------------------
Centralised application settings loaded from environment variables / .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    APP_NAME: str        = "SmartInbox – SMS Spam Detection API"
    APP_VERSION: str     = "1.0.0"
    DEBUG: bool          = False
    ENVIRONMENT: str     = "production"   # development | staging | production

    # ── Server ───────────────────────────────────────────────────────────────
    HOST: str  = "0.0.0.0"
    PORT: int  = 8000

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:password@localhost:5432/smartinbox"
    )

    # ── JWT ───────────────────────────────────────────────────────────────────
    SECRET_KEY: str       = "CHANGE_ME_IN_PRODUCTION_USE_32_CHAR_RANDOM_STRING"
    ALGORITHM: str        = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int  = 60      # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS:   int  = 7

    # ── ML ───────────────────────────────────────────────────────────────────
    ML_DIR: Path         = Path(__file__).resolve().parents[2] / "ml"
    MODEL_VERSION: str   = "v1"

    # ── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Pagination ────────────────────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE:     int = 100

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE:  str = "logs/api.log"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton (loaded once at startup)."""
    return Settings()
