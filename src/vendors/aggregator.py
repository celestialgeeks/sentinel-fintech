# ruff: noqa: E501
"""Vendor registry + resilient fan-out.

``build_registry`` assembles providers from configuration: a commercial adapter
is used when its key is present, otherwise a deterministic mock stands in (so
dev/CI exercise the real code paths). ``LocalListSanctionsProvider`` is always
included because it needs no key.

``VendorAggregator.screen`` fans subjects out to the providers that handle them,
applying caching, retries, per-provider circuit breakers, a latency budget,
tiered cost control, and per-provider fail policy (never a silent ALLOW when a
required provider is down). The result is a single CounterpartyScreening.
"""

from __future__ import annotations

import asyncio
import logging

from src.gateway.schemas import GuardPhase, P2POrder
from src.screening.schemas import (
    CounterpartyScreening,
    ProviderCategory,
    ProviderStatus,
    ProviderVerdict,
)
from src.vendors.account_aggregator import AccountAggregatorProvider
from src.vendors.base import (
    AddressSubject,
    BankSubject,
    NameSubject,
    ProviderError,
    ProviderUnavailable,
    ScreeningProvider,
    SubjectKind,
)
from src.vendors.chainalysis import ChainalysisProvider
from src.vendors.config import VendorSettings, get_vendor_settings
from src.vendors.cryptoauthet import CryptoAuthetProvider
from src.vendors.elliptic import EllipticProvider
from src.vendors.hyperverge import HyperVergeProvider
from src.vendors.idfy import IDfyProvider
from src.vendors.mock import (
    MockMuleProvider,
    MockNameMatchProvider,
    MockWalletProvider,
)
from src.vendors.resilience import CircuitBreaker, CircuitOpen, cached_json, with_retry
from src.vendors.sanctions import LocalListSanctionsProvider, RemoteSanctionsProvider
from src.vendors.signzy import SignzyProvider

logger = logging.getLogger(__name__)

# Categories whose >=0.9 hit is treated as a hard block at the fusion layer.
_HARD_BLOCK_CATEGORIES = {ProviderCategory.SANCTIONS, ProviderCategory.MULE, ProviderCategory.WALLET}


def build_registry(settings: VendorSettings | None = None) -> list[ScreeningProvider]:
    """Return the configured provider set (commercial where keyed, else mock)."""
    s = settings or get_vendor_settings()
    mocks = s.use_mocks_when_unconfigured
    providers: list[ScreeningProvider] = []

    # Always-on, key-free sanctions from the local watchlist.
    providers.append(LocalListSanctionsProvider())

    # On-chain wallet screening
    wallet: list[ScreeningProvider] = []
    if s.chainalysis_api_key:
        wallet.append(ChainalysisProvider(s.chainalysis_api_key))
    if s.cryptoauthet_api_key:
        wallet.append(CryptoAuthetProvider(s.cryptoauthet_api_key, s.cryptoauthet_base_url))
    if s.elliptic_api_key:
        wallet.append(EllipticProvider(s.elliptic_api_key))
    if not wallet and mocks:
        wallet.append(MockWalletProvider())
    providers.extend(wallet)

    # India mule / bank / name
    bank: list[ScreeningProvider] = []
    if s.idfy_client_id and s.idfy_client_secret:
        bank.append(IDfyProvider(s.idfy_client_id, s.idfy_client_secret))
    if s.hyperverge_api_key:
        bank.append(HyperVergeProvider(s.hyperverge_api_key))
    if s.signzy_private_key and s.signzy_public_key:
        bank.append(SignzyProvider(s.signzy_private_key, s.signzy_public_key))
    if s.aa_client_id and s.aa_client_secret:
        bank.append(AccountAggregatorProvider(s.aa_client_id, s.aa_client_secret))
    if not any(p.category == ProviderCategory.MULE for p in bank) and mocks:
        bank.append(MockMuleProvider())
    if not any(p.category == ProviderCategory.NAME_MATCH for p in bank) and mocks:
        bank.append(MockNameMatchProvider())
    providers.extend(bank)

    # Commercial sanctions feed (in addition to the local list)
    if s.sanctions_feed_url and s.sanctions_api_key:
        providers.append(RemoteSanctionsProvider(s.sanctions_feed_url, s.sanctions_api_key))

    return providers


