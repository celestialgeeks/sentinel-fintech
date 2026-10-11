"""IDfy bank-account / mule-intelligence adapter.

OAuth2 client-credentials then a fraud / bank-account-intelligence check keyed
by masked account + IFSC + VPA. Maps the vendor risk band to a MULE verdict.
Exact endpoint paths should be confirmed against the contracted IDfy product.
"""

from __future__ import annotations

from src.screening.schemas import ProviderCategory, ProviderStatus
from src.vendors._http import HttpError, request_json
from src.vendors.base import BankSubject, ProviderError, ProviderUnavailable, ScreeningProvider, SubjectKind

_BAND = {"low": 0.1, "medium": 0.45, "high": 0.8, "critical": 0.95}


class IDfyProvider(ScreeningProvider):
    name = "idfy"
    category = ProviderCategory.MULE
    weight = 1.0
    required = True
    fail_closed = True
    cache_ttl = 600
    tier = 0

    AUTH_URL = "https://api.idfy.me/api/v2/auth/token"
    CHECK_URL = "https://api.idfy.me/api/v2/fraud/bank-account"  # confirm per contracted product

    def __init__(self, client_id: str | None, client_secret: str | None) -> None:
        self._id = client_id
        self._secret = client_secret

    def handles(self, kind: SubjectKind) -> bool:
        return kind == SubjectKind.BANK

    async def screen(self, subject: BankSubject):
        if not (self._id and self._secret):
            raise ProviderUnavailable("IDFY_CLIENT_ID/SECRET not set")
        try:
            tok, _ = await request_json(
                "POST", self.AUTH_URL,
                json_body={"grant_type": "client_credentials", "client_id": self._id, "client_secret": self._secret},
            )
            data, latency = await request_json(
                "POST", self.CHECK_URL,
                headers={"Authorization": f"Bearer {tok.get('access_token', '')}"},
                json_body={
                    "account_number": subject.account_no_masked,
                    "ifsc": subject.ifsc,
                    "vpa": subject.vpa,
                    "name": subject.payer_name,
                },
            )
        except HttpError as exc:
            raise ProviderError(str(exc)) from exc
        band = str(data.get("risk", data.get("band", ""))).lower()
        is_mule = bool(data.get("is_mule", data.get("mule", False)))
        risk = 0.98 if is_mule else _BAND.get(band, 0.3)
        return self._verdict(
            status=ProviderStatus.OK, risk=risk, matched_list=band or ("mule" if is_mule else "clean"),
            detail=f"IDfy band={band} mule={is_mule}", raw_ref=str(data.get("transaction_id", "")), latency_ms=latency,
        )
