"""
app/core/logging.py
-------------------
Centralised structured logging configuration for the FastAPI application.
Uses Python's stdlib logging with a JSON-friendly formatter for production
and a colour-friendly formatter for development.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()
_configured = False


def configure_logging() -> None:
    """Configure root logger + app logger. Idempotent."""
    global _configured
    if _configured:
        return
    _configured = True

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # ── Formatter ────────────────────────────────────────────────────────────
    fmt = (
        "%(asctime)s | %(levelname)-8s | %(name)-24s | "
        "%(filename)s:%(lineno)d | %(message)s"
    )
    formatter = logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")

    # ── Console handler ───────────────────────────────────────────────────────
    import io
    stdout_utf8 = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace") if hasattr(sys.stdout, "buffer") else sys.stdout
    console_handler = logging.StreamHandler(stdout_utf8)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # ── File handler (rotating, 10 MB, keep 5 backups) ───────────────────────
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # ── Root logger ───────────────────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(level)
    # Avoid adding duplicate handlers on reload
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(console_handler)
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        root.addHandler(file_handler)

    # Quiet noisy third-party loggers
    for noisy in ("uvicorn.access", "passlib", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (configure_logging must have been called first)."""
    return logging.getLogger(name)
