# ruff: noqa: E501, PLR0913, PLR0917, PLC0415
"""Tests for the Sentinel P2P taint guard (mock providers, no live services)."""

from __future__ import annotations

import hashlib
import hmac
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware.hmac_auth import HmacAuthMiddleware
from src.gateway.schemas import (
    BuyerProfile,
    GuardPhase,
    GuardVerdict,
    P2POrder,
    PayerPayment,
    TradeWallet,
)
from src.p2p import compliance, evidence, fusion, rules, settlement
from src.p2p.consumer import process_order_event, reset_dedupe
from src.p2p.pipeline import guard_order
from src.p2p.router import router as p2p_router
from src.p2p.state import guard_state
from src.screening.schemas import CounterpartyScreening, ProviderCategory, ProviderStatus, ProviderVerdict
from src.vendors import VendorAggregator, build_registry
from src.vendors.base import ProviderError, ScreeningProvider, SubjectKind
from src.vendors.resilience import _mem_cache


@pytest.fixture(autouse=True)
def _reset_state():
    guard_state._mem.clear()
    _mem_cache.clear()
    reset_dedupe()
    yield
    guard_state._mem.clear()
    _mem_cache.clear()
    reset_dedupe()


def make_order(payer="Ramesh Kumar", vpa="buyer@okaxis", acct="1234", addr=None, qty=10, price=900):
    return P2POrder(
        order_id="ord_test_1",
        qty=qty,
        price_inr=price,
        buyer=BuyerProfile(binance_user="u_amesh", verified_name="Ramesh Kumar", trade_count=50, account_age_days=400),
        payment=PayerPayment(vpa=vpa, account_no_masked=acct, payer_name_on_account=payer, amount=qty * price, utr="UTR123", confirmed=True),
        wallet=TradeWallet(withdrawal_address=addr) if addr else None,
    )


# ─── fusion unit tests (no vendors) ──────────────────────────────────────────


def _screening(**cat_risk) -> CounterpartyScreening:
    verdicts = [
        ProviderVerdict(provider=f"p_{c.name.lower()}", category=c, status=ProviderStatus.OK, risk=r)
        for c, r in cat_risk.items()
    ]
    hard = any(v.category in {ProviderCategory.SANCTIONS, ProviderCategory.MULE, ProviderCategory.WALLET} and v.risk >= 0.9 for v in verdicts)
    return CounterpartyScreening(order_id="x", verdicts=verdicts, max_risk=max((v.risk for v in verdicts), default=0.0), hard_block=hard)


class TestFusion:
    def _decide(self, order, phase, screening, behavioural=0.0):
        hits, beh = rules.evaluate(order, screening, {"flagged": 0, "clean_streak": 0}, [])
        return fusion.decide(order, phase, screening, hits, max(behavioural, beh))

    def test_clean_allows(self):
        d = self._decide(make_order(), GuardPhase.RELEASE_GATE, _screening(**{ProviderCategory.NAME_MATCH: 0.0}))
        assert d.verdict == GuardVerdict.ALLOW and d.action == "release"

    def test_mule_blocks(self):
        d = self._decide(make_order(), GuardPhase.RELEASE_GATE, _screening(**{ProviderCategory.MULE: 0.98}))
        assert d.verdict == GuardVerdict.BLOCK and "mule_account" in d.hard_rules

    def test_wallet_blocks(self):
        d = self._decide(make_order(addr="Tbadxyz"), GuardPhase.RELEASE_GATE, _screening(**{ProviderCategory.WALLET: 0.95}))
        assert d.verdict == GuardVerdict.BLOCK

    def test_third_party_blocks_at_release(self):
        d = self._decide(make_order(payer="Some Other Guy"), GuardPhase.RELEASE_GATE,
                         _screening(**{ProviderCategory.NAME_MATCH: 0.9}))
        assert d.verdict == GuardVerdict.BLOCK

    def test_degraded_never_allows(self):
        sc = CounterpartyScreening(order_id="x", max_risk=0.0, degraded=True,
                                   verdicts=[ProviderVerdict(provider="p", category=ProviderCategory.MULE, status=ProviderStatus.ERROR, risk=0.9)])
        d = self._decide(make_order(), GuardPhase.RELEASE_GATE, sc)
        assert d.verdict != GuardVerdict.ALLOW and d.degraded is True


