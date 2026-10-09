"""``/api/v1/auth/*`` — signup, login, refresh, and the workspace switcher.

Credentials belong to Supabase. This module never sees a stored hash and never
mints a token: signup creates a confirmed GoTrue user and a local workspace in
the same request, login exchanges the merchant's password for a Supabase session
and hands it straight back, and every subsequent call is authenticated by
:func:`src.portal.deps.get_current_user` verifying that access token.

Signup creates three things in one transaction: the human, a merchant workspace,
and the owner membership that ties them together. The workspace's
``merchant_key`` is what the bot must send as ``P2POrder.merchant_id``; it is
generated here and shown once on the integration screen, because every ledger
row the portal later displays is partitioned by that string.

Because the remote half cannot join the local transaction, a failed workspace
insert rolls the GoTrue user back too. Leaving an orphaned auth user behind would
burn that email address permanently with no way to sign in.

``/auth/link`` is the Google-shaped exception: nothing is minted there, because
Supabase already created the identity before the browser was redirected back. It
only maps that identity onto a workspace — see the endpoint for why the match is
made on the token subject and never on the email claim.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_session
from src.core.models import (
    KYBStatusEnum,
    KYCStatusEnum,
    Merchant,
    MerchantMembership,
    MerchantStatusEnum,
    PortalUser,
)
from src.portal import supabase
from src.portal.deps import AccessScope, bearer, get_current_user, get_scope
from src.portal.ledger.scoping import order_counts, workspace_names
from src.portal.schemas import (
    AuthResponse,
    CreateMerchantRequest,
    LoginRequest,
    MerchantRef,
    MeResponse,
    OAuthLinkRequest,
    RefreshRequest,
    SignupRequest,
    UserInfo,
)
from src.portal.supabase import Session, SupabaseAuthError

router = APIRouter(prefix="/auth", tags=["portal-auth"])


def _normalise(email: str) -> str:
    return email.strip().lower()


def _http_error(exc: SupabaseAuthError) -> HTTPException:
    """Surface an auth-server failure as the portal's own error shape."""
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


async def _merchant_refs(session: AsyncSession, keys: tuple[str, ...], roles: dict[str, str]) -> list[MerchantRef]:
    if not keys:
        return []
    names = await workspace_names(session, keys)
    counts = await order_counts(session, keys)
    return [
        MerchantRef(
            merchant_key=key,
            business_name=names[key]["business_name"],
            role=roles.get(key, "owner"),
            country=names[key]["country"],
            orders=counts.get(key, 0),
        )
        for key in keys
    ]


def _user_info(user: PortalUser) -> UserInfo:
    return UserInfo(user_id=user.id, email=user.email, name=user.name)


def _display_name(claims: dict[str, Any]) -> str | None:
    """The name Supabase copied off the identity provider's profile, if it sent one.

    Read from ``user_metadata``, which Supabase populates from Google's account
    details. Only ever used when creating a local row: a merchant who already has
    one chose their own name, and a provider profile does not get to rewrite it.
    """
    meta = claims.get("user_metadata") or {}
    name = meta.get("full_name") or meta.get("name")
    return str(name).strip()[:256] if name else None


