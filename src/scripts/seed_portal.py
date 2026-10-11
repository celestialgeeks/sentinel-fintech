"""Seed a demo merchant with real guard decisions, so the portal has a story to show.

Nothing here is fabricated: every order is pushed through the live pipeline
(``pipeline.guard_order``) with the deterministic mock providers, so verdicts,
reason strings, evidence bundles, vouchers and compliance events are exactly what
a bot would have produced. That matters for mockups and demos — a dashboard
populated with invented numbers teaches nobody how the product behaves.

    python -m src.scripts.seed_portal
    python -m src.scripts.seed_portal --email you@example.com --merchant default --reset

Then sign in and read it back:

    curl -s -X POST localhost:8000/api/v1/auth/login \
      -H 'content-type: application/json' \
      -d '{"email":"demo@sentinel.dev","password":"demo-passw0rd-123"}'
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select

from src.core.db import engine, init_db, session_factory
from src.core.models import (
    ComplianceEvent,
    EvidenceBundle,
    KYBStatusEnum,
    KYCStatusEnum,
    LienCase,
    Merchant,
    MerchantMembership,
    MerchantStatusEnum,
    OverrideNote,
    P2POrderRecord,
    PortalUser,
    SettlementVoucher,
    VendorCall,
)
from src.gateway.schemas import (
    BuyerProfile,
    GuardPhase,
    P2POrder,
    PayerPayment,
    PaymentMethod,
    TradeWallet,
)
from src.p2p import lien as lien_intake
from src.p2p.pipeline import guard_order
from src.p2p.schemas import LienNotice
from src.portal import supabase

logger = logging.getLogger("seed_portal")

DEMO_EMAIL = "demo@sentinel.dev"
DEMO_PASSWORD = "demo-passw0rd-123"

CLEAN_BUYERS = [
    ("u_amesh", "Ramesh Kumar", 50, 400),
    ("u_priya", "Priya Nair", 128, 900),
    ("u_vikram", "Vikram Shah", 22, 140),
    ("u_anjali", "Anjali Desai", 310, 1200),
]
RISKY_BUYERS = [
    ("u_sunil", "Sunil Verma", 3, 12),
    ("u_kabir", "Kabir Khan", 0, 4),
]


def _order(
    index: int,
    merchant_id: str,
    *,
    buyer: tuple[str, str, int, int],
    payer_name: str,
    vpa: str,
    acct: str,
    address: str | None = None,
    qty: float = 10.0,
    price: float = 905.0,
    chat: str | None = None,
    confirmed: bool = True,
) -> P2POrder:
    user, name, trades, age = buyer
    return P2POrder(
        order_id=f"ord_{index:05d}",
        qty=qty,
        price_inr=price,
        merchant_id=merchant_id,
        created_at=datetime.now(UTC) - timedelta(minutes=index * 17),
        buyer=BuyerProfile(
            binance_user=user,
            verified_name=name,
            trade_count=trades,
            account_age_days=age,
            completion_rate=0.98 if trades > 10 else 0.7,
            chat_snippet=chat,
        ),
        payment=PayerPayment(
            method=PaymentMethod.UPI if index % 3 else PaymentMethod.IMPS,
            payer_name_on_account=payer_name,
            bank_name="HDFC Bank",
            account_no_masked=acct,
            ifsc="HDFC0001234",
            vpa=vpa,
            utr=f"{420000000000 + index}",
            amount=qty * price,
            credit_ts=datetime.now(UTC) - timedelta(minutes=index * 17 + 4),
            confirmed=confirmed,
        ),
        wallet=TradeWallet(withdrawal_address=address, chain="TRC20") if address else None,
    )


def _scenario(count: int, merchant_id: str) -> list[tuple[P2POrder, GuardPhase]]:
    """A week of trading with the four patterns that actually happen.

    Roughly 70% clean, and the rest spread over the failure modes the guard
    exists for: third-party payment, a mule account, an exposed wallet, and a
    brand-new buyer paying in slices.
    """
    rng = random.Random(20260926)
    plan: list[tuple[P2POrder, GuardPhase]] = []
    index = 0

    def next_index() -> int:
        nonlocal index
        index += 1
        return index

    clean = max(1, int(count * 0.7))
    for _ in range(clean):
        i = next_index()
        buyer = CLEAN_BUYERS[i % len(CLEAN_BUYERS)]
        qty = round(rng.uniform(4, 90), 2)
        order = _order(
            i, merchant_id, buyer=buyer, payer_name=buyer[1], vpa=f"{buyer[0]}@okaxis",
            acct=f"{rng.randint(1000, 9998)}", qty=qty, price=round(rng.uniform(888, 918), 2),
        )
        plan.append((order, GuardPhase.PRE_SCREEN))
        plan.append((order, GuardPhase.RELEASE_GATE))

    # Third-party payment: someone else's account funded the order.
    for _ in range(max(1, count // 8)):
        i = next_index()
        buyer = CLEAN_BUYERS[i % len(CLEAN_BUYERS)]
        order = _order(
            i, merchant_id, buyer=buyer, payer_name="Sunil Verma", vpa="sunil@okhdfcbank",
            acct="4417", qty=40.0, price=910.0, chat="payment done screenshot, urgent please release",
        )
        plan.append((order, GuardPhase.PRE_SCREEN))
        plan.append((order, GuardPhase.RELEASE_GATE))

    # Mule account in the complaint database.
    for _ in range(max(1, count // 10)):
        i = next_index()
        buyer = RISKY_BUYERS[i % len(RISKY_BUYERS)]
        order = _order(
            i, merchant_id, buyer=buyer, payer_name=buyer[1], vpa="fraud-confirm@ybl", acct="8899",
            qty=55.0, price=902.0,
        )
        plan.append((order, GuardPhase.RELEASE_GATE))

    # On-chain exposure on the buyer's withdrawal address.
    for _ in range(max(1, count // 12)):
        i = next_index()
        buyer = CLEAN_BUYERS[i % len(CLEAN_BUYERS)]
        order = _order(
            i, merchant_id, buyer=buyer, payer_name=buyer[1], vpa=f"{buyer[0]}@okicici", acct="2055",
            address="Tbad9f3c71q4mn", qty=25.0, price=900.0,
        )
        plan.append((order, GuardPhase.RELEASE_GATE))

    # Fresh buyer, unconfirmed credit, paying in slices.
    for _ in range(max(1, count // 10)):
        i = next_index()
        buyer = RISKY_BUYERS[i % len(RISKY_BUYERS)]
        order = _order(
            i, merchant_id, buyer=buyer, payer_name=buyer[1], vpa="newacct@upi", acct="7700",
            qty=8.0, price=903.0, confirmed=False, chat="my friend paid from different account",
        )
        plan.append((order, GuardPhase.PRE_SCREEN))
        plan.append((order, GuardPhase.RELEASE_GATE))

    return plan


async def _auth_subject(email: str) -> str:
    """The GoTrue id for the demo address, creating it if needed.

    Seeding wipes local rows but cannot wipe Supabase, so re-seeding almost always
    meets an email that is already registered. Finding the existing subject rather
    than failing keeps ``--reset-seed`` repeatable.
    """
    try:
        state = await supabase.create_verified_user(email, DEMO_PASSWORD, name="Demo Merchant")
        return state.user_id
    except supabase.SupabaseAuthError as exc:
        if exc.status_code != 409:
            raise
    existing = await supabase.find_user(email)
    if existing is None:
        raise RuntimeError(f"Supabase reports {email} as registered but does not list it")
    return str(existing["id"])


async def _ensure_user(session, email: str, merchant_id: str) -> PortalUser:
    user = (await session.execute(select(PortalUser).where(PortalUser.email == email))).scalar_one_or_none()
    if user is not None:
        return user
    user = PortalUser(auth_user_id=await _auth_subject(email), email=email, name="Demo Merchant")
    session.add(user)
    await session.flush()
    session.add(
        Merchant(
            business_name="Demo P2P Desk",
            merchant_key=merchant_id,
            country="IN",
            industry="Crypto P2P trading",
            status=MerchantStatusEnum.APPROVED,
            kyb_status=KYBStatusEnum.VERIFIED,
            kyc_status=KYCStatusEnum.VERIFIED,
        )
    )
    session.add(MerchantMembership(user_id=user.id, merchant_key=merchant_id, role="owner"))
    await session.commit()
    return user


async def _reset(session, merchant_id: str) -> None:
    """Clear this workspace's history so the seed is repeatable."""
    order_ids = select(P2POrderRecord.order_id).where(P2POrderRecord.merchant_id == merchant_id)
    for model in (VendorCall, EvidenceBundle, SettlementVoucher, ComplianceEvent, OverrideNote):
        await session.execute(delete(model).where(model.order_id.in_(order_ids)))
    await session.execute(delete(LienCase).where(LienCase.merchant_id == merchant_id))
    await session.execute(delete(P2POrderRecord).where(P2POrderRecord.merchant_id == merchant_id))
    await session.commit()


