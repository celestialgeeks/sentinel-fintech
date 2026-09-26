"""Sentinel API layer — the composition root.

:mod:`src.api.main` builds the FastAPI app and mounts each domain slice's router;
:mod:`src.api.middleware` holds ASGI middleware, :mod:`src.api.dependencies` the
reusable ``Depends`` providers, and :mod:`src.api.rate_limit` the throttling
decorator. No domain logic lives in this package.
"""
