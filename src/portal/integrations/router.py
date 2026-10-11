"""``/api/v1/integration/*`` — the connect-your-automation wizard's backend.

Step 2 (credentials), step 3 (transport) and step 4 (test with mock data) of the
setup wizard. The important promise here is that the test runs the **real**
pipeline — vendor fan-out, durable state, rules, fusion, evidence bundle — with
persistence and publishing switched off, so the verdict the merchant sees is the
verdict their bot would have received, and a test can never write to the ledger.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import get_session
from src.core.models import ApiKey
from src.gateway.schemas import GuardPhase, P2POrder
from src.p2p.pipeline import guard_order
from src.p2p.schemas import GuardDecision
from src.portal.deps import AccessScope, get_scope
from src.portal.ledger.orders import order_bounds
from src.portal.ledger.scoping import active_keys
from src.portal.schemas import (
    ApiKeyRow,
    ConnectionTestRequest,
    ConnectionTestResponse,
    CreatedApiKey,
    CreateKeyRequest,
    EndpointInfo,
    IntegrationStatus,
)
from src.portal.security import issue_credential

router = APIRouter(prefix="/integration", tags=["portal-integration"])

_BASE = "/api/v1/p2p"

ENDPOINTS = (
    EndpointInfo(
        method="POST", path=f"{_BASE}/orders/pre-screen", purpose="screen the buyer before INR is accepted"
    ),
    EndpointInfo(
        method="POST", path=f"{_BASE}/orders/release-gate", purpose="gate the escrow release on the confirmed credit"
    ),
    EndpointInfo(
        method="POST",
        path=f"{_BASE}/liens",
        purpose="open a freeze case and auto-assemble its evidence pack",
    ),
    EndpointInfo(method="GET", path=f"{_BASE}/health", purpose="guard liveness"),
)

SIGNATURE_HELP = (
    'X-Sentinel-Signature = hex(hmac_sha256(secret, f"{timestamp}." + raw_body)); '
    "X-Sentinel-Timestamp = unix seconds, 300s tolerance. Sign the bytes you send, "
    "not a re-serialised object."
)


def _hmac_enforced() -> bool:
    return bool(os.getenv("GUARD_HMAC_SECRET", "").strip())


def _key_row(row: ApiKey) -> ApiKeyRow:
    return ApiKeyRow(
        id=f"key_{row.id}",
        name=row.name,
        key_prefix=row.key_prefix,
        scopes=list(row.scopes or ["guard:call"]),
        mode=row.mode,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
        revoked_at=row.revoked_at,
        active=row.revoked_at is None,
    )


@router.get("/status", response_model=IntegrationStatus)
async def status_of(
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None, description="Workspace to inspect; defaults to your first"),
) -> IntegrationStatus:
    """Has this merchant's bot actually called the guard yet?"""
    keys = scope.resolve(merchant)
    if not keys:
        raise HTTPException(status_code=400, detail="no merchant workspace on this account")
    key = merchant or keys[0]
    total, first, last = await order_bounds(session, (key,))
    rows = await active_keys(session, key)
    return IntegrationStatus(
        merchant_key=key,
        transport="rest",
        connected=total > 0,
        has_api_key=any(row.revoked_at is None for row in rows),
        hmac_enforced=_hmac_enforced(),
        orders_total=total,
        first_order_at=first,
        last_order_at=last,
        endpoints=list(ENDPOINTS),
        kafka_topics=["sentinel.p2p.order", "sentinel.p2p.decision"],
        signature_help=SIGNATURE_HELP,
        sandbox_available=True,
    )


@router.get("/keys", response_model=list[ApiKeyRow])
async def list_keys(
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None, description="Workspace; defaults to your first"),
) -> list[ApiKeyRow]:
    """Bot credentials for a workspace. Secrets are never included."""
    keys = scope.resolve(merchant)
    if not keys:
        return []
    return [_key_row(row) for row in await active_keys(session, keys[0])]


@router.post("/keys", response_model=CreatedApiKey, status_code=201)
async def create_key(
    req: CreateKeyRequest,
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
    merchant: str | None = Query(None, description="Workspace the bot will call as merchant_id"),
) -> CreatedApiKey:
    """Mint a guard credential. The HMAC secret appears in this response once."""
    keys = scope.resolve(merchant)
    if not keys:
        raise HTTPException(status_code=400, detail="create a merchant workspace first")
    key = keys[0]
    scope.require(key, "owner", "risk")

    credential = issue_credential()
    row = ApiKey(
        merchant_key=key,
        name=req.name,
        key_prefix=credential.key_prefix,
        secret_hash=credential.secret_hash,
        scopes=list(req.scopes),
        mode=req.mode if req.mode in ("observe", "enforce") else "observe",
        created_by=scope.user.id,
    )
    session.add(row)
    await session.flush()
    return CreatedApiKey(
        id=f"key_{row.id}",
        name=row.name,
        key_prefix=row.key_prefix,
        hmac_secret=credential.hmac_secret,
    )


@router.delete("/keys/{key_id}", response_model=ApiKeyRow)
async def revoke_key(
    key_id: str,
    scope: AccessScope = Depends(get_scope),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyRow:
    """Revoke without deleting: the audit trail keeps knowing which key signed what."""
    numeric = key_id.removeprefix("key_")
    if not numeric.isdigit():
        raise HTTPException(status_code=404, detail=f"unknown key '{key_id}'")
    row = await session.get(ApiKey, int(numeric))
    if row is None:
        raise HTTPException(status_code=404, detail=f"unknown key '{key_id}'")
    scope.require(row.merchant_key, "owner")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(UTC).replace(tzinfo=None)
        await session.commit()
    return _key_row(row)


@router.post("/test", response_model=ConnectionTestResponse)
async def test_connection(
    req: ConnectionTestRequest,
    scope: AccessScope = Depends(get_scope),
) -> ConnectionTestResponse:
    """Wizard step 4: run one real decision against the live pipeline.

    Nothing is persisted and nothing is published, so this is safe to fire from a
    browser at any volume. It is still the real guard: unkeyed vendors fall back
    to their deterministic mocks, which is the whole point of a sandbox.
    """
    body: dict[str, Any] = dict(req.order)
    body.pop("_phase", None)
    try:
        order = P2POrder.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"order payload rejected: {exc.errors()[0]}") from exc

    if order.merchant_id not in scope.merchants:
        raise HTTPException(
            status_code=403,
            detail=(
                f"order.merchant_id '{order.merchant_id}' is not one of your workspaces "
                f"({', '.join(scope.merchants) or 'none'}). Put that value in your bot."
            ),
        )
    try:
        phase = GuardPhase(req.phase)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="phase must be pre_screen or release_gate") from exc
    if phase is GuardPhase.RELEASE_GATE and order.payment is None:
        raise HTTPException(status_code=400, detail="release-gate requires order.payment (the observed INR credit)")

    decision: GuardDecision = await guard_order(order, phase, persist=False, publish=False)
    return ConnectionTestResponse(decision=decision, persisted=False, published=False)
