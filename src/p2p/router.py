"""FastAPI router for the P2P taint guard.

The merchant bot calls these two gates around a P2P order:

* POST /p2p/orders/pre-screen     - before accepting the buyer's payment
* POST /p2p/orders/release-gate   - before releasing USDT from escrow

Plus freeze-notice intake. All share pipeline.guard_order. Evidence download is
deliberately not here: a pack carries buyer names, UTRs and masked accounts, so it
is served authenticated and merchant-scoped from ``src.portal.ledger.router``.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from src.gateway.schemas import GuardPhase
from src.p2p import lien
from src.p2p.pipeline import guard_order
from src.p2p.schemas import GuardDecision, GuardRequest, LienNotice

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/p2p", tags=["p2p-guard"])


@router.post("/orders/pre-screen", response_model=GuardDecision)
async def pre_screen(req: GuardRequest) -> GuardDecision:
    """Screen a buyer at order creation, before any INR is accepted."""
    return await guard_order(req.order, GuardPhase.PRE_SCREEN)


@router.post("/orders/release-gate", response_model=GuardDecision)
async def release_gate(req: GuardRequest) -> GuardDecision:
    """Gate the escrow release using the confirmed bank credit + wallet checks."""
    if req.order.payment is None:
        raise HTTPException(status_code=400, detail="release-gate requires order.payment (the observed INR credit)")
    return await guard_order(req.order, GuardPhase.RELEASE_GATE)


@router.post("/liens")
async def report_lien(notice: LienNotice) -> dict[str, Any]:
    """Intake a bank/legal freeze notice and auto-assemble its evidence case."""
    return await lien.open_case(notice)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"service": "sentinel-p2p-guard", "status": "ok"}