async def _simulate_vendor_telemetry(merchant_id: str) -> int:
    """Backfill plausible latency/cost on mock vendor calls, on request only.

    Mock providers make no network call, so ``latency_ms`` and ``cost_usd`` are
    genuinely ~0 — which leaves the Insights screen and the latency KPI empty in
    a demo. This fills them with values in the range a keyed vendor would report
    (50-1200 ms, $0.03-$0.18 per call). It is opt-in because a dashboard full of
    invented performance numbers is exactly the kind of thing that gets quoted
    back at you; production data comes from the real adapters, not from here.
    """
    rng = random.Random(7)
    async with session_factory() as session:
        rows = (
            await session.execute(
                select(VendorCall).where(VendorCall.order_id.in_(
                    select(P2POrderRecord.order_id).where(P2POrderRecord.merchant_id == merchant_id)
                ))
            )
        ).scalars().all()
        for row in rows:
            row.latency_ms = rng.choice([64, 120, 240, 410, 680, 930, 1180])
            row.cost_usd = round(rng.uniform(0.03, 0.18), 4)
        await session.commit()
        return len(rows)


async def seed(*, email: str, merchant_id: str, orders: int, reset: bool, simulate_telemetry: bool = False) -> None:
    await init_db()
    async with session_factory() as session:
        await _ensure_user(session, email, merchant_id)
        if reset:
            await _reset(session, merchant_id)

    tally = {"ALLOW": 0, "HOLD": 0, "BLOCK": 0}
    blocked_order: str | None = None
    for order, phase in _scenario(orders, merchant_id):
        # Re-stamp the clock so decided_at spreads across the window the portal shows.
        decision = await guard_order(order, phase, persist=True, publish=False)
        tally[decision.verdict.value] += 1
        if decision.verdict.value == "BLOCK" and blocked_order is None and order.payment:
            blocked_order = order.order_id
        logger.info(
            "%s %s -> %s risk=%.2f", order.order_id, phase.value, decision.verdict.value, decision.risk_score
        )

    if blocked_order:
        async with session_factory():
            await lien_intake.open_case(
                LienNotice(
                    order_id=blocked_order,
                    utr="420000000101",
                    account_no_masked="4417",
                    merchant_id=merchant_id,
                    source="bank_email",
                    notice_text=(
                        "Dear customer, your account has been marked Lien-mark as per "
                        "direction received from the Cyber Crime Cell, reference NCRP/CFCFRMS."
                    ),
                )
            )

    await _report(merchant_id)
    if simulate_telemetry:
        touched = await _simulate_vendor_telemetry(merchant_id)
        print(f"Simulated    {touched} vendor-call rows given demo latency/cost — NOT production data")
    print(f"\nSigned-in email    {email}")
    print(f"Password           {DEMO_PASSWORD}   (dev seed only — change it anywhere real)")
    print(f"merchant_id        {merchant_id}   (send this from your bot)")
    print("Verdicts           " + "  ".join(f"{k}={v}" for k, v in tally.items()))
    await engine.dispose()


