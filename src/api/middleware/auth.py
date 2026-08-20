"""JWT authentication dependency for FastAPI."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Optional[str]]:
    """
    Validate JWT token and return user info.

    In production, decode and verify the JWT using the secret from .env.
    For now, accepts any non-empty token as a pass-through.
    """
    token = credentials.credentials

    if not token or len(token) < 10:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # TODO: Implement JWT verification with python-jose
    # For now, accept any reasonable-length token
    return {"sub": "anonymous", "token": token[:20] + "..."}


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict[str, Optional[str]]:
    """Optional authentication — returns anon user if no token provided."""
    if credentials is None:
        return {"sub": "anonymous", "token": None}
    return await get_current_user(credentials)
