"""Auth, workspace scoping and the connection wizard."""

from __future__ import annotations

from src.portal.security import encode_jwt
from tests.test_portal.conftest import PASSWORD, auth, call_gate, order_payload, signup


class TestSignupAndLogin:
    async def test_signup_creates_account_workspace_and_token(self, client):
        result = await client.post(
            "/api/v1/auth/signup",
            json={"email": "Ramesh@Example.com", "password": PASSWORD, "business_name": "Ramesh Desk"},
        )
        assert result.status_code == 201
        body = result.json()
        assert body["user"]["email"] == "ramesh@example.com"  # normalised, so login is forgiving
        assert body["merchants"][0]["business_name"] == "Ramesh Desk"
        assert body["access_token"].count(".") == 2

        me = await client.get("/api/v1/auth/me", headers=auth(body["access_token"]))
        assert me.status_code == 200
        assert me.json()["merchants"][0]["merchant_key"] == body["merchants"][0]["merchant_key"]

    async def test_email_is_unique_whatever_the_casing(self, client):
        await signup(client, email="dup@example.com")
        second = await client.post(
            "/api/v1/auth/signup", json={"email": "DUP@example.com", "password": PASSWORD}
        )
        assert second.status_code == 409

    async def test_short_password_is_refused(self, client):
        result = await client.post("/api/v1/auth/signup", json={"email": "a@b.co", "password": "short"})
        assert result.status_code == 422

    async def test_login_accepts_the_email_as_typed_at_signup(self, client):
        await signup(client, email="MixedCase@Example.com")
        result = await client.post(
            "/api/v1/auth/login", json={"email": "mixedcase@example.com", "password": PASSWORD}
        )
        assert result.status_code == 200

    async def test_wrong_password_and_unknown_email_share_one_error(self, client):
        await signup(client, email="known@example.com")
        wrong = await client.post(
            "/api/v1/auth/login", json={"email": "known@example.com", "password": "not-the-password-1"}
        )
        unknown = await client.post(
            "/api/v1/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
        )
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json()["detail"] == unknown.json()["detail"]

    async def test_tampered_token_is_rejected(self, client):
        workspace = await signup(client)
        token = workspace["token"]
        header, payload, signature = token.split(".")
        forged = f"{header}.{payload}.{'0' * len(signature)}"
        result = await client.get("/api/v1/auth/me", headers=auth(forged))
        assert result.status_code == 401

    async def test_another_secret_cannot_mint_a_session(self, client):

        await signup(client)
        forged = encode_jwt({"sub": 1, "typ": "sessions"}, "not-the-server-secret")
        result = await client.get("/api/v1/auth/me", headers=auth(forged))
        assert result.status_code == 401


class TestWorkspaceScoping:
    async def test_requests_needing_a_workspace_get_401_without_a_token(self, client):
        result = await client.get("/api/v1/portal/orders")
        assert result.status_code == 401

    async def test_second_workspace_appears_in_the_switcher(self, client):
        workspace = await signup(client)
        created = await client.post(
            "/api/v1/auth/merchants",
            json={"business_name": "Second Bank Account", "merchant_key": "desk_two"},
            headers=auth(workspace["token"]),
        )
        assert created.status_code == 201
        me = await client.get("/api/v1/auth/me", headers=auth(workspace["token"]))
        keys = {merchant["merchant_key"] for merchant in me.json()["merchants"]}
        assert keys == {workspace["merchant_key"], "desk_two"}

    async def test_a_taken_merchant_key_is_refused_at_signup(self, client):
        await signup(client, email="first@example.com", merchant_key="shared_key")
        second = await client.post(
            "/api/v1/auth/signup",
            json={"email": "second@example.com", "password": PASSWORD, "merchant_key": "shared_key"},
        )
        assert second.status_code == 409
        assert "shared_key" in second.json()["detail"]

        # The rejected signup must not leave a half-created account behind.
        login = await client.post(
            "/api/v1/auth/login", json={"email": "second@example.com", "password": PASSWORD}
        )
        assert login.status_code == 401

    async def test_a_taken_merchant_key_is_refused_when_adding_a_workspace(self, client):
        await signup(client, email="first@example.com", merchant_key="shared_key")
        other = await signup(client, email="second@example.com")
        clash = await client.post(
            "/api/v1/auth/merchants",
            json={"business_name": "Copycat", "merchant_key": "shared_key"},
            headers=auth(other["token"]),
        )
        assert clash.status_code == 409

    async def test_cannot_read_another_merchants_workspace(self, client):
        mine = await signup(client, email="mine@example.com", merchant_key="m_mine")
        theirs = await signup(client, email="theirs@example.com", merchant_key="m_theirs")

        denied = await client.get("/api/v1/portal/orders", params={"merchant": theirs["merchant_key"]},
                                  headers=auth(mine["token"]))
        assert denied.status_code == 403

    async def test_my_reads_only_return_my_rows(self, client):
        mine = await signup(client, email="a@example.com", merchant_key="m_a")
        await signup(client, email="b@example.com", merchant_key="m_b")
        await call_gate(client, "m_a", order_id="ord_a1")
        await call_gate(client, "m_b", order_id="ord_b1")

        rows = await client.get("/api/v1/portal/orders", headers=auth(mine["token"]))
        assert [item["order_id"] for item in rows.json()["items"]] == ["ord_a1"]


