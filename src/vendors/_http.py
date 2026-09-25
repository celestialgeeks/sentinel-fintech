# ruff: noqa: PLR0913
"""Minimal async JSON HTTP helper shared by vendor adapters."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:  # pragma: no cover - httpx is a project dependency
    httpx = None  # type: ignore


class HttpError(RuntimeError):
    """Non-2xx response or transport error from a vendor."""

    def __init__(self, status: int, body: str = "") -> None:
        super().__init__(f"vendor HTTP {status}")
        self.status = status
        self.body = body


async def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 6.0,
) -> tuple[dict[str, Any], int]:
    """Perform a request and return ``(parsed_json, latency_ms)``.

    Raises :class:`HttpError` on transport failure or a non-2xx status so the
    caller can translate it into a :class:`~src.vendors.base.ProviderError`.
    """
    if httpx is None:  # pragma: no cover
        raise HttpError(0, "httpx not installed")
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(method, url, headers=headers, json=json_body, params=params)
    except httpx.HTTPError as exc:  # network/timeout
        raise HttpError(0, str(exc)) from exc
    latency_ms = int((time.monotonic() - start) * 1000)
    if resp.status_code >= 400:
        raise HttpError(resp.status_code, resp.text[:500])
    try:
        data = resp.json()
    except ValueError:
        data = {}
    return data, latency_ms
