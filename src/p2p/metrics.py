"""Prometheus metrics for the guard (graceful when the client is absent).

Decision mix, vendor latency and vendor spend are the three numbers an operator
needs on a dashboard to tune thresholds and control per-order vendor cost. If
``prometheus-client`` is not installed these degrade to no-ops so the guard
still runs.
"""

from __future__ import annotations

try:
    from prometheus_client import Counter, Histogram

    _DECISIONS = Counter(
        "sentinel_p2p_guard_decisions_total",
        "Guard verdicts",
        ["verdict", "phase", "degraded"],
    )
    _VENDOR_LATENCY = Histogram(
        "sentinel_p2p_vendor_latency_ms",
        "Vendor call latency (ms)",
        ["provider", "category", "status"],
        buckets=(50, 100, 250, 500, 1000, 2000, 4000, 6000),
    )
    _VENDOR_COST = Counter(
        "sentinel_p2p_vendor_cost_usd_total",
        "Approx vendor spend",
        ["provider"],
    )
    _ENABLED = True
except ImportError:  # pragma: no cover
    _ENABLED = False


def record_decision(verdict: str, phase: str, degraded: bool) -> None:
    if _ENABLED:
        _DECISIONS.labels(verdict=verdict, phase=phase, degraded=str(degraded).lower()).inc()


def record_vendor(provider: str, category: str, status: str, latency_ms: int, cost_usd: float) -> None:
    if not _ENABLED:
        return
    _VENDOR_LATENCY.labels(provider=provider, category=category, status=status).observe(latency_ms)
    if cost_usd:
        _VENDOR_COST.labels(provider=provider).inc(cost_usd)
