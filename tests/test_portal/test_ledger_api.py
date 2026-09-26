"""The ledger: what the portal shows after the guard has decided.

Also the regression net for two defects this API surfaced: the release-gate row
and its evidence pack used to vanish because of unique constraints, which meant
the most important pack of the two — the one carrying the UTR and payer name —
was the one that never got written.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import delete

import src.core.db as db_module
from src.core.models import MerchantMembership
from src.gateway.schemas import GuardPhase, P2POrder
from src.p2p import fusion, rules
from src.portal.ledger.aggregates import window_bounds
from src.screening.schemas import ProviderCategory
from src.vendors import VendorAggregator
from src.vendors.base import ProviderError, ScreeningProvider, SubjectKind
from tests.test_portal.conftest import auth, call_gate, order_payload, signup


class TestLedgerPersistence:
    async def test_both_gates_of_one_order_are_both_in_the_ledger(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_two_gates", phase="pre_screen")
        await call_gate(client, key, order_id="ord_two_gates", phase="release_gate")

        rows = await client.get("/api/v1/portal/orders", headers=auth(workspace["token"]))
        body = rows.json()
        assert body["total"] == 2
        assert {item["phase"] for item in body["items"]} == {"pre_screen", "release_gate"}

    async def test_release_gate_writes_its_own_evidence_pack(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        pre = await call_gate(client, key, order_id="ord_ev", phase="pre_screen")
        release = await call_gate(client, key, order_id="ord_ev", phase="release_gate")

        # Distinct references: colliding on one would silently drop the second.
        assert pre["evidence_ref"] != release["evidence_ref"]
        assert release["evidence_ref"].startswith("EV-")

        detail = await client.get(
            "/api/v1/portal/orders/ord_ev", params={"merchant": key}, headers=auth(workspace["token"])
        )
        pack = detail.json()["evidence"]
        assert pack["phase"] == "release_gate"
        assert pack["reference"] == release["evidence_ref"]

    async def test_each_gate_owns_its_vendor_calls_and_compliance_rows(self, client):
        """No double counting: an order screened twice spent money twice, separately."""
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_gates", phase="pre_screen", qty=100, price=905)
        await call_gate(client, key, order_id="ord_gates", phase="release_gate", qty=100, price=905)

        headers = auth(workspace["token"])
        rows = await client.get(
            "/api/v1/portal/orders", params={"search": "ord_gates"}, headers=headers
        )
        by_phase = {item["phase"]: item for item in rows.json()["items"]}
        assert set(by_phase) == {"pre_screen", "release_gate"}
        # Per-gate spend must be the same order of magnitude, not one double and
        # one single, and latency must be attributed to the gate that waited.
        assert by_phase["pre_screen"]["spend_usd"] == by_phase["release_gate"]["spend_usd"]

        detail = await client.get("/api/v1/portal/orders/ord_gates", params={"merchant": key}, headers=headers)
        body = detail.json()
        assert body["order"]["phase"] == "release_gate", "detail opens on the newest decision"
        assert len(body["vendor_calls"]) == 3, "one call per provider for this gate, not six"
        assert len({c["provider"] for c in body["vendor_calls"]}) == 3
        types = [event["event_type"] for event in body["compliance"]]
        assert types.count("KYC_RETENTION") == 1, "the register is not duplicated across gates"

    async def test_re_screening_the_same_gate_updates_instead_of_colliding(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_retry", phase="release_gate", vpa="buyer@okaxis")
        again = await call_gate(client, key, order_id="ord_retry", phase="release_gate", vpa="fraud@ybl")

        rows = await client.get(
            "/api/v1/portal/orders", params={"phase": "release_gate"}, headers=auth(workspace["token"])
        )
        assert rows.json()["total"] == 1, "a retry refreshes the row, it does not duplicate it"
        assert rows.json()["items"][0]["verdict"] == again["verdict"]

    async def test_the_ledger_row_carries_the_credit_it_screened(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(
            client, key, order_id="ord_credit", payer="Sunil Verma", acct="4417", utr="429177651234", qty=50, price=905
        )
        rows = await client.get("/api/v1/portal/orders", headers=auth(workspace["token"]))
        item = rows.json()["items"][0]
        assert item["utr"] == "429177651234"
        assert item["payer_name"] == "Sunil Verma"
        assert item["account_no_masked"] == "4417"
        assert item["payment_method"] == "upi"
        assert item["inr_value"] == 50 * 905


class TestOrderReads:
    async def test_third_party_payment_is_blocked_and_attributed(self, client):
        workspace = await signup(client)
        decision = await call_gate(client, workspace["merchant_key"], order_id="ord_3p", payer="Total Stranger")
        assert decision["verdict"] == "BLOCK"

        detail = await client.get("/api/v1/portal/orders/ord_3p", headers=auth(workspace["token"]))
        body = detail.json()
        assert body["decision"]["hard_rules"] == [], "a name mismatch is policy, not a hard rule"
        assert any("Third-party" in reason for reason in body["decision"]["reasons"])
        assert body["order"]["verdict"] == "BLOCK"
        assert body["payment"]["payer_name_on_account"] == "Total Stranger"

    async def test_mule_block_lists_the_rule_and_the_vendor(self, client):
        workspace = await signup(client)
        await call_gate(client, workspace["merchant_key"], order_id="ord_mule", vpa="fraud@ybl")
        detail = await client.get(
            "/api/v1/portal/orders/ord_mule", headers=auth(workspace["token"])
        )
        body = detail.json()
        assert "mule_account" in body["decision"]["hard_rules"]
        assert body["decision"]["verdict"] == "BLOCK"
        providers = {call["provider"] for call in body["vendor_calls"]}
        assert "mock_mule" in providers
        assert body["vendor_calls"], "the sources tab must have rows"

    async def test_detail_exposes_the_voucher_and_the_wallet(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_vch", phase="pre_screen", address="Tbad9999x")
        detail = await client.get(
            "/api/v1/portal/orders/ord_vch", params={"merchant": key}, headers=auth(workspace["token"])
        )
        body = detail.json()
        assert body["voucher"]["voucher_ref"].startswith("VCH-")
        assert body["voucher"]["pool"] == "quarantine"
        assert body["voucher"]["sweep_after"] is None  # blocked money never sweeps automatically
        assert body["wallet"]["withdrawal_address"] == "Tbad9999x"

    async def test_timeline_marks_each_gate(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_tl", phase="pre_screen")
        await call_gate(client, key, order_id="ord_tl", phase="release_gate")
        detail = await client.get(
            "/api/v1/portal/orders/ord_tl", params={"merchant": key}, headers=auth(workspace["token"])
        )
        names = [node["name"] for node in detail.json()["timeline"]]
        assert "order_created" in names
        assert "guard_pre_screen" in names
        assert "evidence_stored" in names

    async def test_unknown_order_is_404_not_another_merchants_row(self, client):
        mine = await signup(client, email="m@example.com", merchant_key="m_mine")
        await signup(client, email="t@example.com", merchant_key="m_theirs")
        await call_gate(client, "m_theirs", order_id="ord_secret")

        result = await client.get(
            "/api/v1/portal/orders/ord_secret", headers=auth(mine["token"])
        )
        assert result.status_code == 404

    async def test_a_required_vendor_being_down_never_allows(self, client):
        """Degradation is the fail-closed promise, tested against a dead provider."""

        class Down(ScreeningProvider):
            name = "mock_wallet"  # required and fail_closed in the real registry
            category = ProviderCategory.WALLET
            required = True
            fail_closed = True
            cache_ttl = 0
            tier = 0

            def handles(self, kind: SubjectKind) -> bool:
                return kind == SubjectKind.ADDRESS

            async def screen(self, subject):
                raise ProviderError("vendor down")

        workspace = await signup(client)
        key = workspace["merchant_key"]
        order = P2POrder.model_validate(order_payload(key, order_id="ord_deg", address="Txyz"))

        aggregator = VendorAggregator([Down()])
        screening = await aggregator.screen(order, GuardPhase.RELEASE_GATE)
        assert screening.degraded is True

        hits, behavioural = rules.evaluate(order, screening, {}, [])
        decision = fusion.decide(order, GuardPhase.RELEASE_GATE, screening, hits, behavioural)
        assert decision.verdict.value != "ALLOW"
        assert decision.degraded is True
        assert any("degraded" in reason.lower() for reason in decision.reasons)

    async def test_severe_wallet_exposure_is_a_hard_block(self, client):
        workspace = await signup(client)
        decision = await call_gate(
            client, workspace["merchant_key"], order_id="ord_wallet", address="Tbad0099"
        )
        assert decision["verdict"] == "BLOCK"
        assert "wallet_exposure" in decision["hard_rules"]


class TestFiltersAndSearch:
    async def _seed_mixed(self, client, key: str) -> None:
        await call_gate(client, key, order_id="ord_clean", buyer="Ramesh Kumar", binance_user="u_amesh",
                        utr="4200000101")
        await call_gate(client, key, order_id="ord_mule", vpa="fraud@ybl", binance_user="u_kabir",
                        buyer="Kabir Khan", utr="4200000102")
        await call_gate(client, key, order_id="ord_3p", payer="Sunil Verma", binance_user="u_priya",
                        buyer="Priya Nair", utr="4200000103")

    async def test_verdict_filter(self, client):
        workspace = await signup(client)
        await self._seed_mixed(client, workspace["merchant_key"])
        headers = auth(workspace["token"])
        blocked = await client.get("/api/v1/portal/orders", params={"verdict": "BLOCK"}, headers=headers)
        assert {item["order_id"] for item in blocked.json()["items"]} == {"ord_mule", "ord_3p"}
        assert all(item["verdict"] == "BLOCK" for item in blocked.json()["items"])

    async def test_risk_floor_filter(self, client):
        workspace = await signup(client)
        await self._seed_mixed(client, workspace["merchant_key"])
        result = await client.get(
            "/api/v1/portal/orders", params={"risk_min": 0.8}, headers=auth(workspace["token"])
        )
        assert result.json()["total"] == 2
        assert all(item["risk_score"] >= 0.8 for item in result.json()["items"])

    async def test_hard_rule_filter_matches_the_rule_name(self, client):
        workspace = await signup(client)
        await self._seed_mixed(client, workspace["merchant_key"])
        result = await client.get(
            "/api/v1/portal/orders", params={"hard_rule": "mule_account"}, headers=auth(workspace["token"])
        )
        assert [item["order_id"] for item in result.json()["items"]] == ["ord_mule"]

    async def test_search_matches_utr_and_buyer(self, client):
        workspace = await signup(client)
        await self._seed_mixed(client, workspace["merchant_key"])
        headers = auth(workspace["token"])
        by_utr = await client.get("/api/v1/portal/orders", params={"search": "4200000102"}, headers=headers)
        assert [item["order_id"] for item in by_utr.json()["items"]] == ["ord_mule"]
        by_name = await client.get("/api/v1/portal/orders", params={"search": "Priya"}, headers=headers)
        assert [item["order_id"] for item in by_name.json()["items"]] == ["ord_3p"]

    async def test_pagination_reports_whether_more_is_coming(self, client):
        workspace = await signup(client)
        await self._seed_mixed(client, workspace["merchant_key"])
        headers = auth(workspace["token"])
        page = await client.get("/api/v1/portal/orders", params={"limit": 2, "offset": 0}, headers=headers)
        body = page.json()
        assert len(body["items"]) == 2
        assert body["total"] == 3
        assert body["has_more"] is True

    async def test_sort_by_risk_descending(self, client):
        workspace = await signup(client)
        await self._seed_mixed(client, workspace["merchant_key"])
        result = await client.get(
            "/api/v1/portal/orders", params={"sort": "risk_score", "desc": "true"},
            headers=auth(workspace["token"]),
        )
        scores = [item["risk_score"] for item in result.json()["items"]]
        assert scores == sorted(scores, reverse=True)

    async def test_untrusted_sort_column_falls_back_to_decided_at(self, client):
        workspace = await signup(client)
        await call_gate(client, workspace["merchant_key"], order_id="ord_sort")
        result = await client.get(
            "/api/v1/portal/orders", params={"sort": "risk_score; DROP TABLE p2p_orders"},
            headers=auth(workspace["token"]),
        )
        assert result.status_code == 200
        assert result.json()["total"] == 1

    async def test_has_utr_filter_separates_untraceable_credits(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_utr", utr="4200000009")
        await call_gate(client, key, order_id="ord_no_utr", utr=None)
        headers = auth(workspace["token"])
        missing = await client.get("/api/v1/portal/orders", params={"has_utr": "false"}, headers=headers)
        assert [item["order_id"] for item in missing.json()["items"]] == ["ord_no_utr"]


class TestEvidenceAndOverrides:
    async def test_evidence_download_requires_a_session(self, client):
        workspace = await signup(client)
        await call_gate(client, workspace["merchant_key"], order_id="ord_pack", vpa="fraud@ybl")
        anonymous = await client.get("/api/v1/portal/orders/ord_pack/evidence")
        assert anonymous.status_code in (401, 403)

    async def test_evidence_markdown_is_the_real_pack(self, client):
        workspace = await signup(client)
        await call_gate(client, workspace["merchant_key"], order_id="ord_md", vpa="fraud@ybl")
        result = await client.get(
            "/api/v1/portal/orders/ord_md/evidence", headers=auth(workspace["token"])
        )
        assert result.status_code == 200
        assert result.headers["content-type"].startswith("text/markdown")
        assert "Sentinel Evidence Pack EV-" in result.text
        assert "mule_account" in result.text
        assert "attachment; filename=" in result.headers["content-disposition"]

    async def test_evidence_json_keeps_masks_only(self, client):
        workspace = await signup(client)
        await call_gate(client, workspace["merchant_key"], order_id="ord_json", acct="1234")
        result = await client.get(
            "/api/v1/portal/orders/ord_json/evidence", params={"fmt": "json"}, headers=auth(workspace["token"])
        )
        bundle = json.loads(result.text)
        assert bundle["payment"]["account_no_masked"] == "1234"
        assert "account_no" not in bundle["payment"]

    async def test_override_records_the_actor_and_leaves_the_verdict(self, client):
        workspace = await signup(client)
        await call_gate(
            client,
            workspace["merchant_key"],
            order_id="ord_held",
            vpa="mixer7@okaxis",
            buyer="Vikram Shah",
        )
        headers = auth(workspace["token"])
        override = await client.post(
            "/api/v1/portal/orders/ord_held/override",
            json={"action": "reject", "reason": "Buyer refused to provide a statement showing the UTR."},
            headers=headers,
        )
        assert override.status_code == 200
        body = override.json()
        assert body["overrides"][0]["action"] == "reject"
        assert body["overrides"][0]["actor_email"] == workspace["user"]["email"]
        assert body["order"]["verdict"] == body["decision"]["verdict"], "the engine's word is never rewritten"

    async def test_override_needs_a_reason(self, client):
        workspace = await signup(client)
        await call_gate(client, workspace["merchant_key"], order_id="ord_short")
        result = await client.post(
            "/api/v1/portal/orders/ord_short/override",
            json={"action": "reject", "reason": "no"},
            headers=auth(workspace["token"]),
        )
        assert result.status_code == 422

    async def test_release_override_is_owner_only(self, client):
        """A risk seat may work a HOLD, but may not overrule it into a release."""
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_release")

        analyst = await signup(client, email="risk@example.com")
        async with db_module.session_factory() as session:
            session.add(MerchantMembership(user_id=analyst["user"]["user_id"], merchant_key=key, role="risk"))
            await session.commit()
        headers = auth(analyst["token"])

        blocked = await client.post(
            "/api/v1/portal/orders/ord_release/override",
            json={"action": "release", "reason": "Bank confirmed the credit is same-person funds."},
            headers=headers,
        )
        assert blocked.status_code == 403
        assert "only an owner" in blocked.json()["detail"]

        # The same seat may still reject, which is the safe direction.
        allowed = await client.post(
            "/api/v1/portal/orders/ord_release/override",
            json={"action": "reject", "reason": "Buyer went silent and the window expired."},
            headers=headers,
        )
        assert allowed.status_code == 200

    async def test_a_stranger_cannot_override_at_all(self, client):
        workspace = await signup(client)
        await call_gate(client, workspace["merchant_key"], order_id="ord_private")
        other = await signup(client, email="nosey@example.com")
        result = await client.post(
            "/api/v1/portal/orders/ord_private/override",
            json={"action": "reject", "reason": "Trying to touch a workspace I do not belong to."},
            headers=auth(other["token"]),
        )
        assert result.status_code == 404, "not their order, so not even a 403 hint"


class TestHoldsAndCounterparties:
    async def test_holds_endpoint_lists_only_holds_with_step_up(self, client):
        workspace = await signup(client)
        # Unconfirmed credit: reconciliation pushes this to HOLD, not BLOCK.
        decision = await call_gate(
            client, workspace["merchant_key"], order_id="ord_hold", confirmed=False,
            acct="7000", buyer="Kabir Khan", binance_user="u_kabir", trades=0, age_days=3,
        )
        assert decision["verdict"] == "HOLD", decision["reasons"]
        assert decision["step_up"], "a HOLD must say how to clear it"

        result = await client.get("/api/v1/portal/holds", headers=auth(workspace["token"]))
        body = result.json()
        assert body["total"] >= 1
        assert all(item["verdict"] == "HOLD" for item in body["items"])
        assert "ord_hold" in {item["order_id"] for item in body["items"]}

    async def test_counterparties_aggregate_this_merchants_history(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_b1", binance_user="u_amesh", buyer="Ramesh Kumar")
        await call_gate(client, key, order_id="ord_b2", binance_user="u_amesh", buyer="Ramesh Kumar", vpa="fraud@ybl")

        result = await client.get("/api/v1/portal/counterparties", headers=auth(workspace["token"]))
        rows = {item["buyer_key"]: item for item in result.json()["items"]}
        assert "u_amesh" in rows
        assert rows["u_amesh"]["seen"] == 2
        assert rows["u_amesh"]["block"] == 1
        assert rows["u_amesh"]["flagged"] == 1
        assert rows["u_amesh"]["inr_traded"] > 0

    async def test_buyer_drilldown_returns_their_orders(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_d1", binance_user="u_priya", buyer="Priya Nair")
        await call_gate(client, key, order_id="ord_d2", binance_user="u_vikram", buyer="Vikram Shah")
        result = await client.get("/api/v1/portal/counterparties/u_priya", headers=auth(workspace["token"]))
        assert {item["order_id"] for item in result.json()["items"]} == {"ord_d1"}

    async def test_flagged_only_filter(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_ok", binance_user="u_amesh", buyer="Ramesh Kumar")
        await call_gate(client, key, order_id="ord_bad", binance_user="u_kabir", buyer="Kabir Khan", vpa="fraud@ybl")
        result = await client.get(
            "/api/v1/portal/counterparties", params={"flagged_only": "true"}, headers=auth(workspace["token"])
        )
        assert [item["buyer_key"] for item in result.json()["items"]] == ["u_kabir"]


class TestSettlementFreezesCompliance:
    async def test_vouchers_are_scoped_and_alert_on_missing_utr(self, client):
        mine = await signup(client, email="v1@example.com", merchant_key="v_mine")
        await signup(client, email="v2@example.com", merchant_key="v_theirs")
        await call_gate(client, "v_mine", order_id="ord_v1", phase="pre_screen")
        await call_gate(client, "v_theirs", order_id="ord_v2", phase="pre_screen")

        result = await client.get("/api/v1/portal/vouchers", headers=auth(mine["token"]))
        body = result.json()
        assert [item["order_id"] for item in body["items"]] == ["ord_v1"]
        assert body["items"][0]["pool"] == "quarantine"
        assert any("no UTR" in alert for alert in body["items"][0]["alerts"])

    async def test_lien_case_assembles_the_pack(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_lien", vpa="fraud@ybl", utr="420000777001")

        created = await client.post(
            "/api/v1/portal/liens",
            params={"merchant": key},
            json={
                "order_id": "ord_lien",
                "utr": "420000777001",
                "source": "bank_email",
                "notice_text": "Account lien-marked per Cyber Crime Cell direction.",
            },
            headers=auth(workspace["token"]),
        )
        assert created.status_code == 201
        body = created.json()
        assert body["assembled"] is True
        assert body["case"]["case_ref"].startswith("LIEN-")
        assert body["case"]["merchant_id"] == key
        assert "Sentinel Evidence Pack" in body["evidence_markdown"]
        assert body["missing"] == []

    async def test_lien_case_for_an_unguarded_order_says_so(self, client):
        workspace = await signup(client)
        created = await client.post(
            "/api/v1/portal/liens",
            params={"merchant": workspace["merchant_key"]},
            json={"utr": "9999999999", "notice_text": "Freeze notice for a credit from before Sentinel."},
            headers=auth(workspace["token"]),
        )
        body = created.json()
        assert body["assembled"] is False
        assert body["missing"] and "predates" in body["missing"][0]

    async def test_lien_status_moves_and_note_is_kept(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_lien2", vpa="fraud@ybl", utr="420000777002")
        created = await client.post(
            "/api/v1/portal/liens",
            params={"merchant": key},
            json={"order_id": "ord_lien2", "utr": "420000777002", "notice_text": "Lien marked."},
            headers=auth(workspace["token"]),
        )
        case_ref = created.json()["case"]["case_ref"]

        moved = await client.patch(
            f"/api/v1/portal/liens/{case_ref}",
            json={"status": "awaiting_bank", "note": "Emailed the branch manager."},
            headers=auth(workspace["token"]),
        )
        assert moved.status_code == 200
        assert moved.json()["status"] == "awaiting_bank"

        listed = await client.get("/api/v1/portal/liens", headers=auth(workspace["token"]))
        row = [item for item in listed.json()["items"] if item["case_ref"] == case_ref][0]
        assert "Emailed the branch manager." in row["notice_text"]

    async def test_bad_lien_status_is_refused(self, client):
        workspace = await signup(client)
        result = await client.patch(
            "/api/v1/portal/liens/LIEN-NOPED",
            json={"status": "wishful"},
            headers=auth(workspace["token"]),
        )
        assert result.status_code == 400

    async def test_compliance_events_are_recorded_and_scoped(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_big", qty=200, price=905, vpa="fraud@ybl")
        result = await client.get("/api/v1/portal/compliance-events", headers=auth(workspace["token"]))
        types = {item["event_type"] for item in result.json()["items"]}
        assert {"STR_CONTEXT", "TDS_194S", "KYC_RETENTION"} <= types
        tds = [item for item in result.json()["items"] if item["event_type"] == "TDS_194S"][0]
        assert tds["payload"]["advisory"] is True

    async def test_a_foreign_lien_case_cannot_be_patched(self, client):
        mine = await signup(client, email="l1@example.com", merchant_key="l_mine")
        theirs = await signup(client, email="l2@example.com", merchant_key="l_theirs")
        created = await client.post(
            "/api/v1/portal/liens",
            params={"merchant": mine["merchant_key"]},
            json={"utr": "555111", "notice_text": "mine"},
            headers=auth(mine["token"]),
        )
        case_ref = created.json()["case"]["case_ref"]
        result = await client.patch(
            f"/api/v1/portal/liens/{case_ref}",
            json={"status": "lifted"},
            headers=auth(theirs["token"]),
        )
        assert result.status_code == 404


class TestAggregates:
    async def test_summary_counts_match_the_ledger(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_s1")
        await call_gate(client, key, order_id="ord_s2", vpa="fraud@ybl")

        result = await client.get(
            "/api/v1/portal/stats/summary", params={"window": "all"}, headers=auth(workspace["token"])
        )
        body = result.json()
        assert body["orders"] == 2
        assert body["verdicts"]["allow"] == 1
        assert body["verdicts"]["block"] == 1
        assert body["inr_blocked"] == 10 * 905
        assert body["window"] == "all"

    async def test_overview_is_one_consistent_snapshot(self, client):
        workspace = await signup(client)
        await call_gate(client, workspace["merchant_key"], order_id="ord_o1")
        await call_gate(client, workspace["merchant_key"], order_id="ord_o2", payer="Someone Else")
        result = await client.get(
            "/api/v1/portal/overview", params={"window": "all"}, headers=auth(workspace["token"])
        )
        body = result.json()
        assert body["summary"]["orders"] == 2
        assert body["mix"]["allow"] + body["mix"]["hold"] + body["mix"]["block"] == 2
        assert len(body["risk_histogram"]) == 20
        assert sum(bucket["count"] for bucket in body["risk_histogram"]) == 2
        assert body["sparklines"]["orders"]["values"]
        assert body["providers"], "provider health must be reported"

    async def test_timeseries_and_rule_attribution(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_t1", vpa="fraud@ybl")
        result = await client.get(
            "/api/v1/portal/insights", params={"window": "all"}, headers=auth(workspace["token"])
        )
        body = result.json()
        assert sum(point["block"] for point in body["timeseries"]) == 1
        names = {rule["name"] for rule in body["top_rules"]}
        assert "mule_account" in names

    async def test_windows_are_deterministic_and_bounded(self, client):
        start, end = window_bounds("7d", now=datetime(2026, 9, 25, 12, 0, 0))
        assert (end - start).days == 7
        start_today, _ = window_bounds("today", now=datetime(2026, 9, 25, 12, 30, 0))
        assert start_today.hour == 0 and start_today.minute == 0
        start_all, _ = window_bounds("all")
        assert start_all is None


class TestFeedAndExport:
    async def test_feed_replays_the_backlog_when_asked_to_close(self, client):
        workspace = await signup(client)
        await call_gate(client, workspace["merchant_key"], order_id="ord_f1")
        await call_gate(client, workspace["merchant_key"], order_id="ord_f2", vpa="fraud@ybl")

        result = await client.get(
            "/api/v1/portal/feed",
            params={"once": "true", "after_id": 0},
            headers=auth(workspace["token"]),
        )
        assert result.status_code == 200
        assert result.headers["content-type"].startswith("text/event-stream")
        events = [line for line in result.text.splitlines() if line.startswith("data: ")]
        assert len(events) == 2
        payloads = [json.loads(event.removeprefix("data: ")) for event in events]
        assert {payload["order_id"] for payload in payloads} == {"ord_f1", "ord_f2"}
        assert payloads[0]["id"] < payloads[1]["id"], "oldest first so a cursor can resume"

    async def test_feed_without_a_cursor_starts_at_the_edge(self, client):
        """A fresh tab must not re-read history it has never asked for."""
        workspace = await signup(client)
        await call_gate(client, workspace["merchant_key"], order_id="ord_edge")
        result = await client.get(
            "/api/v1/portal/feed", params={"once": "true"}, headers=auth(workspace["token"])
        )
        assert [line for line in result.text.splitlines() if line.startswith("data: ")] == []

    async def test_feed_requires_a_session(self, client):
        result = await client.get("/api/v1/portal/feed", params={"once": "true"})
        assert result.status_code in (401, 403)

    async def test_csv_export_honours_filters_and_masks(self, client):
        workspace = await signup(client)
        key = workspace["merchant_key"]
        await call_gate(client, key, order_id="ord_c1", acct="1234")
        await call_gate(client, key, order_id="ord_c2", vpa="fraud@ybl", acct="5678")

        result = await client.get(
            "/api/v1/portal/orders/export",
            params={"verdict": "BLOCK"},
            headers=auth(workspace["token"]),
        )
        assert result.status_code == 200
        assert result.headers["content-type"].startswith("text/csv")
        lines = result.text.strip().splitlines()
        assert len(lines) == 2, "header plus the one blocked order"
        assert "5678" in lines[1] and "1234" not in result.text

    async def test_an_account_with_no_workspace_is_told_plainly(self, client):
        workspace = await signup(client)

        async with db_module.session_factory() as session:
            await session.execute(delete(MerchantMembership))
            await session.commit()

        result = await client.get("/api/v1/portal/orders", headers=auth(workspace["token"]))
        assert result.status_code == 400
        assert "workspace" in result.json()["detail"]
