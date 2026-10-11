# ruff: noqa: PLC0415
"""Sanctions / PEP screening.

Two implementations:

* :class:`LocalListSanctionsProvider` - works with no API key by reusing the
  existing watchlist module (``src.screening.watchlists``) plus fuzzy resolution
  from ``src.screening.entity_resolution``. This keeps sanctions screening live
  in dev/CI.
* :class:`RemoteSanctionsProvider` - a commercial feed (World-Check / LSEG /
  Dow Jones); only used when a feed URL + key are configured.
"""

from __future__ import annotations

from src.screening.schemas import ProviderCategory, ProviderStatus
from src.vendors._http import HttpError, request_json
from src.vendors.base import NameSubject, ProviderError, ProviderUnavailable, ScreeningProvider, SubjectKind


class LocalListSanctionsProvider(ScreeningProvider):
    name = "sanctions_local"
    category = ProviderCategory.SANCTIONS
    weight = 1.0
    required = True
    fail_closed = False  # always available, so no fail-closed needed
    cache_ttl = 3600
    tier = 0

    def handles(self, kind: SubjectKind) -> bool:
        return kind == SubjectKind.NAME

    async def screen(self, subject: NameSubject):
        # Imported lazily to avoid a hard module-load cycle with screening.*
        from src.screening.watchlists import search_by_name

        matches = search_by_name(subject.name)
        if matches:
            top = max(matches, key=lambda m: m.risk_weight)
            return self._verdict(
                status=ProviderStatus.OK,
                risk=top.risk_weight,
                matched_list=top.list_source,
                detail=f"Watchlist match: {top.name} ({top.list_source})",
                raw_ref=top.entity_id,
            )
        return self._verdict(risk=0.0, detail="No sanctions/PEP match on local list")


class RemoteSanctionsProvider(ScreeningProvider):
    name = "sanctions_feed"
    category = ProviderCategory.SANCTIONS
    weight = 1.0
    required = True
    fail_closed = True
    cache_ttl = 3600
    tier = 1

    def __init__(self, base_url: str | None, api_key: str | None) -> None:
        self._url = base_url
        self._key = api_key

    def handles(self, kind: SubjectKind) -> bool:
        return kind == SubjectKind.NAME

    async def screen(self, subject: NameSubject):
        if not (self._url and self._key):
            raise ProviderUnavailable("sanctions feed not configured")
        try:
            data, latency = await request_json(
                "POST",
                self._url,
                headers={"Authorization": f"Bearer {self._key}"},
                json_body={"name": subject.name, "country": subject.country},
            )
        except HttpError as exc:
            raise ProviderError(str(exc)) from exc
        hits = data.get("results") or data.get("matches") or []
        if hits:
            score = float(hits[0].get("score", hits[0].get("matchScore", 0.9)))
            return self._verdict(
                risk=min(1.0, score),
                matched_list="feed",
                detail=f"{len(hits)} adverse-media/sanctions hit(s)",
                raw_ref=str(hits[0].get("id", "")),
                latency_ms=latency,
            )
        return self._verdict(risk=0.0, detail="Feed: no match", latency_ms=latency)
