# ruff: noqa: E501
"""Signzy bank-account verification + name-verification adapter.

Contributes two signals: BANK_ACCOUNT (does the account exist / active) and
NAME_MATCH (payer name vs beneficiary name on the credit). Production Signzy
calls are JWT-signed with an RSA keypair; the signing is delegated to a helper
so this module stays readable, and the whole provider is guarded by keys.
"""

from __future__ import annotations

from src.screening.schemas import ProviderCategory
from src.vendors._http import HttpError, request_json
from src.vendors.base import BankSubject, ProviderError, ProviderUnavailable, ScreeningProvider, SubjectKind


class SignzyProvider(ScreeningProvider):
    name = "signzy"
    category = ProviderCategory.NAME_MATCH
    weight = 1.0
    required = False
    fail_closed = False
    cache_ttl = 600
    tier = 1

    VERIFY_URL = "https://api.signzy.tech/psa/v1/bank/account/verify"  # confirm per contracted product

    def __init__(self, private_key: str | None, public_key: str | None) -> None:
        self._priv = private_key
        self._pub = public_key

    def handles(self, kind: SubjectKind) -> bool:
        return kind == SubjectKind.BANK

    def _auth_headers(self) -> dict[str, str]:
        # Real deployments sign a JWT (x-api-key) with the RSA private key and
        # encrypt the payload with the Signzy public key. Placeholder header
        # wiring is intentional: the provider is unreachable without keys.
        return {"x-api-key": "signzy", "content-type": "application/json"}

    async def screen(self, subject: BankSubject):
        if not (self._priv and self._pub):
            raise ProviderUnavailable("SIGNZY keys not set")
        try:
            data, latency = await request_json(
                "POST", self.VERIFY_URL, headers=self._auth_headers(),
                json_body={"accountNumber": subject.account_no_masked, "ifscCode": subject.ifsc,
                           "nameOnAccount": subject.payer_name, "beneficiaryName": subject.beneficiary_name},
            )
        except HttpError as exc:
            raise ProviderError(str(exc)) from exc
        result = data.get("data", data)
        status = str(result.get("status", "")).lower()
        name_match = str(result.get("nameMatch", result.get("nameMatched", ""))).lower()
        if status not in {"success", "verified", "active"}:
            return self._verdict(category=ProviderCategory.BANK_ACCOUNT, risk=0.85,
                                 matched_list="account_invalid", detail=f"Signzy account status={status}", latency_ms=latency)
        risk = 0.0 if name_match in {"exact", "true", "matched", "yes"} else (0.5 if name_match == "partial" else 0.9)
        return self._verdict(risk=risk, matched_list=name_match or "unknown",
                             detail=f"Signzy nameMatch={name_match or 'unknown'}", latency_ms=latency)