async def _report(merchant_id: str) -> None:
    """What actually landed in the database, read back rather than assumed."""
    async with session_factory() as session:
        rows = (
            await session.execute(
                select(P2POrderRecord.verdict, func.count())
                .where(P2POrderRecord.merchant_id == merchant_id)
                .group_by(P2POrderRecord.verdict)
            )
        ).all()
        cases = (
            await session.execute(select(LienCase).where(LienCase.merchant_id == merchant_id))
        ).scalars().all()
    print("Persisted rows     " + ", ".join(f"{verdict}: {count}" for verdict, count in rows))
    print(f"Freeze cases       {len(cases)}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Seed a demo merchant into the Sentinel portal")
    parser.add_argument("--email", default=DEMO_EMAIL)
    parser.add_argument("--merchant", default="default", help="merchant_id the bot will send")
    parser.add_argument("--orders", type=int, default=18, help="clean orders to generate (other cases scale off it)")
    parser.add_argument("--reset", action="store_true", help="delete this workspace's history first")
    parser.add_argument(
        "--simulate-vendor-telemetry",
        action="store_true",
        help="fill latency/cost with plausible demo values (mock providers report ~0)",
    )
    args = parser.parse_args()
    asyncio.run(
        seed(
            email=args.email,
            merchant_id=args.merchant,
            orders=args.orders,
            reset=args.reset,
            simulate_telemetry=args.simulate_vendor_telemetry,
        )
    )


if __name__ == "__main__":
    main()
