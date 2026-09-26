"""Authentication and merchant-scope dependencies for the portal.

Every portal read is scoped: a session resolves to a set of ``merchant_key``
values, and queries filter on that set. A request that asks for a workspace the
caller does not belong to is refused with 403 rather than silently widened or
emptied — leaking another merchant's ledger would be the exact opposite of what
this product is for.

The bearer token is a Supabase access token, verified against the project's JWKS
in :mod:`src.portal.supabase`. The portal mints no tokens and holds no secrets:
``sub`` is the GoTrue user id, and ``portal_users.auth_user_id`` is what ties it
to a set of workspaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_session
from src.core.models import MerchantMembership, PortalUser
from src.portal import supabase
from src.portal.supabase import SupabaseAuthError

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AccessScope:
    """What an authenticated caller may see."""

    user: PortalUser
    merchants: tuple[str, ...]
    roles: dict[str, str]

    def resolve(self, requested: str | None) -> tuple[str, ...]:
        """Return the merchant keys a query should be filtered to."""
        if requested is None:
            return self.merchants
        if requested not in self.merchants:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"you are not a member of merchant '{requested}'",
            )
        return (requested,)

    def role_in(self, merchant_key: str) -> str:
        return self.roles.get(merchant_key, "read")

    def require(self, merchant_key: str, *roles: str) -> None:
        """Gate a write action on membership plus a role, or refuse it."""
        current = self.roles.get(merchant_key)
        if current is None:
            raise HTTPException(status_code=403, detail=f"not a member of merchant '{merchant_key}'")
        if roles and current not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"role '{current}' may not perform this action (needs {'/'.join(roles)})",
            )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> PortalUser:
    """Resolve a Supabase access token to an active portal user."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = await supabase.verify_access_token(credentials.credentials)
    except SupabaseAuthError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    subject = str(claims.get("sub") or "")
    try:
        # Parse before querying: a malformed subject should be a 401, not a
        # PostgreSQL type error surfacing as a 500.
        UUID(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token subject is not a user id",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = (
        await session.execute(select(PortalUser).where(PortalUser.auth_user_id == subject))
    ).scalar_one_or_none()
    if user is None:
        # A valid GoTrue session with no portal row means the account was created
        # outside the portal (dashboard, or a direct auth call) and owns no
        # workspace yet. It is authenticated, but there is nothing to show.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="this account is not linked to a portal workspace",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="account disabled")
    return user


async def get_scope(
    user: PortalUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AccessScope:
    """Attach the caller's workspaces to the request."""
    rows = (
        await session.execute(select(MerchantMembership).where(MerchantMembership.user_id == user.id))
    ).scalars().all()
    merchants = tuple(sorted({r.merchant_key for r in rows}))
    roles = {r.merchant_key: (r.role or "owner") for r in rows}
    return AccessScope(user=user, merchants=merchants, roles=roles)


def merchant_param(
    scope: AccessScope = Depends(get_scope),
    merchant: str | None = Query(None, description="Narrow to one workspace you belong to"),
) -> tuple[str, ...]:
    """Dependency that yields the merchant keys a read should be filtered to."""
    return scope.resolve(merchant)