def _subjects_for(order: P2POrder, phase: GuardPhase) -> dict[SubjectKind, list]:
    subjects: dict[SubjectKind, list] = {SubjectKind.NAME: [], SubjectKind.ADDRESS: [], SubjectKind.BANK: []}

    subjects[SubjectKind.NAME].append(NameSubject(name=order.buyer.verified_name, country=order.buyer.country))

    if order.wallet:
        if order.wallet.withdrawal_address:
            subjects[SubjectKind.ADDRESS].append(
                AddressSubject(chain=order.wallet.chain, address=order.wallet.withdrawal_address, role="buyer_withdrawal")
            )
        if order.wallet.deposit_address:
            subjects[SubjectKind.ADDRESS].append(
                AddressSubject(chain=order.wallet.chain, address=order.wallet.deposit_address, role="merchant_deposit")
            )

    # Bank/credit signals only exist once we can see the actual INR credit.
    if order.payment is not None:
        subjects[SubjectKind.BANK].append(
            BankSubject(
                payer_name=order.payment.payer_name_on_account,
                beneficiary_name=order.buyer.verified_name,
                account_no_masked=order.payment.account_no_masked,
                ifsc=order.payment.ifsc,
                vpa=order.payment.vpa,
                amount=order.payment.amount,
            )
        )
    return subjects


def _max_tier(phase: GuardPhase, inr_value: float) -> int:
    """Tiered cost control: escalate to pricier providers for larger/real deals."""
    if phase == GuardPhase.PRE_SCREEN:
        return 0
    if inr_value >= 200_000:
        return 2
    if inr_value >= 50_000:
        return 1
    return 1  # release gate always runs at least tier 1


class VendorAggregator:
    def __init__(self, providers: list[ScreeningProvider], settings: VendorSettings | None = None) -> None:
        self._providers = providers
        self._settings = settings or get_vendor_settings()
        self._breakers: dict[str, CircuitBreaker] = {}

    def _breaker(self, name: str) -> CircuitBreaker:
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker()
        return self._breakers[name]

    def _cache_key(self, provider: ScreeningProvider, subject) -> str:
        ident = getattr(subject, "address", None) or getattr(subject, "name", None) or getattr(subject, "key", lambda: "")()
        return f"vendor:{provider.name}:{subject.kind.value}:{ident}"

    async def _screen_one(self, provider: ScreeningProvider, subject) -> ProviderVerdict:
        breaker = self._breaker(provider.name)
        timeout = self._settings.max_vendor_latency_ms / 1000.0

        async def _call() -> dict:
            verdict = await asyncio.wait_for(breaker.call(lambda: provider.screen(subject)), timeout=timeout)
            return verdict.model_dump(mode="json")

        try:
            async def _load() -> dict:
                return await with_retry(_call, attempts=2, retry_on=(ProviderError, CircuitOpen, asyncio.TimeoutError))

            data = await cached_json(self._cache_key(provider, subject), _load, provider.cache_ttl)
            return ProviderVerdict.model_validate(data)
        except ProviderUnavailable as exc:
            logger.info("Provider %s unavailable: %s", provider.name, exc)
            return self._degraded_verdict(provider, ProviderStatus.UNAVAILABLE, str(exc))
        except Exception as exc:  # noqa: BLE001 - any provider failure funnels here
            logger.warning("Provider %s failed: %s", provider.name, exc)
            return self._degraded_verdict(provider, ProviderStatus.ERROR, str(exc))

    def _degraded_verdict(self, provider: ScreeningProvider, status: ProviderStatus, detail: str) -> ProviderVerdict:
        # Fail-closed providers contribute maximal uncertainty; the fusion layer
        # reads `degraded` and refuses to ALLOW. Non-fail-closed contribute 0.
        risk = provider.weight if provider.fail_closed and provider.required else 0.0
        return ProviderVerdict(
            provider=provider.name, category=provider.category, status=status,
            risk=min(1.0, risk), detail=f"degraded: {detail}",
        )

    async def screen(self, order: P2POrder, phase: GuardPhase) -> CounterpartyScreening:
        subjects = _subjects_for(order, phase)
        max_tier = _max_tier(phase, order.price_inr * order.qty)
        tasks: list[asyncio.Task] = []

        for provider in self._providers:
            if provider.tier > max_tier:
                continue
            for kind, items in subjects.items():
                if not items or not provider.handles(kind):
                    continue
                for subject in items:
                    tasks.append(asyncio.create_task(self._screen_one(provider, subject)))

        verdicts: list[ProviderVerdict] = list(await asyncio.gather(*tasks)) if tasks else []

        ok = [v for v in verdicts if v.status == ProviderStatus.OK]
        degraded = any(v.status in {ProviderStatus.ERROR, ProviderStatus.UNAVAILABLE} and v.risk > 0 for v in verdicts)
        max_risk = max((v.risk for v in ok), default=0.0)
        hard_block = any(
            v.status == ProviderStatus.OK and v.risk >= 0.9 and v.category in _HARD_BLOCK_CATEGORIES
            for v in verdicts
        )
        return CounterpartyScreening(
            order_id=order.order_id, verdicts=verdicts, max_risk=max_risk,
            hard_block=hard_block, degraded=degraded,
        )


# Module-level default aggregator (lazy registry built on first use)
_aggregator: VendorAggregator | None = None


def get_aggregator() -> VendorAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = VendorAggregator(build_registry())
    return _aggregator
