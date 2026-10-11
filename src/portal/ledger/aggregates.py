"""Aggregates behind the dashboard, live feed and insights screens.

Percentiles, date bins and rule attribution are computed in Python over a
bounded row set instead of dialect-specific SQL. Two reasons: the portal must
run on the SQLite database the tests use as well as PostgreSQL, and a merchant
ledger is small enough (thousands of decisions a day, not billions) that the
read is cheaper than the complexity of maintaining two SQL dialects. Every
function here caps the rows it pulls and says so in the response.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import (
    LienCase,
    P2POrderRecord,
    SettlementVoucher,
    VendorCall,
)
from src.portal import schemas as S  # noqa: N812 - short alias keeps response models readable
from src.portal.ledger.mappers import order_row
from src.portal.ledger.orders import enrich
from src.portal.ledger.scoping import Filters, scoped

# A HOLD older than this has missed the Binance P2P release window.
RELEASE_WINDOW_MINUTES = 15

# Max ledger rows a single aggregate call will read. Beyond this the numbers are
# computed on the most recent slice, which the response marks with `partial`.
MAX_AGG_ROWS = 20_000

# Fixed grid origin for time bucketing (naive UTC, same convention as the ledger).
_EPOCH = datetime(2020, 1, 1)

_WINDOWS: dict[str, timedelta] = {
    "today": timedelta(hours=0),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def window_bounds(window: str, now: datetime | None = None) -> tuple[datetime | None, datetime]:
    """Half-open ``[start, end]`` in naive UTC for a named window.

    ``today`` means calendar-to-date in UTC, which is how the ledger is stored;
    the frontend renders the result in IST.
    """
    now = (now or datetime.now(UTC)).replace(tzinfo=None)
    span = _WINDOWS.get(window, _WINDOWS["24h"])
    if window == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0), now
    if window == "all":
        return None, now
    return now - span, now


def percentile(values: Sequence[float], q: float) -> float:
    """Nearest-rank percentile. Empty input is 0, not an error."""
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, int(round((q / 100.0) * len(ordered))))
    return float(ordered[min(rank - 1, len(ordered) - 1)])


def median(values: Sequence[float]) -> float:
    return percentile(values, 50)


async def _ledger_rows(
    session: AsyncSession, keys: Sequence[str], start: datetime | None, end: datetime | None
) -> list[P2POrderRecord]:
    conds = Filters(start=start, end=end).conditions()
    stmt = scoped(select(P2POrderRecord), keys).where(*conds).order_by(P2POrderRecord.id.desc()).limit(MAX_AGG_ROWS)
    return list((await session.execute(stmt)).scalars().all())


def _verdict_counts(rows: Iterable[P2POrderRecord]) -> S.VerdictCounts:
    rows = list(rows)
    return S.VerdictCounts(
        allow=sum(1 for r in rows if r.verdict == "ALLOW"),
        hold=sum(1 for r in rows if r.verdict == "HOLD"),
        block=sum(1 for r in rows if r.verdict == "BLOCK"),
        degraded=sum(1 for r in rows if r.degraded),
    )


async def summary(
    session: AsyncSession,
    keys: Sequence[str],
    *,
    window: str = "today",
    latencies: Sequence[float] | None = None,
    spend_usd: float | None = None,
) -> S.StatsSummary:
    """The KPI strip on the overview screen."""
    start, end = window_bounds(window)
    rows = await _ledger_rows(session, keys, start, end)
    counts = _verdict_counts(rows)
    blocked = float(sum(r.inr_value for r in rows if r.verdict == "BLOCK"))
    released = float(sum(r.inr_value for r in rows if r.verdict == "ALLOW"))
    on_hold = float(sum(r.inr_value for r in rows if r.verdict == "HOLD"))
    now = datetime.now(UTC).replace(tzinfo=None)
    overdue = sum(
        1
        for r in rows
        if r.verdict == "HOLD" and r.decided_at and (now - r.decided_at) > timedelta(minutes=RELEASE_WINDOW_MINUTES)
    )

    if latencies is None:
        latencies = await vendor_latency(session, keys, start=start, end=end)
    if spend_usd is None:
        spend_usd = await vendor_spend(session, keys, start=start, end=end)

    quarantine, awaiting, unmatched = await pool_totals(session, keys)
    open_liens = (
        await session.execute(
            select(func.count()).select_from(LienCase).where(
                LienCase.merchant_id.in_(list(keys)), LienCase.status.notin_(["lifted", "rejected"])
            )
        )
    ).scalar_one()

    total = len(rows)
    return S.StatsSummary(
        merchant_keys=list(keys),
        window=window,
        orders=total,
        verdicts=counts,
        inr_blocked=round(blocked, 2),
        inr_released=round(released, 2),
        inr_on_hold=round(on_hold, 2),
        auto_cleared_pct=round((counts.allow / total) * 100, 2) if total else 0.0,
        median_latency_ms=round(median(latencies), 2),
        p95_latency_ms=round(percentile(latencies, 95), 2),
        vendor_spend_usd=round(float(spend_usd), 4),
        spend_per_order_usd=round(float(spend_usd) / total, 6) if total else 0.0,
        holds_open=counts.hold,
        holds_overdue=overdue,
        quarantine_inr=round(quarantine, 2),
        awaiting_sweep_inr=round(awaiting, 2),
        unmatched_credits=unmatched,
        lien_cases_open=int(open_liens or 0),
    )


async def pool_totals(session: AsyncSession, keys: Sequence[str]) -> tuple[float, float, int]:
    """Quarantine balance, sweep-pending balance, and credits with no voucher.

    ``unmatched`` counts release-gate decisions that carry a UTR but never got a
    voucher — the exact shape of "money arrived that we cannot attribute", which
    is what turns one buyer into an account-wide freeze.
    """
    scoped_orders = scoped(select(P2POrderRecord.order_id), keys)
    vouchers = (
        await session.execute(select(SettlementVoucher).where(SettlementVoucher.order_id.in_(scoped_orders)))
    ).scalars().all()
    quarantine = float(sum(v.amount or 0.0 for v in vouchers if v.pool == "quarantine" and v.status != "swept"))
    awaiting = float(
        sum(
            v.amount or 0.0
            for v in vouchers
            if v.pool == "quarantine" and v.status in ("issued", "credited") and v.sweep_after is not None
        )
    )
    unmatched = (
        await session.execute(
            scoped(
                select(func.count()).select_from(P2POrderRecord).where(
                    P2POrderRecord.phase == "release_gate",
                    P2POrderRecord.utr.is_not(None),
                    P2POrderRecord.utr != "",
                    P2POrderRecord.order_id.notin_(
                        select(SettlementVoucher.order_id).where(SettlementVoucher.order_id.is_not(None))
                    ),
                ),
                keys,
            )
        )
    ).scalar_one()
    return quarantine, awaiting, int(unmatched or 0)


async def vendor_latency(
    session: AsyncSession, keys: Sequence[str], *, start: datetime | None = None, end: datetime | None = None
) -> list[float]:
    """Per-order worst vendor call, in ms — the latency the bot actually waited."""
    conds = Filters(start=start, end=end).conditions()
    orders = scoped(select(P2POrderRecord.order_id).where(*conds), keys)
    rows = (
        await session.execute(
            select(VendorCall.order_id, VendorCall.phase, func.max(VendorCall.latency_ms))
            .where(VendorCall.order_id.in_(orders))
            .group_by(VendorCall.order_id, VendorCall.phase)
            .limit(MAX_AGG_ROWS)
        )
    ).all()
    return [float(latency or 0) for _order, _phase, latency in rows]


async def vendor_spend(
    session: AsyncSession, keys: Sequence[str], *, start: datetime | None = None, end: datetime | None = None
) -> float:
    conds = Filters(start=start, end=end).conditions()
    orders = scoped(select(P2POrderRecord.order_id).where(*conds), keys)
    value = (
        await session.execute(select(func.sum(VendorCall.cost_usd)).where(VendorCall.order_id.in_(orders)))
    ).scalar()
    return float(value or 0.0)


def timeseries(rows: Sequence[P2POrderRecord], *, bucket_minutes: int = 60) -> list[S.TimeseriesPoint]:
    """Verdict counts per fixed bucket, oldest first, gaps filled with zeroes.

    Buckets are aligned to an absolute epoch rather than to the first row, so the
    same window always produces the same x-axis — a chart that slides because the
    first decision landed at :07 is unreadable on a wallboard.
    """
    stamps = [row.decided_at for row in rows if row.decided_at]
    if not stamps:
        return []
    step = timedelta(minutes=max(1, bucket_minutes))
    buckets: dict[int, list[P2POrderRecord]] = defaultdict(list)
    for row in rows:
        if not row.decided_at:
            continue
        offset = int((row.decided_at - _EPOCH).total_seconds() // step.total_seconds())
        buckets[offset].append(row)

    out: list[S.TimeseriesPoint] = []
    for offset in range(min(buckets), max(buckets) + 1):
        group = buckets.get(offset, [])
        out.append(
            S.TimeseriesPoint(
                bucket=(_EPOCH + step * offset).replace(tzinfo=UTC),
                allow=sum(1 for r in group if r.verdict == "ALLOW"),
                hold=sum(1 for r in group if r.verdict == "HOLD"),
                block=sum(1 for r in group if r.verdict == "BLOCK"),
                inr_blocked=round(float(sum(r.inr_value for r in group if r.verdict == "BLOCK")), 2),
                decisions=len(group),
            )
        )
    return out


def risk_histogram(rows: Sequence[P2POrderRecord], *, buckets: int = 20) -> list[S.RiskBucket]:
    """Risk distribution with the BLOCK/HOLD thresholds drawn over it."""
    width = 1.0 / buckets
    counts = [0] * buckets
    for row in rows:
        index = min(buckets - 1, int(row.risk_score / width))
        counts[max(0, index)] += 1
    return [
        S.RiskBucket(low=round(i * width, 4), high=round((i + 1) * width, 4), count=counts[i])
        for i in range(buckets)
    ]


def rule_stats(rows: Sequence[P2POrderRecord], *, limit: int = 12) -> list[S.RuleStat]:
    """Which signals fire, and how often firing one ended in a BLOCK.

    Attributed from ``hard_rules`` (decisive) and ``reasons`` prefixes (soft),
    because the engine stores the rule name in both.
    """
    triggers: Counter[str] = Counter()
    led_to_block: Counter[str] = Counter()
    for row in rows:
        names: set[str] = set()
        for hard in row.hard_rules or []:
            names.add(str(hard))
        for reason in row.reasons or []:
            text = str(reason)
            if ":" in text:
                names.add(text.split(":", 1)[0].strip())
        for name in names:
            if name and not name.lower().startswith("required vendor") and "voucher" not in name.lower():
                triggers[name] += 1
                if row.verdict == "BLOCK":
                    led_to_block[name] += 1
    ordered = sorted(triggers, key=lambda name: triggers[name], reverse=True)[:limit]
    return [
        S.RuleStat(name=name, triggers=triggers[name], led_to_block=led_to_block.get(name, 0)) for name in ordered
    ]


async def provider_stats(session: AsyncSession, keys: Sequence[str], *, start: datetime | None = None,
                         end: datetime | None = None) -> list[S.ProviderStat]:
    """Per-provider call health: status mix, latency, cost."""
    conds = Filters(start=start, end=end).conditions()
    orders = scoped(select(P2POrderRecord.order_id).where(*conds), keys)
    rows = (
        await session.execute(
            select(
                VendorCall.provider,
                VendorCall.category,
                VendorCall.status,
                VendorCall.latency_ms,
                VendorCall.cost_usd,
            )
            .where(VendorCall.order_id.in_(orders))
            .limit(MAX_AGG_ROWS)
        )
    ).all()
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for provider, category, status, latency, cost in rows:
        entry = grouped.setdefault((provider, category), {"latency": [], "cost": 0.0, "counts": Counter()})
        entry["latency"].append(float(latency or 0))
        entry["cost"] += float(cost or 0.0)
        entry["counts"][status] += 1
    out: list[S.ProviderStat] = []
    for (provider, category), entry in grouped.items():
        counts: Counter = entry["counts"]
        total = sum(counts.values())
        unhealthy = counts["error"] + counts["unavailable"]
        if not counts["ok"]:
            health = "down"
        elif unhealthy and unhealthy >= max(1, total // 5):
            health = "degraded"
        else:
            health = "ok"
        out.append(
            S.ProviderStat(
                provider=provider,
                category=category,
                calls=total,
                ok=counts["ok"],
                errored=counts["error"],
                unavailable=counts["unavailable"],
                skipped=counts["skipped"],
                p50_latency_ms=round(median(entry["latency"]), 2),
                p95_latency_ms=round(percentile(entry["latency"], 95), 2),
                cost_usd=round(entry["cost"], 4),
                status=health,
            )
        )
    return sorted(out, key=lambda stat: stat.calls, reverse=True)


async def latency_by_order(
    session: AsyncSession, keys: Sequence[str], *, start: datetime | None = None, end: datetime | None = None
) -> dict[tuple[str, str], float]:
    """(order_id, phase) -> slowest vendor call for that decision, in ms."""
    conds = Filters(start=start, end=end).conditions()
    orders = scoped(select(P2POrderRecord.order_id).where(*conds), keys)
    rows = (
        await session.execute(
            select(VendorCall.order_id, VendorCall.phase, func.max(VendorCall.latency_ms))
            .where(VendorCall.order_id.in_(orders))
            .group_by(VendorCall.order_id, VendorCall.phase)
            .limit(MAX_AGG_ROWS)
        )
    ).all()
    return {(order_id, phase): float(latency or 0) for order_id, phase, latency in rows}


async def sparklines(session: AsyncSession, keys: Sequence[str], *, days: int = 7) -> dict[str, S.Sparkline]:
    """Daily series for the KPI cards, oldest to newest, missing days as zero.

    Latency is the real per-order vendor latency, not a stand-in: a sparkline
    that quietly plots something else is worse than one that is absent.
    """
    today = datetime.now(UTC).replace(tzinfo=None).date()
    start = datetime.combine(today - timedelta(days=days - 1), datetime.min.time())
    rows = await _ledger_rows(session, keys, start, None)
    per_order = await latency_by_order(session, keys, start=start, end=None)

    days_list = [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]
    index = {day: position for position, day in enumerate(days_list)}

    series: dict[str, list[float]] = {
        "orders": [0.0] * days,
        "blocked": [0.0] * days,
        "inr_blocked": [0.0] * days,
        "latency": [0.0] * days,
    }
    latency_by_day: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        stamp = row.decided_at or row.created_at
        position = index.get(stamp.date())
        if position is None:
            continue
        series["orders"][position] += 1
        if row.verdict == "BLOCK":
            series["blocked"][position] += 1
            series["inr_blocked"][position] += row.inr_value
        if (row.order_id, row.phase) in per_order:
            latency_by_day[position].append(per_order[(row.order_id, row.phase)])
    series["latency"] = [round(median(latency_by_day.get(p, [])), 2) for p in range(days)]
    return {name: S.Sparkline(values=[round(value, 2) for value in values]) for name, values in series.items()}


async def overview(
    session: AsyncSession, keys: Sequence[str], *, window: str = "today", needs_action_limit: int = 8
) -> S.OverviewResponse:
    """One call that fills the whole overview screen.

    The ledger slice is read once and reused for every chart, so the cards cannot
    disagree with each other the way five independent queries would.
    """
    start, end = window_bounds(window)
    rows = await _ledger_rows(session, keys, start, end)
    latencies = await vendor_latency(session, keys, start=start, end=end)
    spend = await vendor_spend(session, keys, start=start, end=end)
    stats = await summary(session, keys, window=window, latencies=latencies, spend_usd=spend)

    mix_by_phase = {
        phase: _verdict_counts([row for row in rows if row.phase == phase])
        for phase in ("pre_screen", "release_gate")
    }
    needs = [row for row in rows if row.verdict == "HOLD"]
    needs.sort(key=lambda row: row.decided_at or datetime.min)
    urgent = needs[:needs_action_limit]
    vouchers, costs = await enrich(session, urgent)

    return S.OverviewResponse(
        summary=stats,
        mix=stats.verdicts,
        mix_by_phase=mix_by_phase,
        risk_histogram=risk_histogram(rows),
        timeseries=timeseries(rows, bucket_minutes=_bucket_for(window)),
        top_rules=rule_stats(rows),
        providers=await provider_stats(session, keys, start=start, end=end),
        needs_action=[
            order_row(rec, vouchers.get(rec.order_id), *costs.get((rec.order_id, rec.phase), (0.0, 0)))
            for rec in urgent
        ],
        sparklines=await sparklines(session, keys),
    )


def _bucket_for(window: str) -> int:
    """Chart resolution per window: 30 min for today, a day for a month."""
    return {"today": 30, "24h": 60, "7d": 360, "30d": 1440}.get(window, 60)
