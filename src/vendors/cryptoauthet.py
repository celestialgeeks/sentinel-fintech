"""CryptoAuthet (India) wallet-screening adapter.

GET <base>/screen/<address> with header ``Authkey: <api_key>``. Response carries
a numeric ``Score`` and textual ``RiskLevel``; both are folded into 0..1.
"""

from __future__ import annotations

from src.screening.schemas import ProviderCategory, ProviderStatus
from src.vendors._http import HttpError, request_json
from src.vendors.base import AddressSubject, ProviderError, ProviderUnavailable, ScreeningProvider, SubjectKind

_LEVEL = {"low": 0.1, "medium": 0.5, "high": 0.8, "severe": 0.9, "sanctioned": 0.98}


class CryptoAuthetProvider(ScreeningProvider):
    name = "cryptoauthet"
    category = ProviderCategory.WALLET
    weight = 0.9
    required = False
    fail_closed = False
    cache_ttl = 900
    tier = 1

    def __init__(self, api_key: str | None, base_url: str) -> None:
        self._key = api_key
        self._base = base_url.rstrip("/")

    def handles(self, kind: SubjectKind) -> bool:
        return kind == SubjectKind.ADDRESS

    async def screen(self, subject: AddressSubject):
        if not self._key:
            raise ProviderUnavailable("CRYPTOAUTHET_API_KEY not set")
        try:
            data, latency = await request_json(
                "GET", f"{self._base}/screen/{subject.address}", headers={"Authkey": self._key}
            )
        except HttpError as exc:
            raise ProviderError(str(exc)) from exc
        level = str(data.get("RiskLevel", "")).lower()
        score = float(data.get("Score", 0) or 0)
        risk = max(_LEVEL.get(level, 0.2), min(1.0, score / 100.0))
        return self._verdict(
            status=ProviderStatus.OK, risk=risk, matched_list=level,
            detail=f"CryptoAuthet RiskLevel={level} Score={score}",
            raw_ref=str(data.get("TxnId", "")), latency_ms=latency,
        )
