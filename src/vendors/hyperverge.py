"""HyperVerge bank-account / mule risk adapter (alternate to IDfy).

Header-keyed REST. Contributes a MULE / BANK_ACCOUNT verdict. Guarded by
HYPERVERGE_API_KEY.
"""

from __future__ import annotations

from src.screening.schemas import ProviderCategory, ProviderStatus
from src.vendors._http import HttpError, request_json
from src.vendors.base import BankSubject, ProviderError, ProviderUnavailable, ScreeningProvider, SubjectKind


class HyperVergeProvider(ScreeningProvider):
    name = "hyperverge"
    category = ProviderCategory.MULE
    weight = 0.9
    required = False
    fail_closed = False
    cache_ttl = 600
    tier = 2

    URL = "https://api.hyperverge.co/v1/bank/account-verifier"  # confirm per contracted product

    def __init__(self, api_key: str | None) -> None:
        self._key = api_key

    def handles(self, kind: SubjectKind) -> bool:
        return kind == SubjectKind.BANK

    async def screen(self, subject: BankSubject):
        if not self._key:
            raise ProviderUnavailable("HYPERVERGE_API_KEY not set")
        try:
            data, latency = await request_json(
                "POST", self.URL, headers={"x-access-token": self._key},
                json_body={"accountNumber": subject.account_no_masked, "ifscCode": subject.ifsc, "vpa": subject.vpa},
            )
        except HttpError as exc:
            raise ProviderError(str(exc)) from exc
        score = float(data.get("fraudScore", data.get("riskScore", 0)) or 0)
        risk = score / 100.0 if score > 1 else score
        return self._verdict(
            status=ProviderStatus.OK, risk=min(1.0, risk),
            matched_list=str(data.get("category", "")),
            detail=f"HyperVerge fraudScore={score}", raw_ref=str(data.get("requestId", "")), latency_ms=latency,
        )
