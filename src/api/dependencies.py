"""Bearer authentication for the non-portal API surface.

This used to be a stub that accepted any token longer than ten characters and
returned ``{"sub": "anonymous"}`` — which is indistinguishable from working until
someone relies on it. It now verifies the same Supabase access tokens the merchant
portal does, so a caller cannot reach a "protected" route with a made-up string.

Nothing mounts it today; it exists so new routers have a real dependency to reach
for instead of re-inventing one.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.portal.supabase import SupabaseAuthError, verify_access_token

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """Validate the bearer token and return its claims.

    Raises 401 for anything that is not a current, correctly-signed session token
    for this project, and 503 if the deployment cannot reach the auth server — a
    configuration failure must not read as "bad password".
    """
    try:
        claims = await verify_access_token(credentials.credentials)
    except SupabaseAuthError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return claims


async def optional_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    """Anonymous when no token is sent; otherwise the verified claims.

    Only for routes that genuinely have a public shape. A caller who sends a
    *broken* token is rejected rather than silently downgraded to anonymous, so a
    typo cannot look like a missing permission.
    """
    if credentials is None:
        return {"sub": "anonymous"}
    return await get_current_user(credentials)