# ─── rules ───────────────────────────────────────────────────────────────────


class TestRules:
    def test_velocity_and_structuring(self):
        import time
        now = time.time()
        recent = [(now - 10, 60_000) for _ in range(6)]
        hits, beh = rules.evaluate(make_order(qty=70, price=900), _screening(), {"flagged": 0, "clean_streak": 0}, recent, now)
        assert any(h.name == "velocity" and h.triggered for h in hits)
        assert beh > 0.0

    def test_chat_red_flags(self):
        order = make_order()
        order.buyer.chat_snippet = "please release urgent, my brother paid from different account"
        hits, _ = rules.evaluate(order, _screening(), {}, [], None)
        assert any(h.name == "deal_red_flags" and h.triggered for h in hits)


# ─── pipeline end-to-end with mock providers ─────────────────────────────────


class TestPipeline:
    async def test_release_gate_blocks_mule(self):
        d = await guard_order(make_order(vpa="fraud@xyz", payer="Ramesh Kumar"), GuardPhase.RELEASE_GATE, persist=False, publish=False)
        assert d.verdict == GuardVerdict.BLOCK
        assert d.evidence_ref and d.evidence_ref.startswith("EV-")

    async def test_release_gate_blocks_third_party(self):
        d = await guard_order(make_order(payer="Total Stranger"), GuardPhase.RELEASE_GATE, persist=False, publish=False)
        assert d.verdict == GuardVerdict.BLOCK

    async def test_clean_release_allows(self):
        d = await guard_order(make_order(payer="Ramesh Kumar", vpa="buyer@okaxis", acct="1234"), GuardPhase.RELEASE_GATE, persist=False, publish=False)
        assert d.verdict == GuardVerdict.ALLOW

    async def test_prescreen_issues_voucher(self):
        order = make_order()
        order.payment = None
        d = await guard_order(order, GuardPhase.PRE_SCREEN, persist=False, publish=False)
        assert any("voucher" in r.lower() for r in d.reasons)

    async def test_repeat_flag_tracked(self):
        # first a block, then the same buyer should carry a flagged trust state
        await guard_order(make_order(vpa="fraud@xyz"), GuardPhase.RELEASE_GATE, persist=False, publish=False)
        trust = await guard_state.get_trust("u_amesh")
        assert trust["flagged"] >= 1


class TestAggregatorDegradation:
    async def test_required_provider_outage_degrades(self):
        class Boom(ScreeningProvider):
            name = "boom"
            category = ProviderCategory.MULE
            required = True
            fail_closed = True
            cache_ttl = 0
            tier = 0

            def handles(self, kind):
                return kind == SubjectKind.BANK

            async def screen(self, subject):
                raise ProviderError("vendor down")

        # only the failing provider -> screening is degraded, no clean verdicts
        agg = VendorAggregator([Boom()])
        sc = await agg.screen(make_order(), GuardPhase.RELEASE_GATE)
        assert sc.degraded is True
        hits, beh = rules.evaluate(make_order(), sc, {}, [])
        d = fusion.decide(make_order(), GuardPhase.RELEASE_GATE, sc, hits, beh)
        assert d.verdict != GuardVerdict.ALLOW


# ─── evidence / settlement / compliance ──────────────────────────────────────


