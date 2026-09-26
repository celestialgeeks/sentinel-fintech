"""Merchant-scope primitives shared by every portal read.

Rule 1 of the ledger: no query runs unscoped. ``scoped()`` is the only place the
merchant-key restriction is written, ``Filters`` is the single vocabulary for the
shared query-string parameters, and the helpers here resolve a scope into the
display metadata and volume badges the shell needs.
"""


from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import ApiKey, Merchant, P2POrderRecord, SettlementVoucher


def scoped(stmt: Select, keys: Sequence[str]) -> Select:
    """Constrain a ``P2POrderRecord``-rooted statement to the caller's merchants."""
    return stmt.where(P2POrderRecord.merchant_id.in_(keys))


async def workspace_names(session: AsyncSession, keys: Sequence[str]) -> dict[str, dict[str, str]]:
    """Display metadata for each merchant key, falling back to the key itself."""
    rows = (
        await session.execute(select(Merchant).where(Merchant.merchant_key.in_(list(keys))))
    ).scalars().all()
    found = {
        m.merchant_key: {"business_name": m.business_name or m.merchant_key, "country": (m.country or "IN")}
        for m in rows
        if m.merchant_key
    }
    return {key: found.get(key, {"business_name": key, "country": "IN"}) for key in keys}


async def order_counts(session: AsyncSession, keys: Sequence[str]) -> dict[str, int]:
    """Order volume per merchant, for the workspace switcher badge."""
    rows = (
        await session.execute(
            select(P2POrderRecord.merchant_id, func.count()).where(
                P2POrderRecord.merchant_id.in_(list(keys))
            ).group_by(P2POrderRecord.merchant_id)
        )
    ).all()
    per_key = {str(key): int(count) for key, count in rows}
    return {key: per_key.get(key, 0) for key in keys}


@dataclass(slots=True)
class Filters:
    """Every ledger filter, in one object.

    A dataclass rather than fourteen keyword arguments, because the same set is
    needed by the paginated list, by the aggregate header above it, and by every
    chart on the dashboard — and those numbers must agree with the table they sit
    on top of, which is easy to break when each call re-lists its own subset.
    """

    verdicts: Sequence[str] | None = None
    phases: Sequence[str] | None = None
    risk_min: float | None = None
    risk_max: float | None = None
    hard_rule: str | None = None
    degraded: bool | None = None
    has_utr: bool | None = None
    payment_method: str | None = None
    pool: str | None = None
    confirmed: bool | None = None
    buyer_key: str | None = None
    search: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def conditions(self) -> list[Any]:
        conds: list[Any] = []
        if self.verdicts:
            conds.append(P2POrderRecord.verdict.in_([v.upper() for v in self.verdicts]))
        if self.phases:
            conds.append(P2POrderRecord.phase.in_(list(self.phases)))
        if self.risk_min is not None:
            conds.append(P2POrderRecord.risk_score >= self.risk_min)
        if self.risk_max is not None:
            conds.append(P2POrderRecord.risk_score <= self.risk_max)
        if self.hard_rule:
            # hard_rules is a JSON array; LIKE is the only portable containment test.
            conds.append(P2POrderRecord.hard_rules.like(f'%"{self.hard_rule}"%'))
        if self.degraded is not None:
            conds.append(P2POrderRecord.degraded.is_(bool(self.degraded)))
        if self.has_utr is not None:
            present = P2POrderRecord.utr.is_not(None) & (P2POrderRecord.utr != "")
            conds.append(present if self.has_utr else or_(P2POrderRecord.utr.is_(None), P2POrderRecord.utr == ""))
        if self.payment_method:
            conds.append(P2POrderRecord.payment_method == self.payment_method)
        if self.confirmed is not None:
            conds.append(P2POrderRecord.credit_confirmed.is_(bool(self.confirmed)))
        if self.buyer_key:
            key = func.lower(func.coalesce(P2POrderRecord.buyer_user, P2POrderRecord.buyer_name))
            conds.append(key == self.buyer_key.lower())
        if self.search:
            like = f"%{self.search}%"
            conds.append(
                or_(
                    P2POrderRecord.order_id.ilike(like),
                    P2POrderRecord.utr.ilike(like),
                    P2POrderRecord.vpa.ilike(like),
                    P2POrderRecord.buyer_user.ilike(like),
                    P2POrderRecord.buyer_name.ilike(like),
                )
            )
        if self.start is not None:
            conds.append(P2POrderRecord.decided_at >= self.start)
        if self.end is not None:
            conds.append(P2POrderRecord.decided_at <= self.end)
        if self.pool:
            conds.append(
                P2POrderRecord.order_id.in_(
                    select(SettlementVoucher.order_id).where(SettlementVoucher.pool == self.pool)
                )
            )
        return conds


async def active_keys(session: AsyncSession, merchant_key: str) -> list[ApiKey]:
    rows = (
        await session.execute(
            select(ApiKey).where(ApiKey.merchant_key == merchant_key).order_by(ApiKey.id.desc())
        )
    ).scalars().all()
    return list(rows)