class TestIntegrationWizard:
    async def test_status_before_any_order_says_not_connected(self, client):
        workspace = await signup(client)
        result = await client.get("/api/v1/integration/status", headers=auth(workspace["token"]))
        assert result.status_code == 200
        body = result.json()
        assert body["connected"] is False
        assert body["orders_total"] == 0
        assert "pre-screen" in str(body["endpoints"])
        assert "hmac_sha256" in body["signature_help"]

    async def test_key_secret_is_returned_once_and_never_again(self, client):
        workspace = await signup(client)
        headers = auth(workspace["token"])
        created = await client.post(
            "/api/v1/integration/keys", params={"merchant": workspace["merchant_key"]},
            json={"name": "prod bot"}, headers=headers,
        )
        assert created.status_code == 201
        secret = created.json()["hmac_secret"]
        assert len(secret) == 64

        listed = await client.get(
            "/api/v1/integration/keys", params={"merchant": workspace["merchant_key"]}, headers=headers
        )
        row = listed.json()[0]
        assert row["key_prefix"] == created.json()["key_prefix"]
        assert "hmac_secret" not in row
        assert secret not in str(listed.json())

    async def test_revoking_a_key_keeps_the_row_and_marks_it_inactive(self, client):
        workspace = await signup(client)
        headers = auth(workspace["token"])
        created = await client.post(
            "/api/v1/integration/keys", params={"merchant": workspace["merchant_key"]},
            json={"name": "old bot"}, headers=headers,
        )
        key_id = created.json()["id"]
        revoked = await client.delete(f"/api/v1/integration/keys/{key_id}", headers=headers)
        assert revoked.status_code == 200
        assert revoked.json()["active"] is False
        assert revoked.json()["revoked_at"] is not None

    async def test_sandbox_test_runs_the_real_pipeline_without_persisting(self, client):
        workspace = await signup(client)

        body = {"order": order_payload(workspace["merchant_key"], order_id="ord_sandbox"), "phase": "release_gate"}
        result = await client.post(
            "/api/v1/integration/test", json=body, headers=auth(workspace["token"])
        )
        assert result.status_code == 200
        decision = result.json()["decision"]
        assert decision["verdict"] in ("ALLOW", "HOLD", "BLOCK")
        assert decision["evidence_ref"].startswith("EV-")
        assert result.json()["persisted"] is False

        ledger = await client.get("/api/v1/portal/orders", headers=auth(workspace["token"]))
        assert ledger.json()["total"] == 0, "a sandbox test must not appear in the ledger"

    async def test_sandbox_test_blocks_a_foreign_merchant_id(self, client):
        workspace = await signup(client)

        body = {"order": order_payload("someone_elses_desk"), "phase": "pre_screen"}
        result = await client.post("/api/v1/integration/test", json=body, headers=auth(workspace["token"]))
        assert result.status_code == 403

    async def test_release_gate_without_payment_mirrors_the_bot_contract(self, client):
        workspace = await signup(client)

        body = {
            "order": order_payload(workspace["merchant_key"], with_payment=False),
            "phase": "release_gate",
        }
        result = await client.post("/api/v1/integration/test", json=body, headers=auth(workspace["token"]))
        assert result.status_code == 400
        assert "order.payment" in result.json()["detail"]

    async def test_status_shows_connected_after_a_live_decision(self, client):
        workspace = await signup(client)

        await call_gate(client, workspace["merchant_key"], order_id="ord_live")
        result = await client.get(
            "/api/v1/integration/status", params={"merchant": workspace["merchant_key"]},
            headers=auth(workspace["token"]),
        )
        body = result.json()
        assert body["connected"] is True
        assert body["orders_total"] == 1
        assert body["last_order_at"]
