"""Google sign-in arriving at the portal: ``POST /api/v1/auth/link``.

Supabase owns the Google credential, so nothing here calls GoTrue. The one boundary
under test is ``verify_access_token``, patched to return the claims a real
Google-backed Supabase token carries — checked live against this project: ``ES256``,
``aud=authenticated``, ``app_metadata.provider="google"``, the address in ``email``,
the display name in ``user_metadata.full_name``.

What these tests prove is the *account* half of the flow, which is the half Supabase
cannot do: who gets a workspace, who is refused, and that a repeated Google return
cannot mint a second desk.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.models import (
    KYBStatusEnum,
    KYCStatusEnum,
    Merchant,
    MerchantMembership,
    MerchantStatusEnum,
    PortalUser,
)
from src.portal import supabase
from src.portal.supabase import SupabaseAuthError
from tests.test_portal.conftest import auth

GOOGLE_SUBJECT = "7f1f4a6e-2b0e-4f6d-9b3c-1a2b3c4d5e6f"
OTHER_SUBJECT = "11111111-2222-3333-4444-555555555555"


def google_claims(**over: Any) -> dict[str, Any]:
    """The claims payload a Google-signed-in Supabase access token decodes to."""
    claims: dict[str, Any] = {
        "iss": "https://project.supabase.co/auth/v1",
        "sub": GOOGLE_SUBJECT,
        "aud": "authenticated",
        "email": "desk.owner@gmail.com",
        "role": "authenticated",
        "app_metadata": {"provider": "google", "providers": ["google"]},
        "user_metadata": {"full_name": "Desk Owner", "email_verified": True},
    }
    claims.update(over)
    return claims


@pytest.fixture
def as_identity(monkeypatch):
    """Stand in for a verified Supabase session, or for the auth server being down."""

    def _install(claims: dict[str, Any] | None = None, *, error: SupabaseAuthError | None = None):
        async def fake_verify(_token: str) -> dict[str, Any]:
            if error is not None:
                raise error
            return claims or google_claims()

        monkeypatch.setattr(supabase, "verify_access_token", fake_verify)

    return _install


async def link(client: AsyncClient, **body: Any) -> Any:
    return await client.post("/api/v1/auth/link", json=body, headers=auth("google-session-token"))


async def seed_merchant(
    factory: async_sessionmaker[AsyncSession],
    *,
    subject: str,
    email: str,
    merchant_key: str = "merch_existing",
    business_name: str = "Existing Desk",
    is_active: bool = True,
    name: str | None = "Chosen Name",
) -> None:
    """Create a portal account that already owns a desk, without touching Supabase."""
    async with factory() as session:
        user = PortalUser(auth_user_id=subject, email=email, name=name, is_active=is_active)
        session.add(user)
        await session.flush()
        session.add(
            Merchant(
                business_name=business_name,
                merchant_key=merchant_key,
                country="IN",
                status=MerchantStatusEnum.APPROVED,
                kyb_status=KYBStatusEnum.NOT_STARTED,
                kyc_status=KYCStatusEnum.NOT_STARTED,
            )
        )
        session.add(MerchantMembership(user_id=user.id, merchant_key=merchant_key, role="owner"))
        await session.commit()


async def _counts(factory: async_sessionmaker[AsyncSession]) -> tuple[int, int, int]:
    """(portal users, merchants, memberships) after the request under test."""
    async with factory() as session:
        users = len((await session.execute(select(PortalUser))).scalars().all())
        merchants = len((await session.execute(select(Merchant))).scalars().all())
        memberships = len((await session.execute(select(MerchantMembership))).scalars().all())
    return users, merchants, memberships


class TestFirstGoogleSignIn:
    async def test_creates_the_account_and_exactly_one_workspace(self, client, as_identity, session_factory):
        as_identity()
        result = await link(client, business_name="Ramesh Desk", country="in")
        assert result.status_code == 200, result.text
        body = result.json()
        assert body["user"]["email"] == "desk.owner@gmail.com"
        assert body["user"]["name"] == "Desk Owner"  # taken off the Google profile
        assert len(body["merchants"]) == 1
        assert body["merchants"][0]["business_name"] == "Ramesh Desk"
        assert body["merchants"][0]["country"] == "IN"
        assert body["merchants"][0]["role"] == "owner"
        assert await _counts(session_factory) == (1, 1, 1)

    async def test_the_subject_is_what_is_stored_not_the_email(self, client, as_identity, session_factory):
        as_identity()
        await link(client)
        async with session_factory() as session:
            user = (await session.execute(select(PortalUser))).scalar_one()
            assert user.auth_user_id == GOOGLE_SUBJECT

    async def test_a_missing_business_name_still_lands_on_a_desk(self, client, as_identity):
        as_identity()
        body = (await link(client)).json()
        assert body["merchants"][0]["business_name"] == "My P2P desk"

    async def test_an_existing_bots_merchant_key_is_honoured(self, client, as_identity):
        as_identity()
        body = (await link(client, merchant_key="desk_alpha")).json()
        assert body["merchants"][0]["merchant_key"] == "desk_alpha"

    async def test_returns_401_without_a_token(self, client):
        assert (await client.post("/api/v1/auth/link", json={})).status_code == 401

    async def test_rejects_a_subject_that_is_not_a_uuid(self, client, as_identity, session_factory):
        as_identity(google_claims(sub="1"))  # a local-style numeric id is not a GoTrue subject
        result = await link(client)
        assert result.status_code == 401
        assert result.json()["detail"] == "token subject is not a user id"
        assert await _counts(session_factory) == (0, 0, 0)

    async def test_rejects_an_identity_with_no_email(self, client, as_identity):
        as_identity(google_claims(email=None))
        assert (await link(client)).status_code == 401

    async def test_forwards_an_unreachable_auth_server(self, client, as_identity):
        as_identity(error=SupabaseAuthError("Supabase Auth is not configured", status_code=503))
        assert (await link(client)).status_code == 503


class TestRepeatSignInIsIdempotent:
    async def test_second_return_adds_nothing(self, client, as_identity, session_factory):
        as_identity()
        first = (await link(client, business_name="Ramesh Desk")).json()
        second = (await link(client, business_name="A Different Desk", merchant_key="other_key")).json()
        assert [m["merchant_key"] for m in second["merchants"]] == [m["merchant_key"] for m in first["merchants"]]
        assert second["merchants"][0]["business_name"] == "Ramesh Desk"
        assert await _counts(session_factory) == (1, 1, 1)

    async def test_the_google_profile_never_rewrites_an_existing_name(self, client, as_identity):
        as_identity(google_claims(user_metadata={"full_name": "First Name"}))
        await link(client)
        as_identity(google_claims(user_metadata={"full_name": "Renamed On Google"}))
        assert (await link(client)).json()["user"]["name"] == "First Name"


class TestReturningPasswordMerchant:
    async def test_a_shared_subject_keeps_its_own_desk_and_gains_no_other(
        self, client, as_identity, session_factory
    ):
        """Supabase links Google onto a confirmed user and keeps the same subject.

        So the merchant lands on the workspace they signed up with; nothing is
        duplicated and nothing is renamed.
        """
        await seed_merchant(session_factory, subject=GOOGLE_SUBJECT, email="desk.owner@gmail.com")
        as_identity()
        body = (await link(client, business_name="Should Not Be Created")).json()
        assert [m["merchant_key"] for m in body["merchants"]] == ["merch_existing"]
        assert body["user"]["name"] == "Chosen Name"
        assert await _counts(session_factory) == (1, 1, 1)

    async def test_a_disabled_account_is_refused(self, client, as_identity, session_factory):
        await seed_merchant(session_factory, subject=GOOGLE_SUBJECT, email="desk.owner@gmail.com", is_active=False)
        as_identity()
        result = await link(client)
        assert result.status_code == 403
        assert result.json()["detail"] == "account disabled"


class TestTakeoverGuard:
    async def test_matching_email_but_different_subject_is_refused(self, client, as_identity, session_factory):
        """The one case that must never merge.

        A portal row that already answers to another subject means GoTrue decided
        *not* to fold this Google identity into that user. Trusting the email claim
        here would hand that merchant's ledger to whoever presented a Google session
        for the same address.
        """
        await seed_merchant(session_factory, subject=OTHER_SUBJECT, email="desk.owner@gmail.com")
        as_identity()
        result = await link(client)
        assert result.status_code == 409
        assert "sign in with your password" in result.json()["detail"]
        # The impersonator is not created, and the real owner's rows are untouched.
        assert await _counts(session_factory) == (1, 1, 1)
        async with session_factory() as session:
            user = (await session.execute(select(PortalUser))).scalar_one()
            assert user.auth_user_id == OTHER_SUBJECT

    async def test_a_taken_merchant_key_leaves_no_orphan_login(self, client, as_identity, session_factory):
        """A failed desk creation rolls the whole link back."""
        await seed_merchant(session_factory, subject=OTHER_SUBJECT, email="someone.else@gmail.com")
        as_identity(google_claims(subject="99999999-8888-7777-6666-555555555555", email="new.person@gmail.com"))
        result = await link(client, merchant_key="merch_existing")
        assert result.status_code == 409
        assert "merch_existing" in result.json()["detail"]
        assert await _counts(session_factory) == (1, 1, 1)
