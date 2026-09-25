# ruff: noqa: N818, UP042, PLR0913
"""Screening-provider abstraction for the P2P taint guard.

Every vendor (on-chain analytics, Indian mule/bank/name checks, sanctions
feeds) implements :class:`ScreeningProvider` and returns a uniform
:class:`~src.screening.schemas.ProviderVerdict`. Keeping the surface tiny lets
the aggregator fan out to many vendors, apply per-provider fail policies, and
swap a mock for a commercial adapter without touching the decision logic.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum

from src.screening.schemas import ProviderCategory, ProviderStatus, ProviderVerdict


class ProviderError(Exception):
    """Raised by an adapter when a live call fails (network / non-2xx / parse)."""


class ProviderUnavailable(Exception):
    """Raised when a provider is not configured (missing API key / base url)."""


class SubjectKind(str, Enum):
    ADDRESS = "address"
    BANK = "bank"
    NAME = "name"


@dataclass(frozen=True)
class AddressSubject:
    """An on-chain address to screen for exposure."""
    chain: str
    address: str
    role: str = "counterparty"  # "merchant_deposit" | "buyer_withdrawal" | "counterparty"

    kind: SubjectKind = field(default=SubjectKind.ADDRESS, init=False)


@dataclass(frozen=True)
class BankSubject:
    """A payer bank account / VPA + the beneficiary name to reconcile against."""
    payer_name: str | None = None
    beneficiary_name: str | None = None
    account_no_masked: str | None = None
    ifsc: str | None = None
    vpa: str | None = None
    amount: float | None = None

    kind: SubjectKind = field(default=SubjectKind.BANK, init=False)

    def key(self) -> str:
        return "|".join(filter(None, [self.account_no_masked, self.ifsc, self.vpa])) or self.payer_name or "anon"


@dataclass(frozen=True)
class NameSubject:
    """A person/organisation name to screen against sanctions / PEP / adverse media."""
    name: str
    country: str = "IN"

    kind: SubjectKind = field(default=SubjectKind.NAME, init=False)


class ScreeningProvider(abc.ABC):
    """Base class implemented by every vendor adapter."""

    #: registry name, e.g. "chainalysis"
    name: str = "provider"
    #: primary risk class this provider contributes
    category: ProviderCategory = ProviderCategory.OTHER
    #: relative weight when fusing this provider's risk into the composite score
    weight: float = 1.0
    #: if True and the call errors, the aggregator must NOT silently allow (fail-closed)
    required: bool = False
    #: if True (and required), an outage escalates the verdict to HOLD
    fail_closed: bool = False
    #: seconds to cache a verdict per subject key (0 = no cache)
    cache_ttl: int = 300
    #: cheap providers run first; expensive ones only when tier >= threshold
    tier: int = 0

    @abc.abstractmethod
    def handles(self, kind: SubjectKind) -> bool:
        """Return True if this provider can screen the given subject kind."""

    @abc.abstractmethod
    async def screen(self, subject: AddressSubject | BankSubject | NameSubject) -> ProviderVerdict:
        """Screen a subject and return a verdict.

        Implementations should raise :class:`ProviderUnavailable` when not
        configured and :class:`ProviderError` on live-call failures so the
        aggregator can apply the provider's fail policy.
        """

    # -- helpers for concrete adapters ----------------------------------------

    def _verdict(
        self,
        *,
        category: ProviderCategory | None = None,
        status: ProviderStatus = ProviderStatus.OK,
        risk: float = 0.0,
        matched_list: str = "",
        detail: str = "",
        evidence_ref: str = "",
        raw_ref: str = "",
        cost_usd: float = 0.0,
        latency_ms: int = 0,
    ) -> ProviderVerdict:
        return ProviderVerdict(
            provider=self.name,
            category=category or self.category,
            status=status,
            risk=max(0.0, min(1.0, risk)),
            matched_list=matched_list,
            detail=detail,
            evidence_ref=evidence_ref,
            raw_ref=raw_ref,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )
