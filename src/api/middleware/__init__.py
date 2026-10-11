"""ASGI middleware for the Sentinel API.

Only request-level hooks that wrap the whole application belong here. FastAPI
dependencies (``Depends`` providers) live in :mod:`src.api.dependencies`, and the
rate-limit decorator in :mod:`src.api.rate_limit`.
"""
