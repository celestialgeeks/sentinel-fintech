"""Fixtures for the portal API tests.

These use ``httpx.AsyncClient`` with an ASGI transport rather than
``TestClient``: the tests are already async, so the app, the SQLite engine and
the test body share one event loop. ``TestClient`` runs the app on its own loop,
which makes an async engine created in the fixture unsafe to touch.

The root ``conftest.client`` fixture is deliberately not reused — it assigns the
``test_engine`` *fixture function* to ``src.core.db.engine``, so anything that
actually talked to the database through it would fail. Here the session factory
is patched with a real one, which is what the guard's own persistence layer uses.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import src.core.db as db_module
import src.portal.ledger.router as data_router_module
from src.core.db import Base
from src.p2p import state as p2p_state
from src.p2p.router import router as p2p_router
from src.portal.auth.router import router as auth_router
from src.portal.integrations.router import router as integration_router
from src.portal.ledger.router import router as portal_data_router
from src.vendors.resilience import _mem_cache

PASSWORD = "correct-horse-battery"


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """A fresh in-memory schema per test, visible to every module that reads it."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

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
        await engine.dispose()


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


async def signup(client: AsyncClient, email: str = "desk@example.com", **extra: Any) -> dict[str, Any]:
    """Create an account and return ``{token, merchant_key, user}``."""
    body = {"email": email, "password": PASSWORD, "name": "Desk", "business_name": "Demo P2P Desk", **extra}
    response = await client.post("/api/v1/auth/signup", json=body)
    assert response.status_code == 201, response.text
    payload = response.json()
    return {
        "token": payload["access_token"],
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