class TestEvidenceAndCompliance:
    async def test_evidence_bundle_and_markdown(self):
        order = make_order(vpa="fraud@xyz")
        sc = await VendorAggregator(build_registry()).screen(order, GuardPhase.RELEASE_GATE)
        hits, beh = rules.evaluate(order, sc, {}, [])
        d = fusion.decide(order, GuardPhase.RELEASE_GATE, sc, hits, beh)
        bundle = evidence.build_bundle(order, GuardPhase.RELEASE_GATE, sc, d)
        assert bundle["reference"].startswith("EV-")
        md = evidence.to_markdown(bundle)
        assert "Verdict" in md and "BLOCK" in md

    def test_settlement_reconcile_alerts(self):
        voucher = settlement.build_voucher(make_order(), fusion.GuardDecision(
            order_id="x", phase=GuardPhase.PRE_SCREEN, verdict=GuardVerdict.ALLOW, action="release", risk_score=0.1, confidence=0.9))
        assert voucher["pool"] == "quarantine" and voucher["sweep_after"] is not None
        alerts = settlement.reconcile_credit(voucher, observed_utr=None, observed_pool="operating")
        assert len(alerts) == 2

    def test_compliance_events(self):
        order = make_order(qty=100, price=900)  # INR 90,000 > TDS threshold
        d = fusion.GuardDecision(order_id=order.order_id, phase=GuardPhase.RELEASE_GATE, verdict=GuardVerdict.BLOCK, action="reject", risk_score=0.9, confidence=0.95)
        events = compliance.evaluate_compliance(order, d)
        types = {e["event_type"] for e in events}
        assert {"STR_CONTEXT", "TDS_194S", "KYC_RETENTION"} <= types


# ─── router + HMAC ───────────────────────────────────────────────────────────


def _app():
    app = FastAPI()
    app.include_router(p2p_router, prefix="/api/v1")
    return app


class TestRouter:
    def test_release_gate_endpoint(self):
        client = TestClient(_app())
        body = {"order": make_order(vpa="fraud@xyz").model_dump(mode="json"), "phase": "release_gate"}
        r = client.post("/api/v1/p2p/orders/release-gate", json=body)
        assert r.status_code == 200
        assert r.json()["verdict"] == "BLOCK"

    def test_release_gate_requires_payment(self):
        client = TestClient(_app())
        order = make_order()
        order.payment = None
        body = {"order": order.model_dump(mode="json"), "phase": "release_gate"}
        r = client.post("/api/v1/p2p/orders/release-gate", json=body)
        assert r.status_code == 400

    def test_health(self):
        client = TestClient(_app())
        assert client.get("/api/v1/p2p/health").json()["status"] == "ok"


class TestHmac:
    def test_unsigned_blocked_when_secret_set(self, monkeypatch):
        monkeypatch.setenv("GUARD_HMAC_SECRET", "s3cr3t")
        app = _app()
        app.add_middleware(HmacAuthMiddleware)
        client = TestClient(app)
        body = {"order": make_order().model_dump(mode="json"), "phase": "release_gate"}
        r = client.post("/api/v1/p2p/orders/release-gate", json=body)
        assert r.status_code == 401

    def test_signed_passes(self, monkeypatch):
        secret = "s3cr3t"
        monkeypatch.setenv("GUARD_HMAC_SECRET", secret)
        app = _app()
        app.add_middleware(HmacAuthMiddleware)
        client = TestClient(app)
        payload = {"order": make_order(vpa="buyer@okaxis").model_dump(mode="json"), "phase": "release_gate"}
        import json as _json
        raw = _json.dumps(payload).encode()
        ts = str(int(time.time()))
        sig = hmac.new(secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
        r = client.post(
            "/api/v1/p2p/orders/release-gate",
            content=raw,
            headers={"Content-Type": "application/json", "X-Sentinel-Timestamp": ts, "X-Sentinel-Signature": sig},
        )
        assert r.status_code == 200


# ─── Kafka orchestrator path ─────────────────────────────────────────────────


class TestConsumer:
    async def test_process_order_event_blocks_mule(self):
        msg = make_order(vpa="fraud@xyz").model_dump(mode="json")
        result = await process_order_event(msg, persist=False, publish=False)
        assert result and result["verdict"] == "BLOCK"

    async def test_idempotent_replay(self):
        msg = make_order().model_dump(mode="json")
        first = await process_order_event(msg, persist=False, publish=False)
        second = await process_order_event(msg, persist=False, publish=False)
        assert first is not None and second is None

    async def test_inferred_phase_prescreen(self):
        msg = make_order().model_dump(mode="json")
        msg["payment"] = None
        result = await process_order_event(msg, persist=False, publish=False)
        assert result and result["phase"] == "pre_screen"

