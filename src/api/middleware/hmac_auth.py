"""HMAC signature middleware for merchant-bot callbacks.

The bot authenticates its calls to the guard by signing the raw request body:

    X-Sentinel-Signature = hex(hmac_sha256(secret, f"{timestamp}." + body))
    X-Sentinel-Timestamp = unix seconds

It is opt-in: enforcement is only active when GUARD_HMAC_SECRET is set, and it
only guards POST requests under /api/v1/p2p/ (the two gates + lien intake), so
every other endpoint and the existing tests are unaffected.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

_PREFIX = "/api/v1/p2p/"
_TOLERANCE_S = 300


def _secret() -> str:
    return os.getenv("GUARD_HMAC_SECRET", "").strip()


def verify(secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    """Constant-time verification of a signed payload."""
    message = f"{timestamp}.".encode() + body
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


class HmacAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next) -> Response:  # noqa: ANN001
        secret = _secret()
        guarded = request.method == "POST" and request.url.path.startswith(_PREFIX)

        if not secret or not guarded:
            return await call_next(request)

        body = await request.body()  # cached; downstream handlers can re-read
        timestamp = request.headers.get("X-Sentinel-Timestamp", "")
        signature = request.headers.get("X-Sentinel-Signature", "")

        try:
            fresh = abs(time.time() - float(timestamp)) <= _TOLERANCE_S
        except ValueError:
            fresh = False

        if not fresh or not verify(secret, timestamp, body, signature):
            logger.warning("HMAC verification failed for %s", request.url.path)
            return JSONResponse({"detail": "invalid or missing signature"}, status_code=401)

        return await call_next(request)
