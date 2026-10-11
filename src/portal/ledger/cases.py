"""Buyers, settlement vouchers, freeze cases, compliance events, overrides.

These are the record types a human acts on, so this module is the only part of
the read layer that writes: :func:`update_lien` and :func:`record_override`.
"""


from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import (
    ComplianceEvent,
    Counterparty,
    EvidenceBundle,
    LienCase,
    OverrideNote,
    P2POrderRecord,
    SettlementVoucher,
)
from src.portal import schemas as S  # noqa: N812 - short alias keeps response models readable
from src.portal.ledger.mappers import aware, lien_row, voucher_row
from src.portal.ledger.orders import get_record
from src.portal.ledger.scoping import Filters, scoped

LIEN_STATUSES = ("open", "awaiting_bank", "submitted", "lifted", "rejected")


async def list_counterparties(
    session: AsyncSession,
    keys: Sequence[str],
    *,
    search: str | None = None,
    flagged_only: bool = False,
    start: datetime | None = None,
    end: datetime | None = None,
    sort: str = "seen",
    limit: int = 50,
    offset: int = 0,
) -> S.Page[S.CounterpartyRow]:
    """Repeat-buyer state built from this merchant's own decisions.

    Counts and money are scoped to the caller; ``clean_streak`` comes from the
    engine's global ``counterparties`` row because that is the state the rules
    actually read — it is shown, not rewritten, so a merchant never sees a trust
    number the guard did not use.
    """
    buyer_key = func.lower(func.coalesce(P2POrderRecord.buyer_user, P2POrderRecord.buyer_name))
    conds = Filters(search=search, start=start, end=end).conditions()
    stmt = scoped(
        select(
            buyer_key.label("buyer_key"),
            func.count().label("seen"),
            func.sum(case((P2POrderRecord.verdict == "ALLOW", 1), else_=0)).label("allow"),
            func.sum(case((P2POrderRecord.verdict == "HOLD", 1), else_=0)).label("hold"),
            func.sum(case((P2POrderRecord.verdict == "BLOCK", 1), else_=0)).label("block"),
            func.sum(P2POrderRecord.inr_value).label("inr_traded"),
            func.sum(
                case((P2POrderRecord.verdict == "BLOCK", P2POrderRecord.inr_value), else_=0.0)
            ).label("inr_blocked"),
            func.max(P2POrderRecord.decided_at).label("last_seen_at"),
            func.min(P2POrderRecord.created_at).label("first_seen_at"),
            func.max(P2POrderRecord.risk_score).label("peak_risk"),
        ),
        keys,
    ).where(*conds).group_by("buyer_key")
    rows = (await session.execute(stmt)).all()

    ordered = {
        "seen": lambda r: r.seen,
        "flagged": lambda r: r.block,
        "inr_traded": lambda r: r.inr_traded or 0,
        "last_seen_at": lambda r: r.last_seen_at or datetime.min,
        "peak_risk": lambda r: r.peak_risk or 0,
    }
    rows = sorted(rows, key=ordered.get(sort, ordered["seen"]), reverse=True)
    if flagged_only:
        rows = [r for r in rows if r.block > 0]
    page = rows[offset : offset + limit]
    if not page:
        return S.Page[S.CounterpartyRow](items=[], total=len(rows), limit=limit, offset=offset, has_more=False)

    trust_rows = (
        await session.execute(select(Counterparty).where(Counterparty.buyer_key.in_([r.buyer_key for r in page])))
    ).scalars().all()
    trust = {t.buyer_key: t for t in trust_rows}
    names = (
        await session.execute(
            scoped(
                select(P2POrderRecord.buyer_user, P2POrderRecord.buyer_name, buyer_key.label("k")),
                keys,
            ).where(buyer_key.in_([r.buyer_key for r in page])).distinct()
        )
    ).all()
    label = {row.k: (row.buyer_user, row.buyer_name) for row in names if row.k}

    items: list[S.CounterpartyRow] = []
    for row in page:
        state = trust.get(row.buyer_key)
        user, name = label.get(row.buyer_key, (None, None))
        items.append(
            S.CounterpartyRow(
                buyer_key=row.buyer_key or "anon",
                binance_user=user,
                verified_name=name,
                seen=int(row.seen or 0),
                flagged=int(row.block or 0),
                clean_streak=int(state.clean_streak) if state else 0,
                allow=int(row.allow or 0),
                hold=int(row.hold or 0),
                block=int(row.block or 0),
                inr_traded=float(row.inr_traded or 0.0),
                inr_blocked=float(row.inr_blocked or 0.0),
                last_risk=(
                    float(state.last_risk)
                    if state and state.last_risk is not None
                    else float(row.peak_risk or 0.0)
                ),
                last_verdict=state.last_verdict if state else None,
                last_seen_at=aware(state.last_seen_at) if state and state.last_seen_at else aware(row.last_seen_at),
                first_seen_at=aware(row.first_seen_at),
            )
        )
    return S.Page[S.CounterpartyRow](
        items=items, total=len(rows), limit=limit, offset=offset, has_more=(offset + len(items)) < len(rows)
    )


