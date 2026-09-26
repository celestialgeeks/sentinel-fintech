"""Evidence vault.

Per-order evidence is what actually gets a frozen account *unfrozen*: it proves
the merchant performed due diligence and is a downstream victim, not a
participant. ``build_bundle`` snapshots every decision input in a PII-light,
exportable form; ``to_markdown`` renders a pack a merchant can hand to the bank
or the jurisdictional cyber cell. PDF rendering is optional and guarded.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from src.gateway.schemas import GuardPhase, P2POrder
from src.p2p.schemas import GuardDecision
from src.screening.schemas import CounterpartyScreening


def _ref(order_id: str, phase: str, decided_at: datetime) -> str:
    """Deterministic per *decision*, not per order.

    The same order is screened at both gates, and a HOLD can be re-screened
    after thirty minutes, so a reference keyed on order id alone collides on the
    unique ``evidence_bundles.reference`` column: the second pack — usually the
    release-gate one, which is the pack holding the UTR and payer name — failed
    to insert and took the whole best-effort session down with it.
    """
    seed = f"{order_id}:{phase}:{decided_at.isoformat()}"
    return "EV-" + hashlib.sha256(seed.encode()).hexdigest()[:12].upper()


def build_bundle(
    order: P2POrder,
    phase: GuardPhase,
    screening: CounterpartyScreening,
    decision: GuardDecision,
) -> dict[str, Any]:
    """Assemble a PII-light, tamper-evident snapshot for one order."""
    payment = order.payment
    return {
        "reference": _ref(order.order_id, phase.value, decision.decided_at),
        "order_id": order.order_id,
        "merchant_id": order.merchant_id,
        "phase": phase.value,
        "generated_at": datetime.now(UTC).isoformat(),
        "order": {
            "asset": order.asset,
            "fiat": order.fiat,
            "qty": order.qty,
            "price_inr": order.price_inr,
            "inr_value": round(order.qty * order.price_inr, 2),
            "created_at": order.created_at.isoformat(),
        },
        "buyer": {
            "binance_user": order.buyer.binance_user,
            "verified_name": order.buyer.verified_name,
            "country": order.buyer.country,
            "trade_count": order.buyer.trade_count,
            "completion_rate": order.buyer.completion_rate,
            "account_age_days": order.buyer.account_age_days,
        },
        "payment": (
            {
                "method": payment.method.value,
                "utr": payment.utr,
                "vpa": payment.vpa,
                "account_no_masked": payment.account_no_masked,
                "ifsc": payment.ifsc,
                "payer_name_on_account": payment.payer_name_on_account,
                "amount": payment.amount,
                "confirmed": payment.confirmed,
            }
            if payment
            else None
        ),
        "wallet": (
            {
                "chain": order.wallet.chain,
                "deposit_address": order.wallet.deposit_address,
                "withdrawal_address": order.wallet.withdrawal_address,
                "exchange": order.wallet.exchange,
            }
            if order.wallet
            else None
        ),
        "vendor_verdicts": [v.model_dump(mode="json") for v in screening.verdicts],
        "decision": {
            "verdict": decision.verdict.value,
            "action": decision.action,
            "risk_score": decision.risk_score,
            "confidence": decision.confidence,
            "hard_rules": decision.hard_rules,
            "reasons": decision.reasons,
            "degraded": decision.degraded,
            "decided_at": decision.decided_at.isoformat(),
        },
    }


def to_json(bundle: dict[str, Any]) -> str:
    return json.dumps(bundle, indent=2, default=str, sort_keys=True)


def to_markdown(bundle: dict[str, Any]) -> str:
    d = bundle["decision"]
    lines = [
        f"# Sentinel Evidence Pack {bundle['reference']}",
        "",
        f"- Order: `{bundle['order_id']}` (merchant `{bundle['merchant_id']}`)",
        f"- Phase: {bundle['phase']}",
        f"- Generated: {bundle['generated_at']}",
        f"- Verdict: **{d['verdict']}** ({d['action']}) - risk {d['risk_score']:.2f}, confidence {d['confidence']:.2f}",
        "",
        "## Order",
        f"- {bundle['order']['qty']} {bundle['order']['asset']} @ INR {bundle['order']['price_inr']}"
        f" = INR {bundle['order']['inr_value']}",
        "",
        "## Buyer",
        f"- Binance user `{bundle['buyer']['binance_user']}`, verified name '{bundle['buyer']['verified_name']}'",
        f"- Trades: {bundle['buyer']['trade_count']}, completion {bundle['buyer']['completion_rate']}",
    ]
    if bundle["payment"]:
        p = bundle["payment"]
        lines += [
            "",
            "## Payment credit",
            f"- Method {p['method']}, UTR {p['utr']}, VPA {p['vpa']}, acct ****{p['account_no_masked']}",
            f"- Payer name on account: '{p['payer_name_on_account']}', confirmed: {p['confirmed']}",
        ]
    w = bundle.get("wallet")
    if w:
        lines += [
            "",
            "## Trade wallet",
            f"- Chain {w['chain']}, withdrawal address {w['withdrawal_address']}, "
            f"deposit address {w['deposit_address']}",
        ]
    lines += ["", "## Vendor signals"]
    for v in bundle["vendor_verdicts"]:
        lines.append(f"- {v['provider']} [{v['category']}] risk={v['risk']:.2f} - {v['detail']}")
    if d["hard_rules"]:
        lines += ["", f"## Hard rules triggered: {', '.join(d['hard_rules'])}"]
    lines += ["", "## Reasons"]
    lines += [f"- {r}" for r in d["reasons"]] or ["- none"]
    return "\n".join(lines)
