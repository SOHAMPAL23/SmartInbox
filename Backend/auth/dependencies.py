"""
app/auth/dependencies.py
------------------------
FastAPI dependency functions for authentication and role-based access control.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import decode_access_token
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole

_bearer = HTTPBearer(auto_error=True)


# ── Database session ──────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:
    """Yield an async database session, closing it after the request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


DBSession = Annotated[AsyncSession, Depends(get_db)]


# ── Current user ──────────────────────────────────────────────────────────────

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: DBSession,
) -> User:
    """Validate the Bearer token and return the authenticated User."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ── Role guard ────────────────────────────────────────────────────────────────

async def require_admin(current_user: CurrentUser) -> User:
    """Raise 403 if the authenticated user is not an admin."""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
