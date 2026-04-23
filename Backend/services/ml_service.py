"""
app/services/ml_service.py
--------------------------
Thin adapter that bridges the FastAPI app with the ML-layer
SpamDetectorService.

The SpamDetectorService lives in ml/service.py and is completely
framework-agnostic. This module:
  • Adds ml/ to sys.path at import time (once).
  • Exposes get_spam_detector() as a FastAPI dependency that
    returns the singleton SpamDetectorService.
  • Translates ML-layer exceptions into FastAPI HTTPExceptions.
"""

import sys
from pathlib import Path
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status

# ── Add ml/ to sys.path so we can import ml.service ──────────────────────────
_ML_DIR = Path(__file__).resolve().parents[2] / "ml"
if str(_ML_DIR) not in sys.path:
    sys.path.insert(0, str(_ML_DIR))

# These imports resolve from ml/
import sys
import os
import requests
from service import SpamDetectorService, ServiceError, InvalidInputError, ModelNotLoadedError  # noqa: E402

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger("ml_service")

# ── Module-level types and helpers (Defined early to avoid circular ImportErrors) ──
MLService = Annotated[SpamDetectorService, Depends(lambda: init_spam_detector())]

def translate_ml_error(exc: Exception) -> HTTPException:
    """Convert ML-layer exceptions to appropriate FastAPI HTTPExceptions."""
    if isinstance(exc, ModelNotLoadedError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, InvalidInputError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, ServiceError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

# ── Module-level singleton (loaded once at startup) ───────────────────────────
_detector: Optional[SpamDetectorService] = None
_last_error: Optional[str] = None


def init_spam_detector() -> SpamDetectorService:
    """
    Initialise the SpamDetectorService singleton.
    Called once from app lifespan, or on-demand via dependency.
    """
    global _detector
    if _detector is not None:
        if not _detector._loaded:
            logger.info("[ML] Detector found but not loaded. Retrying load...")
            try:
                _detector._load()
                logger.info(f"[ML] Model {_detector._model_version} loaded successfully on retry.")
            except Exception as e:
                logger.error(f"[ML] ERROR: Retry failed: {e}")
        return _detector
        
    model_url = os.environ.get("MODEL_URL")
    tag = os.environ.get("MODEL_VERSION", settings.MODEL_VERSION)
    
    logger.info(f"[ML] Initializing detector version: {tag}")
    
    detector = SpamDetectorService(
        model_version=tag,
        auto_load=False,
    )
    
    # Ensure model exists or download it
    model_path = _ML_DIR / "models" / f"model_{tag}.pkl"
    
    if not model_path.exists():
        if model_url:
            # Handle Dropbox/Drive links by transforming them to direct download if possible
            if "dropbox.com" in model_url and "dl=1" not in model_url:
                model_url = model_url.replace("dl=0", "dl=1")
                if "dl=1" not in model_url:
                    model_url = model_url + ("&" if "?" in model_url else "?") + "dl=1"
            
            logger.info(f"[ML] Model missing at {model_path}. Downloading from {model_url}...")
            try:
                os.makedirs(model_path.parent, exist_ok=True)
                response = requests.get(model_url, stream=True, timeout=60)
                response.raise_for_status()
                with open(model_path, "wb") as f:
                    size = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            size += len(chunk)
                logger.info(f"[ML] Download complete ({size} bytes): {model_path}")
            except Exception as e:
                logger.error(f"[ML] CRITICAL: Download failed: {e}")
        else:
            logger.warning(f"[ML] WARNING: Model missing and no MODEL_URL provided.")

    try:
        detector._load()
        logger.info(f"[ML] Model {tag} loaded successfully.")
    except Exception as e:
        import traceback
        global _last_error
        _last_error = f"{str(e)}\n{traceback.format_exc()}"
        logger.error(f"[ML] ERROR: Failed to load model: {e}\n{traceback.format_exc()}")
    
    _detector = detector
    return _detector


def get_ml_error() -> Optional[str]:
    return _last_error
