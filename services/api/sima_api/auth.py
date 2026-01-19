"""
Authentication for lab routes.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from .settings import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    """Login request body."""
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


def create_access_token() -> tuple[str, datetime]:
    """
    Create a JWT access token.

    Returns:
        Tuple of (token, expiry_datetime).
    """
    expires = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours)
    payload = {
        "sub": "lab_user",
        "exp": expires,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires


def verify_token(token: str) -> bool:
    """
    Verify a JWT token.

    Args:
        token: The JWT token to verify.

    Returns:
        True if valid.

    Raises:
        HTTPException if invalid.
    """
    try:
        jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return True
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def require_lab_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> bool:
    """
    Dependency that requires lab authentication.

    If lab_password is not configured, authentication is bypassed.
    """
    # If no password configured, allow access
    if not settings.lab_password:
        return True

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_token(credentials.credentials)


async def optional_lab_auth(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> bool:
    """
    Dependency for optional lab authentication.

    Returns True if authenticated, False otherwise.
    """
    if not settings.lab_password:
        return True

    if not credentials:
        return False

    try:
        verify_token(credentials.credentials)
        return True
    except HTTPException:
        return False


def login(password: str) -> TokenResponse:
    """
    Authenticate with password and return token.

    Args:
        password: The lab password.

    Returns:
        TokenResponse with access token.

    Raises:
        HTTPException if password is incorrect.
    """
    if not settings.lab_password:
        # No password configured, create token anyway
        token, expires = create_access_token()
        return TokenResponse(access_token=token, expires_at=expires)

    if password != settings.lab_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    token, expires = create_access_token()
    return TokenResponse(access_token=token, expires_at=expires)
