"""Portal ledger slice — merchant-scoped reads over the guard's own output.

The guard (``src.p2p``) writes; this slice reads. Three rules govern everything
in the package.

1. **Merchant scoping is not optional.** Every query takes the tuple of merchant
   keys resolved from the session and puts it in the WHERE clause. A detail fetch
   that does not belong to the caller returns ``None`` (404 at the router), never
   the row.
2. **Columns are preferred over JSON.** The ledger filters on ``verdict``,
   ``risk_score`` and ``utr``, so those are real columns on ``p2p_orders``. The
   evidence bundle's JSON payload is used only for fields nobody filters on
   (trade count, completion rate, chat snippet, wallet addresses).
3. **Cross-dialect SQL only.** Aggregation is plain ``count/sum/max`` plus
   ``CASE``; anything that would need PostgreSQL-only syntax (date binning,
   percentiles, array unnesting) is done in Python over a bounded row set.

Modules:

:mod:`~src.portal.ledger.router`
    ``/portal/*`` endpoints: orders, holds, buyers, vouchers, liens, compliance,
    CSV export and the SSE feed.
:mod:`~src.portal.ledger.scoping`
    :func:`scoped`, the :class:`Filters` vocabulary, and scope-metadata lookups.
:mod:`~src.portal.ledger.mappers`
    Pure ORM-row → response-model shaping (no session, no SQL).
:mod:`~src.portal.ledger.orders`
    The ledger page, one order's detail, and the incremental feed.
:mod:`~src.portal.ledger.cases`
    Counterparties, settlement vouchers, freeze cases, compliance events, and the
    two writes: override notes and lien status.
:mod:`~src.portal.ledger.aggregates`
    Dashboard aggregates: KPI strip, verdict mix, histogram, provider health.
"""