async def _auth_response(session: AsyncSession, user: PortalUser, state: Session) -> AuthResponse:
    """Shape a Supabase session plus the caller's workspaces into one response."""
    rows = (
        await session.execute(select(MerchantMembership).where(MerchantMembership.user_id == user.id))
    ).scalars().all()
    keys = tuple(sorted({row.merchant_key for row in rows}))
    roles = {row.merchant_key: (row.role or "owner") for row in rows}
    return AuthResponse(
        access_token=state.access_token,
        refresh_token=state.refresh_token,
        expires_in=state.expires_in,
        user=_user_info(user),
        merchants=await _merchant_refs(session, keys, roles),
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    req: SignupRequest, session: AsyncSession = Depends(get_session)
) -> AuthResponse:
    """Create an account plus its first merchant workspace, and sign in."""
    email = _normalise(req.email)
    exists = (await session.execute(select(PortalUser).where(PortalUser.email == email))).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="an account for that email already exists")

    try:
        state = await supabase.create_verified_user(email, req.password, name=req.name)
    except SupabaseAuthError as exc:
        raise _http_error(exc) from exc

    merchant_key = (req.merchant_key or "").strip() or f"merch_{state.user_id[:6]}"
    taken = (await session.execute(select(Merchant).where(Merchant.merchant_key == merchant_key))).scalar_one_or_none()
    if taken is not None:
        # A workspace key is claimed once and for all: two merchants sharing one
        # key would share each other's ledger, which is the scoping bug the whole
        # portal exists to avoid. The auth user has to go with it, or the email is
        # registered but unusable.
        await supabase.delete_user(state.user_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"merchant key '{merchant_key}' is already in use",
        )

    user = PortalUser(auth_user_id=state.user_id, email=email, name=req.name)
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:  # raced another signup
        await session.rollback()
        await supabase.delete_user(state.user_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="an account for that email already exists"
        ) from exc

    session.add(
        Merchant(
            business_name=req.business_name or "My P2P desk",
            merchant_key=merchant_key,
            country=req.country.upper(),
            status=MerchantStatusEnum.APPROVED,
            kyb_status=KYBStatusEnum.NOT_STARTED,
            kyc_status=KYCStatusEnum.NOT_STARTED,
        )
    )
    session.add(MerchantMembership(user_id=user.id, merchant_key=merchant_key, role="owner"))
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        await supabase.delete_user(state.user_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"merchant key '{merchant_key}' is already in use",
        ) from exc

    return await _auth_response(session, user, state)


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    """Email + password, verified by Supabase. Same error for a wrong password and
    an unknown account, so the endpoint cannot be used to enumerate merchants."""
    email = _normalise(req.email)
    try:
        state = await supabase.sign_in(email, req.password)
    except SupabaseAuthError as exc:
        if exc.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="email or password is incorrect"
            ) from exc
        raise _http_error(exc) from exc

    user = (
        await session.execute(select(PortalUser).where(PortalUser.auth_user_id == state.user_id))
    ).scalar_one_or_none()
    if user is None:
        # Authenticated against Supabase but unknown to the portal: the account was
        # made in the dashboard or by an admin call, so it owns no workspace.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="this account is not linked to a portal workspace"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="account disabled")

    user.last_login_at = datetime.now(UTC).replace(tzinfo=None)
    return await _auth_response(session, user, state)


