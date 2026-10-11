"""Chainalysis Address Screening adapter.

POST https://api.chainalysis.com/api/risk/v2/entities  {"address": "..."}
with header ``Key: <api_key>``. The response ``risk`` field is a category
label; we map the worst categories to a 0..1 exposure score.
"""

from __future__ import annotations

from src.screening.schemas import ProviderCategory, ProviderStatus
from src.vendors._http import HttpError, request_json
from src.vendors.base import AddressSubject, ProviderError, ProviderUnavailable, ScreeningProvider, SubjectKind

_RISK_MAP = {
    "norisk": 0.02, "no risk": 0.02, "exchanger": 0.05, "merchant": 0.05,
    "payment processor": 0.1, "personal wallet": 0.1, "money transmitter": 0.2,
    "mixer": 0.6, "dark_web": 0.7, "dark web market": 0.75, "sanctions": 0.97,
    "sanctions_scanner": 0.97, "ransomware": 0.95, "hackmed": 0.9, "fraud": 0.85,
    "stolen": 0.85, "exploit": 0.85, "ofac": 0.97,
}


class ChainalysisProvider(ScreeningProvider):
    name = "chainalysis"
    category = ProviderCategory.WALLET
    weight = 1.0
    required = True
    fail_closed = True
    cache_ttl = 900
    tier = 1

    URL = "https://api.chainalysis.com/api/risk/v2/entities"

    def __init__(self, api_key: str | None) -> None:
        self._key = api_key

    def handles(self, kind: SubjectKind) -> bool:
        return kind == SubjectKind.ADDRESS

    async def screen(self, subject: AddressSubject):
        if not self._key:
            raise ProviderUnavailable("CHAINANALYSIS_API_KEY not set")
        try:
            data, latency = await request_json(
                "POST", self.URL, headers={"Key": self._key}, json_body={"address": subject.address}
            )
        except HttpError as exc:
            raise ProviderError(str(exc)) from exc
        category = str(data.get("risk", "")).strip()
        risk = _RISK_MAP.get(category.lower(), 0.3)
        detail = f"Chainalysis risk={category or 'unknown'}"
        if risk >= 0.9:
            detail = f"Chainalysis HIGH RISK: {category}"
        return self._verdict(
            status=ProviderStatus.OK,
            risk=risk,
            matched_list=category or "unknown",
            detail=detail,
            raw_ref=str(data.get("guid", "")),
            latency_ms=latency,
        )
