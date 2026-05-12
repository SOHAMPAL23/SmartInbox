"""
Centralised application settings loaded from environment variables / .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    APP_NAME: str        = "SmartInbox – SMS Spam Detection API"
    APP_VERSION: str     = "2.0.0"
    DEBUG: bool          = False
    ENVIRONMENT: str     = "production" 
    HOST: str  = "0.0.0.0"
    PORT: int  = 8000

    DATABASE_URL: str = "sqlite+aiosqlite:///./smartinbox.db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    SECRET_KEY: str       = "CHANGE_ME_IN_PRODUCTION_USE_32_CHAR_RANDOM_STRING"
    ALGORITHM: str        = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int  = 60 
    REFRESH_TOKEN_EXPIRE_DAYS:   int  = 7
    ML_DIR: Path         = Path(__file__).resolve().parents[2] / "ml"
    MODEL_VERSION: str   = "v8"
    ALLOWED_ORIGINS: List[str] = [
        "https://main.d2tsa0g3cou3c1.amplifyapp.com",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
    ]

    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE:     int = 100
    LOG_LEVEL: str = "INFO"
    LOG_FILE:  str = "logs/api.log"

    # ── Groq LLM API ─────────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str   = "llama3-70b-8192"
    GROQ_FALLBACK_MODEL: str = "llama3-8b-8192"
    GROQ_TIMEOUT_SECONDS: int = 8
    GROQ_MAX_RETRIES: int = 3
    GROQ_ENABLED: bool = True  # Set False to disable Groq (ML+heuristic only)

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
