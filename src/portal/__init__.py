"""Merchant portal backend: auth, scoped ledger reads, and integration keys.

The guard itself (``src.p2p``) answers one question for a bot in milliseconds and
returns a verdict. This package answers the different question a human has:
*what happened to my money, and can I prove it?* — so it is a read layer over the
same tables, wrapped in session auth and merchant scoping.

Slices, each with its own router:

:mod:`~src.portal.auth`
    ``/auth/*`` signup, login, me, workspace creation.
:mod:`~src.portal.integrations`
    ``/integration/*`` keys, status, sandbox connection test.
:mod:`~src.portal.ledger`
    ``/portal/*`` orders, buyers, vouchers, freeze cases, compliance, exports and
    the live decision feed, plus the dashboard aggregates.

Shared plumbing:

:mod:`~src.portal.config`
    Environment settings (JWT secret, CORS origins).
:mod:`~src.portal.security`
    PBKDF2 passwords, HS256 session tokens, bot credentials. No third-party deps.
:mod:`~src.portal.deps`
    ``Depends`` providers that resolve a token into an :class:`AccessScope`.
:mod:`~src.portal.schemas`
    The response models the frontend is built against, one module per capability.
"""
