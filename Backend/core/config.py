"""
Centralised application settings loaded from environment variables / .env file.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Any

from pydantic import field_validator
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
    MODEL_VERSION: str   = "v7"
    ALLOWED_ORIGINS: Any = [
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

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if not v:
            return v
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Clean query parameters for asyncpg compatibility
        if "postgresql+asyncpg://" in v:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            try:
                parsed = urlparse(v)
                query_params = parse_qs(parsed.query)
                if "sslmode" in query_params:
                    sslmode_val = query_params.pop("sslmode")[0]
                    if sslmode_val in ("require", "verify-ca", "verify-full"):
                        query_params["ssl"] = ["require"]
                query_params.pop("channel_binding", None)
                new_query = urlencode(query_params, doseq=True)
                v = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment
                ))
            except Exception:
                pass
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: any) -> List[str]:
        if isinstance(v, str):
            try:
                import json
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except Exception:
                pass
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

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
