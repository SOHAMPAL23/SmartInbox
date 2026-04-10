"""
app/auth/jwt_handler.py
-----------------------
JWT creation and verification using python-jose.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

_ACCESS_TYPE  = "access"
_REFRESH_TYPE = "refresh"


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def create_access_token(
    subject: str,          # typically user.id as string
    role:    str,
    extra:   Optional[Dict[str, Any]] = None,
) -> str:
    """Mint a short-lived access JWT."""
    payload: Dict[str, Any] = {
        "sub":  subject,
        "role": role,
        "type": _ACCESS_TYPE,
        "jti":  str(uuid.uuid4()),
        "iat":  _utc_now(),
        "exp":  _utc_now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Mint a long-lived refresh JWT."""
    payload: Dict[str, Any] = {
        "sub":  subject,
        "type": _REFRESH_TYPE,
        "jti":  str(uuid.uuid4()),
        "iat":  _utc_now(),
        "exp":  _utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate *token*.

    Raises
    ------
    JWTError – if the token is invalid, expired, or tampered with.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def decode_access_token(token: str) -> Dict[str, Any]:
    payload = decode_token(token)
    if payload.get("type") != _ACCESS_TYPE:
        raise JWTError("Not an access token.")
    return payload


def decode_refresh_token(token: str) -> Dict[str, Any]:
    payload = decode_token(token)
    if payload.get("type") != _REFRESH_TYPE:
        raise JWTError("Not a refresh token.")
    return payload
