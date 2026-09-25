# ruff: noqa: E501
"""Deterministic mock providers.

These let the entire guard run (and be unit/integration tested) before any
commercial contract exists. They trigger off simple, documented sentinels so
tests can provoke each risk path:

* wallet  : address containing ``bad``   -> high exposure; ``mixer`` -> medium
* mule    : vpa/account containing ``fraud`` or ending ``9999`` -> mule
* name    : payer_name_on_account != buyer.verified_name -> name mismatch
* trust   : buyer verified name starting ``BLOCKED_`` -> previously flagged
"""

from __future__ import annotations

from src.screening.schemas import ProviderCategory
from src.vendors.base import (
    BankSubject,
    ScreeningProvider,
    SubjectKind,
)


def _norm(name: str) -> str:
    return " ".join(name.lower().replace(".", " ").split()).strip()


class MockWalletProvider(ScreeningProvider):
    name = "mock_wallet"
    category = ProviderCategory.WALLET
    weight = 1.0
    required = True
    fail_closed = True
    cache_ttl = 600
    tier = 0

    def handles(self, kind: SubjectKind) -> bool:
        return kind == SubjectKind.ADDRESS

    async def screen(self, subject):
        addr = getattr(subject, "address", "").lower()
        if "bad" in addr:
            return self._verdict(risk=0.95, matched_list="sanctions", detail="Address linked to sanctioned/threat actor")
        if "mixer" in addr or "tornado" in addr:
            return self._verdict(risk=0.6, matched_list="mixer", detail="Mixer / tornado-cash exposure")
        if "darknet" in addr:
            return self._verdict(risk=0.7, matched_list="darknet", detail="Darkmarket exposure")
        return self._verdict(risk=0.05, detail="No adverse on-chain history")


class MockMuleProvider(ScreeningProvider):
    name = "mock_mule"
    category = ProviderCategory.MULE
    weight = 1.0
    required = True
    fail_closed = True
    cache_ttl = 600
    tier = 0

    def handles(self, kind: SubjectKind) -> bool:
        return kind == SubjectKind.BANK

    async def screen(self, subject: BankSubject):
        vpa = (subject.vpa or "").lower()
        acct = subject.account_no_masked or ""
        if "fraud" in vpa or acct.endswith("9999"):
            return self._verdict(risk=0.98, matched_list="mule_db", detail="Payer account present in mule/complaint database")
        if acct.endswith("0000"):
            return self._verdict(risk=0.5, matched_list="mule_watch", detail="Newly-opened account, no history")
        return self._verdict(risk=0.05, detail="Account not flagged")


class MockNameMatchProvider(ScreeningProvider):
    """Compares the beneficiary name on the bank credit to the Binance-verified name.

    Third-party payment is the single strongest freeze signal for a P2P
    merchant (Binance's own appeal rule suspends such trades), so this is
    weighted heavily and can hard-block.
    """

    name = "mock_name_match"
    category = ProviderCategory.NAME_MATCH
    weight = 1.0
    required = False
    fail_closed = False
    cache_ttl = 0
    tier = 0

    def handles(self, kind: SubjectKind) -> bool:
        return kind == SubjectKind.BANK

    async def screen(self, subject: BankSubject):
        payer = _norm(subject.payer_name or "")
        ben = _norm(subject.beneficiary_name or "")
        if not payer or not ben:
            return self._verdict(risk=0.3, detail="Insufficient names to reconcile")
        if payer == ben:
            return self._verdict(risk=0.0, detail="Payer name matches beneficiary (same-person payment)")
        # token overlap to tolerate middle-name / ordering variance
        pt, bt = set(payer.split()), set(ben.split())
        overlap = len(pt & bt) / max(1, min(len(pt), len(bt)))
        if overlap >= 0.5:
            return self._verdict(risk=0.35, detail="Partial name match (possible alias/typo)")
        return self._verdict(risk=0.9, matched_list="third_party", detail="Payer name does not match beneficiary — third-party payment")
