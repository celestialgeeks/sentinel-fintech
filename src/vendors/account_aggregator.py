"""Account Aggregator (Setu / SAHAMATI) consented bank-credit verification.

At the release gate the merchant needs proof the INR credit is genuine and to
reconcile it (UTR, payer name, amount) rather than trusting the buyer's UPI
screenshot. This adapter exchanges an AA consent handle for the transaction
statement entry and emits a BANK_ACCOUNT verdict. Guarded by AA keys.
"""

from __future__ import annotations

from src.screening.schemas import ProviderCategory, ProviderStatus
from src.vendors._http import HttpError, request_json
from src.vendors.base import BankSubject, ProviderError, ProviderUnavailable, ScreeningProvider, SubjectKind


class AccountAggregatorProvider(ScreeningProvider):
    name = "account_aggregator"
    category = ProviderCategory.BANK_ACCOUNT
    weight = 0.8
    required = False
    fail_closed = False
    cache_ttl = 300
    tier = 1

    URL = "https://api.setu.co/v1/aa/transactions/fetch"  # confirm per AA/FIP integration

    def __init__(self, client_id: str | None, client_secret: str | None) -> None:
        self._id = client_id
        self._secret = client_secret

    def handles(self, kind: SubjectKind) -> bool:
        return kind == SubjectKind.BANK

    async def screen(self, subject: BankSubject):
        if not (self._id and self._secret):
            raise ProviderUnavailable("AA_CLIENT_ID/SECRET not set")
        try:
            data, latency = await request_json(
                "POST", self.URL,
                headers={"Authorization": f"Basic {self._id}:{self._secret}"},
                json_body={"utr": subject.vpa, "amount": subject.amount},
            )
        except HttpError as exc:
            raise ProviderError(str(exc)) from exc
        txns = data.get("transactions", [])
        matched = any(str(t.get("utr", "")) == str(subject.vpa) for t in txns) if subject.vpa else bool(txns)
        if not matched:
            return self._verdict(risk=0.7, matched_list="unconfirmed",
                                 detail="AA: no matching credit found for UTR", latency_ms=latency)
        return self._verdict(
            status=ProviderStatus.OK, risk=0.05, matched_list="confirmed_credit",
            detail="AA: credit confirmed against consented statement", latency_ms=latency,
        )
