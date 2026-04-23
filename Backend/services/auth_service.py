"""
app/services/auth_service.py
-----------------------------
Business logic for user registration, login, and token refresh.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.auth.password import hash_password, verify_password
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

settings = get_settings()
logger = get_logger(__name__)
ADMIN_SETUP_KEY = "SmartInbox@Admin2026"  # change this in production via ADMIN_SETUP_KEY env var


async def register_user(db: AsyncSession, req: RegisterRequest) -> User:
    """
    Register a new user, ensuring unique email and username.

    Raises HTTP 409 if email or username is already taken.
    """
    # ── Uniqueness checks ─────────────────────────────────────────────────────
    email_clean = req.email.lower().strip()
    existing_email = (
        await db.execute(select(User).where(User.email == email_clean))
    ).scalar_one_or_none()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    existing_username = (
        await db.execute(select(User).where(User.username == req.username))
    ).scalar_one_or_none()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already taken.",
        )

    # ── Create user ───────────────────────────────────────────────────────────
    is_admin = req.admin_key == ADMIN_SETUP_KEY

    # If email exists and admin_key matches, upgrade role to admin
    if is_admin:
        existing = (
            await db.execute(select(User).where(User.email == req.email))
        ).scalar_one_or_none()
        if existing:
            if existing.role != UserRole.admin:
                existing.role = UserRole.admin
                await db.commit()
                await db.refresh(existing)
                logger.info("Upgraded to ADMIN │ id=%s │ email=%s", existing.id, existing.email)
            return existing

    user = User(
        email           = email_clean,
        username        = req.username,
        hashed_password = hash_password(req.password),
        role            = UserRole.admin if is_admin else UserRole.user,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    if is_admin:
        logger.info("New ADMIN registered │ id=%s │ email=%s", user.id, user.email)
    else:
        logger.info("New user registered │ id=%s │ email=%s", user.id, user.email)
    return user


async def login_user(db: AsyncSession, req: LoginRequest) -> TokenResponse:
    """
    Authenticate user and return access + refresh tokens.

    Raises HTTP 401 on invalid credentials.
    """
    email_clean = req.email.lower().strip()
    logger.debug("Login attempt │ email=%s", email_clean)

    user = (
        await db.execute(select(User).where(User.email == email_clean))
    ).scalar_one_or_none()

    if not user:
        logger.warning("Login failed: User not found │ email=%s", email_clean)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(req.password, user.hashed_password):
        logger.warning("Login failed: Incorrect password │ email=%s", email_clean)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support.",
        )

    # ── Mint tokens ───────────────────────────────────────────────────────────
    access_token  = create_access_token(subject=str(user.id), role=user.role.value)
    refresh_token = create_refresh_token(subject=str(user.id))

    # ── Update last_login ─────────────────────────────────────────────────────
    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    logger.info("User logged in │ id=%s │ role=%s", user.id, user.role)
    return TokenResponse(
        access_token  = access_token,
        refresh_token = refresh_token,
        expires_in    = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role          = user.role.value,
    )


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    """
    Validate refresh token and mint a new access token.

    Raises HTTP 401 on invalid or expired refresh token.
    """
    from jose import JWTError

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_refresh_token(refresh_token)
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()

    if not user or not user.is_active:
        raise credentials_exception

    access_token  = create_access_token(subject=str(user.id), role=user.role.value)
    new_refresh   = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token  = access_token,
        refresh_token = new_refresh,
        expires_in    = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role          = user.role.value,
    )