@router.post("/link", response_model=MeResponse)
async def link_oauth_identity(
    req: OAuthLinkRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    """Give a Google-signed merchant the workspace half of an account.

    Supabase proves *who* someone is; it says nothing about which ledger rows they
    may read. Those live here, so the first Google return has to either find the
    caller's portal account or open one. Both halves of that decision are made
    against ``sub``, never against the email claim:

    * A merchant who already signed up with email + password keeps their history,
      because GoTrue links a Google identity onto the confirmed user it already has
      and reissues the *same* subject — so ``auth_user_id`` matches directly.
    * A brand-new merchant gets a desk, the way signup creates one.

    Matching on email instead would let anyone register a Google address that
    duplicates a merchant's and be handed that merchant's ledger, so a subject that
    collides with a *different* account's subject is refused, not merged.

    Idempotent by design: the frontend calls this on every Google return, and a
    second call must not create a second workspace.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = await supabase.verify_access_token(credentials.credentials)
    except SupabaseAuthError as exc:
        raise _http_error(exc) from exc

    subject = str(claims.get("sub") or "")
    try:
        # Same guard as deps.get_current_user: a malformed subject must be a 401,
        # not a type error from the Uuid column surfacing as a 500.
        UUID(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token subject is not a user id",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    email = _normalise(str(claims.get("email") or ""))
    if not email:
        raise HTTPException(status_code=401, detail="the signed-in identity carries no email")

    user = (
        await session.execute(select(PortalUser).where(PortalUser.auth_user_id == subject))
    ).scalar_one_or_none()
    if user is None:
        claimed = (await session.execute(select(PortalUser).where(PortalUser.email == email))).scalar_one_or_none()
        if claimed is not None:
            # GoTrue chose not to fold this identity into the existing user, which
            # is its own judgement that the address is not proven to belong to the
            # caller. Merging it here would override that decision.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="an account for this email already exists — sign in with your password to link Google",
            )
        user = PortalUser(auth_user_id=subject, email=email, name=_display_name(claims))
        session.add(user)
        try:
            await session.flush()
        except IntegrityError as exc:  # raced another Google return on the same subject
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="an account for this email already exists"
            ) from exc

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="account disabled")

    # Signup can be answered with no name at all; a Google profile usually has one.
    # Filling the gap only ever writes the local copy, never the provider's.
    user.name = user.name or _display_name(claims)

    rows = (
        await session.execute(select(MerchantMembership).where(MerchantMembership.user_id == user.id))
    ).scalars().all()
    keys = tuple(sorted({row.merchant_key for row in rows}))
    roles = {row.merchant_key: (row.role or "owner") for row in rows}
    if not keys:
        key = (req.merchant_key or "").strip() or f"merch_{subject[:6]}"
        clash = (await session.execute(select(Merchant).where(Merchant.merchant_key == key))).scalar_one_or_none()
        if clash is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"merchant key '{key}' is already in use",
            )
        session.add(
            Merchant(
                business_name=req.business_name or "My P2P desk",
                merchant_key=key,
                country=req.country.upper(),
                status=MerchantStatusEnum.APPROVED,
                kyb_status=KYBStatusEnum.NOT_STARTED,
                kyc_status=KYCStatusEnum.NOT_STARTED,
            )
        )
        session.add(MerchantMembership(user_id=user.id, merchant_key=key, role="owner"))
        try:
            await session.flush()
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"merchant key '{key}' is already in use",
            ) from exc
        keys, roles = (key,), {key: "owner"}

    user.last_login_at = datetime.now(UTC).replace(tzinfo=None)
    return MeResponse(user=_user_info(user), merchants=await _merchant_refs(session, keys, roles))


@router.get("/me", response_model=MeResponse)
async def me(
    scope: AccessScope = Depends(get_scope), session: AsyncSession = Depends(get_session)
) -> MeResponse:
    """Who is signed in and which workspaces they can switch between."""
    return MeResponse(
        user=_user_info(scope.user),
        merchants=await _merchant_refs(session, scope.merchants, scope.roles),
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh(req: RefreshRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    """Rotate a refresh token. Supabase access tokens expire after an hour."""
    try:
        state = await supabase.refresh_session(req.refresh_token)
    except SupabaseAuthError as exc:
        raise _http_error(exc) from exc

    user = (
        await session.execute(select(PortalUser).where(PortalUser.auth_user_id == state.user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="this account is not linked to a portal workspace"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="account disabled")
    return await _auth_response(session, user, state)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    user: PortalUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Response:
    """Revoke the caller's Supabase session server-side.

    The local user is resolved first, so a request carrying someone else's token
    cannot be used to log an unrelated account out.
    """
    if credentials is not None:
        await supabase.sign_out(credentials.credentials)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/merchants", response_model=MerchantRef, status_code=status.HTTP_201_CREATED)
async def create_merchant(
    req: CreateMerchantRequest,
    user: PortalUser = Depends(get_current_user),
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
) -> MerchantRef:
    """Add another P2P account to the same login (a second desk, a second bank)."""
    key = (req.merchant_key or "").strip() or f"merch_{user.id:06d}_{len(scope.merchants) + 1}"
    clash = (await session.execute(select(Merchant).where(Merchant.merchant_key == key))).scalar_one_or_none()
    if clash is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"merchant key '{key}' is already taken")

    session.add(
        Merchant(
            business_name=req.business_name,
            merchant_key=key,
            country=req.country.upper(),
            industry=req.industry,
            status=MerchantStatusEnum.APPROVED,
            kyb_status=KYBStatusEnum.NOT_STARTED,
            kyc_status=KYCStatusEnum.NOT_STARTED,
        )
    )
    session.add(MerchantMembership(user_id=user.id, merchant_key=key, role="owner"))
    await session.flush()
    return MerchantRef(merchant_key=key, business_name=req.business_name, role="owner", country=req.country.upper())