async def list_vouchers(
    session: AsyncSession,
    keys: Sequence[str],
    *,
    pool: str | None = None,
    status: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> S.Page[S.VoucherRow]:
    """Vouchers, scoped by joining each order back to the caller's ledger."""
    scoped_orders = select(P2POrderRecord.order_id).where(P2POrderRecord.merchant_id.in_(list(keys)))
    conds = [SettlementVoucher.order_id.in_(scoped_orders)]
    if pool:
        conds.append(SettlementVoucher.pool == pool)
    if status:
        conds.append(SettlementVoucher.status == status)
    if start is not None:
        conds.append(SettlementVoucher.created_at >= start)
    if end is not None:
        conds.append(SettlementVoucher.created_at <= end)

    total = (await session.execute(select(func.count()).select_from(SettlementVoucher).where(*conds))).scalar_one()
    rows = (
        await session.execute(
            select(SettlementVoucher).where(*conds).order_by(SettlementVoucher.id.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    items = [voucher_row(v) for v in rows]
    return S.Page[S.VoucherRow](
        items=items, total=int(total), limit=limit, offset=offset, has_more=(offset + len(items)) < int(total)
    )


async def latest_bundle(
    session: AsyncSession, keys: Sequence[str], order_id: str
) -> dict[str, Any] | None:
    """The most recent evidence payload for an order, scoped to the caller."""
    row = (
        await session.execute(
            select(EvidenceBundle)
            .where(
                EvidenceBundle.order_id == order_id,
                EvidenceBundle.merchant_id.in_(list(keys)),
            )
            .order_by(EvidenceBundle.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return dict(row.payload) if row else None


async def list_liens(
    session: AsyncSession,
    keys: Sequence[str],
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> S.Page[S.LienRow]:
    conds = [LienCase.merchant_id.in_(list(keys))]
    if status:
        conds.append(LienCase.status == status)
    total = (await session.execute(select(func.count()).select_from(LienCase).where(*conds))).scalar_one()
    rows = (
        await session.execute(
            select(LienCase).where(*conds).order_by(LienCase.id.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    refs = [row.evidence_reference for row in rows if row.evidence_reference]
    have = set()
    if refs:
        found = (
            await session.execute(select(EvidenceBundle.reference).where(EvidenceBundle.reference.in_(refs)))
        ).scalars().all()
        have = set(found)
    items = [lien_row(row, bool(row.evidence_reference and row.evidence_reference in have)) for row in rows]
    return S.Page[S.LienRow](
        items=items, total=int(total), limit=limit, offset=offset, has_more=(offset + len(items)) < int(total)
    )


async def get_lien(session: AsyncSession, keys: Sequence[str], case_ref: str) -> S.LienRow | None:
    """One freeze case, read back through the same mapper the list uses."""
    row = (
        await session.execute(
            select(LienCase).where(LienCase.case_ref == case_ref, LienCase.merchant_id.in_(list(keys)))
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return await _lien_with_evidence(session, row)


async def _lien_with_evidence(session: AsyncSession, row: LienCase) -> S.LienRow:
    has_evidence = False
    if row.evidence_reference:
        has_evidence = bool(
            (
                await session.execute(
                    select(EvidenceBundle.id).where(EvidenceBundle.reference == row.evidence_reference).limit(1)
                )
            ).scalar()
        )
    return lien_row(row, has_evidence)


async def update_lien(
    session: AsyncSession, keys: Sequence[str], case_ref: str, status: str, note: str | None = None
) -> S.LienRow | None:
    """Move a freeze case along its board. Returns None when the case is not ours.

    ``note`` is appended to ``notice_text`` with a timestamp rather than dropped:
    the case file is the artefact that goes to the bank, so an internal remark
    that vanishes would be worse than one that is visibly dated.
    """
    row = (
        await session.execute(
            select(LienCase).where(LienCase.case_ref == case_ref, LienCase.merchant_id.in_(list(keys)))
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    row.status = status
    if note and note.strip():
        stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        row.notice_text = f"{row.notice_text or ''}\n\n[{stamp}] {note.strip()}".strip()
    row.updated_at = datetime.now(UTC).replace(tzinfo=None)
    await session.commit()
    return await _lien_with_evidence(session, row)


async def list_compliance(
    session: AsyncSession,
    keys: Sequence[str],
    *,
    event_type: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> S.Page[S.ComplianceRow]:
    conds = Filters(start=start, end=end).conditions()
    scoped_orders = scoped(select(P2POrderRecord.order_id), keys).where(*conds)
    where = [ComplianceEvent.order_id.in_(scoped_orders)]
    if event_type:
        where.append(ComplianceEvent.event_type == event_type)
    total = (await session.execute(select(func.count()).select_from(ComplianceEvent).where(*where))).scalar_one()
    rows = (
        await session.execute(
            select(ComplianceEvent).where(*where).order_by(ComplianceEvent.id.desc()).limit(limit).offset(offset)
        )
    ).scalars().all()
    items = [
        S.ComplianceRow(
            event_type=row.event_type,
            order_id=row.order_id,
            amount=row.amount,
            created_at=aware(row.created_at) or row.created_at,
            payload=dict(row.payload or {}),
        )
        for row in rows
    ]
    return S.Page[S.ComplianceRow](
        items=items, total=int(total), limit=limit, offset=offset, has_more=(offset + len(items)) < int(total)
    )


async def record_override(
    session: AsyncSession, keys: Sequence[str], order_id: str, actor_email: str, action: str, reason: str
) -> S.OverrideRow | None:
    """Append an override. The verdict row is never mutated."""
    record, _ = await get_record(session, keys, order_id)
    if record is None:
        return None
    note = OverrideNote(
        order_id=order_id,
        merchant_key=record.merchant_id,
        actor_email=actor_email,
        action=action,
        from_verdict=record.verdict,
        reason=reason,
    )
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return S.OverrideRow(
        actor_email=note.actor_email,
        action=note.action,
        from_verdict=note.from_verdict,
        reason=note.reason,
        created_at=aware(note.created_at) or datetime.now(UTC),
    )
