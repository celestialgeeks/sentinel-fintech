"""Fixtures for the portal API tests.

These use ``httpx.AsyncClient`` with an ASGI transport rather than
``TestClient``: the tests are already async, so the app, the database engine and
the test body share one event loop. ``TestClient`` runs the app on its own loop,
which makes an async engine created in the fixture unsafe to touch.

The database is the project's real Supabase PostgreSQL, and the schema is whatever
``alembic upgrade head`` produced — tests never build tables from the models, so a
migration mistake cannot be hidden by a fixture that quietly creates the right
shape. Isolation comes from a connection-level transaction that is rolled back
after each test. Verified against the live server: an app request that calls
``session.commit()`` inside that connection still disappears on rollback, which is
what keeps the fixtures unchanged while the app commits as it always has.

Supabase is not transactional, so anything that reaches GoTrue outlives the test.
Auth users are therefore removed before each signup (see :func:`signup`) and every
address this suite touches is recorded for deletion when the run finishes.

The root ``conftest.client`` fixture is deliberately not reused — it assigns the
``test_engine`` *fixture function* to ``src.core.db.engine``, so anything that
actually talked to the database through it would fail. Here the session factory
is patched with a real one, which is what the guard's own persistence layer uses.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.core.db as db_module
import src.portal.ledger.router as data_router_module
from src.p2p import state as p2p_state
from src.p2p.router import router as p2p_router
from src.portal import supabase
from src.portal.auth.router import router as auth_router
from src.portal.integrations.router import router as integration_router
from src.portal.ledger.router import router as portal_data_router
from src.vendors.resilience import _mem_cache

PASSWORD = "correct-horse-battery"

# Every address this suite signs up, so a run can leave the project as it found it.
TOUCHED_EMAILS: set[str] = set()

# RFC 2606 reserves these domains for documentation, so no merchant can ever own
# one. Wiping them is safe by construction, which is what lets the suite clean up
# Supabase without an opt-in flag a newcomer would forget to set.
RESERVED_DOMAINS = ("example.com", "example.org", "example.net", "example.test", "sentinel.test")


def _is_suite_address(email: str) -> bool:
    lowered = (email or "").strip().lower()
    return lowered in TOUCHED_EMAILS or lowered.split("@")[-1] in RESERVED_DOMAINS


def _test_database_url() -> str:
    """The migrated Supabase database. No SQLite fallback exists any more."""
    url = db_module.get_settings().database_url
    if url.startswith("sqlite"):
        pytest.skip(f"portal tests need PostgreSQL, got {url.split('://')[0]}://…")
    return url


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """The real schema, inside a transaction that never commits."""
    engine = create_async_engine(_test_database_url())

    async with engine.connect() as conn:
        # Begin first: running the probe on a bare connection autobegins a
        # transaction, and SQLAlchemy then refuses the ``begin()`` that has to
        # wrap the test.
        outer = await conn.begin()
        try:
            revision = await conn.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
        except Exception:  # noqa: BLE001 - no alembic_version table reads as "not migrated"
            revision = None
        if not revision:
            await outer.rollback()
            await engine.dispose()
            pytest.fail("portal tests need a migrated database: python -m src.scripts.migrate upgrade head")

        # One Session bound to the connection for the whole test, so several app
        # requests share it and every write disappears with the rollback. The
        # default ``join_transaction_mode="create_savepoint"`` makes a request's
        # ``commit()`` release a savepoint rather than end the transaction that
        # wraps it — which is both what keeps isolation and why binding a plain
        # Connection here emits "transaction already deassociated".
        factory = async_sessionmaker(
            bind=conn, expire_on_commit=False, class_=AsyncSession, join_transaction_mode="create_savepoint"
        )

        original_db = db_module.session_factory
        original_router = data_router_module.session_factory
        db_module.session_factory = factory
        data_router_module.session_factory = factory

        p2p_state.guard_state._mem.clear()
        _mem_cache.clear()
        try:
            yield factory
        finally:
            db_module.session_factory = original_db
            data_router_module.session_factory = original_router
            p2p_state.guard_state._mem.clear()
            _mem_cache.clear()
            await outer.rollback()
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _auth_isolation():
    """Clear this suite's Supabase users before and after the run.

    The database is transactional and rolls back per test; GoTrue is not, so an
    account created by yesterday's run still answers ``/auth/signup`` with 409
    today even though every trace of it is gone from ``portal_users``. Wiping the
    reserved documentation domains first makes a run reproducible, and doing it
    again at the end leaves the project clean.

    Only addresses on :data:`RESERVED_DOMAINS` (plus any this run touched) are
    removed, so a real merchant account in the same project is untouchable.
    """
    _run_cleanup()
    yield
    _run_cleanup()


def _run_cleanup() -> None:
    if not supabase.configured():
        return
    try:
        removed = asyncio.run(_delete_suite_users())
    except Exception:  # noqa: BLE001 - cleanup is best-effort, never the run's fault
        removed = 0
    if removed:
        print(f"[portal tests] removed {removed} Supabase auth user(s) on reserved domains")


async def _delete_suite_users() -> int:
    removed = 0
    for candidate in await supabase.list_users():
        if _is_suite_address(candidate.get("email") or ""):
            await supabase.delete_user(candidate["id"])
            removed += 1
    return removed


@pytest.fixture
def app() -> FastAPI:
    """The real mount order: bot gates first, then the portal surface."""
    application = FastAPI()
    application.include_router(p2p_router, prefix="/api/v1")
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(integration_router, prefix="/api/v1")
    application.include_router(portal_data_router, prefix="/api/v1")
    return application


@pytest_asyncio.fixture
async def client(app, session_factory) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _clear_auth_user(email: str) -> None:
    """Drop a leftover GoTrue user for this address before signing it up again.

    Supabase sits outside the rolled-back transaction, so an address survives the
    test that created it. Without this, the second test to use the default fixture
    address gets 409 from an account the database has already forgotten about.

    The lookup is filtered server-side: listing every user before each signup made
    the suite quadratic, and a cached listing would go stale the first time a test
    created an address another test later reuses.
    """
    normalised = email.strip().lower()
    TOUCHED_EMAILS.add(normalised)
    if not supabase.configured():
        return
    existing = await supabase.find_user(normalised)
    if existing:
        await supabase.delete_user(existing["id"])


async def signup(client: AsyncClient, email: str = "desk@example.com", **extra: Any) -> dict[str, Any]:
    """Create an account and return ``{token, merchant_key, user}``."""
    await _clear_auth_user(email)
    body = {"email": email, "password": PASSWORD, "name": "Desk", "business_name": "Demo P2P Desk", **extra}
    response = await client.post("/api/v1/auth/signup", json=body)
    assert response.status_code == 201, response.text
    payload = response.json()
    return {
        "token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
        "merchant_key": payload["merchants"][0]["merchant_key"],
        "user": payload["user"],
    }


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def workspace(client: AsyncClient) -> dict[str, Any]:
    """A signed-in merchant, ready for ledger calls."""
    return await signup(client)


def order_payload(
    merchant_id: str,
    order_id: str = "ord_0001",
    *,
    buyer: str = "Ramesh Kumar",
    binance_user: str = "u_amesh",
    payer: str | None = None,
    trades: int = 50,
    age_days: int = 400,
    vpa: str = "buyer@okaxis",
    acct: str = "1234",
    address: str | None = None,
    qty: float = 10.0,
    price: float = 905.0,
    utr: str | None = "4200000001",
    confirmed: bool = True,
    chat: str | None = None,
    with_payment: bool = True,
) -> dict[str, Any]:
    """A ``P2POrder`` body with the mock-provider sentinels available.

    Mirrors ``src.vendors.mock``: a vpa/account carrying ``fraud``/``9999`` reads
    as a mule, an address carrying ``bad`` reads as exposed, and a ``payer`` that
    differs from ``buyer`` is a third-party payment.
    """
    order: dict[str, Any] = {
        "order_id": order_id,
        "merchant_id": merchant_id,
        "asset": "USDT",
        "fiat": "INR",
        "qty": qty,
        "price_inr": price,
        "side": "SELL",
        "buyer": {
            "binance_user": binance_user,
            "verified_name": buyer,
            "country": "IN",
            "trade_count": trades,
            "completion_rate": 0.98,
            "account_age_days": age_days,
            "chat_snippet": chat,
        },
    }
    if address:
        order["wallet"] = {"chain": "TRC20", "withdrawal_address": address}
    if with_payment:
        order["payment"] = {
            "method": "upi",
            "payer_name_on_account": payer or buyer,
            "bank_name": "HDFC Bank",
            "account_no_masked": acct,
            "ifsc": "HDFC0001234",
            "vpa": vpa,
            "utr": utr,
            "amount": qty * price,
            "confirmed": confirmed,
        }
    return order


async def call_gate(
    client: AsyncClient, merchant_id: str, *, phase: str = "release_gate", **kwargs: Any
) -> dict[str, Any]:
    """Drive a decision through the real bot endpoint, so persistence is real."""
    payload = {"order": order_payload(merchant_id, **kwargs), "phase": phase}
    response = await client.post(f"/api/v1/p2p/orders/{phase.replace('_', '-')}", json=payload)
    assert response.status_code == 200, response.text
    return response.json()
