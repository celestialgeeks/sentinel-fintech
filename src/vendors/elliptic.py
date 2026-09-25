"""Elliptic Lens connection-assessment adapter.

Uses OAuth2 client-credentials then POST /v1/data-insights/connection-assessments.
Response ``overallRiskScore`` (0..5) is mapped to 0..1. Guarded by ELLIPTIC_API_KEY.
"""

from __future__ import annotations

from src.screening.schemas import ProviderCategory, ProviderStatus
from src.vendors._http import HttpError, request_json
from src.vendors.base import AddressSubject, ProviderError, ProviderUnavailable, ScreeningProvider, SubjectKind


class EllipticProvider(ScreeningProvider):
    name = "elliptic"
    category = ProviderCategory.WALLET
    weight = 1.0
    required = False
    fail_closed = True
    cache_ttl = 900
    tier = 2  # pricier; used as a second opinion on high-value orders

    AUTH_URL = "https://rest.elliptic.co/api/v1/oauth2/token"
    ASSESS_URL = "https://rest.elliptic.co/api/v1/data-insights/connection-assessments"

    def __init__(self, api_key: str | None) -> None:
        self._key = api_key

    def handles(self, kind: SubjectKind) -> bool:
        return kind == SubjectKind.ADDRESS

    async def screen(self, subject: AddressSubject):
        if not self._key:
            raise ProviderUnavailable("ELLIPTIC_API_KEY not set")
        try:
            token_data, _ = await request_json(
                "POST", self.AUTH_URL,
                headers={"Authorization": f"Basic {self._key}"},
                params={"grant_type": "client_credentials"},
            )
            token = token_data.get("access_token", "")
            data, latency = await request_json(
                "POST", self.ASSESS_URL,
                headers={"Authorization": f"Bearer {token}"},
                json_body={"originatorAddress": subject.address, "blockchain": subject.chain.lower()},
            )
        except HttpError as exc:
            raise ProviderError(str(exc)) from exc
        overall = float(data.get("overallRiskScore", 0) or 0)
        risk = min(1.0, overall / 5.0)
        return self._verdict(
            status=ProviderStatus.OK, risk=risk,
            matched_list=str(data.get("riskCategory", "")),
            detail=f"Elliptic overallRiskScore={overall}",
            raw_ref=str(data.get("connectionAssessmentId", "")),
            latency_ms=latency,
        )
