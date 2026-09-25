"""Lien / freeze-notice intake.

When the bank or a cyber cell freezes an account over a credit, speed and
evidence are everything. This maps a notice back to the originating order,
pulls the stored evidence bundle, and opens a case the merchant can hand over.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from src.p2p import evidence, store
from src.p2p.schemas import LienNotice


def _case_ref(notice: LienNotice) -> str:
    seed = (notice.order_id or "") + (notice.utr or "") + (notice.account_no_masked or "")
    return "LIEN-" + hashlib.sha256(seed.encode()).hexdigest()[:10].upper()


async def open_case(notice: LienNotice) -> dict:
    """Resolve a notice to its order + evidence pack and persist a case."""
    bundle = await store.get_evidence(notice.order_id) if notice.order_id else None

    case = {
        "case_ref": _case_ref(notice),
        "order_id": notice.order_id,
        "utr": notice.utr,
        "account_no_masked": notice.account_no_masked,
        "source": notice.source,
        "notice_text": notice.notice_text,
        "status": "open",
        "evidence_reference": (bundle or {}).get("reference") if bundle else None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    await store.save_lien(case)
    return {
        "case": {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in case.items()},
        "evidence_markdown": evidence.to_markdown(bundle) if bundle else None,
        "assembled": bool(bundle),
    }
