"""P2P taint guard tables

Adds the schema for the Binance-P2P taint guard: order records, counterparty
trust state, vendor-call audit, evidence bundles, settlement vouchers, lien
cases and compliance events.

Revision ID: p2pguard0001
Create Date: 2026-09-25
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "p2pguard0001"
down_revision = "platform0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "p2p_orders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("merchant_id", sa.String(64), nullable=False),
        sa.Column("asset", sa.String(16), nullable=False),
        sa.Column("fiat", sa.String(8), nullable=False),
        sa.Column("qty", sa.Float(), nullable=False),
        sa.Column("price_inr", sa.Float(), nullable=False),
        sa.Column("inr_value", sa.Float(), nullable=False),
        sa.Column("buyer_user", sa.String(128), nullable=True),
        sa.Column("buyer_name", sa.String(256), nullable=True),
        sa.Column("buyer_country", sa.String(2), nullable=True),
        sa.Column("phase", sa.String(16), nullable=False),
        sa.Column("verdict", sa.String(8), nullable=False),
        sa.Column("action", sa.String(8), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("hard_rules", sa.JSON(), nullable=True),
        sa.Column("reasons", sa.JSON(), nullable=True),
        sa.Column("degraded", sa.Boolean(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("order_id", name="uq_p2p_orders_order_id"),
    )
    op.create_index("ix_p2p_orders_order_id", "p2p_orders", ["order_id"])
    op.create_index("ix_p2p_orders_merchant_id", "p2p_orders", ["merchant_id"])
    op.create_index("ix_p2p_orders_verdict", "p2p_orders", ["verdict"])
    op.create_index("ix_p2p_orders_merchant_verdict", "p2p_orders", ["merchant_id", "verdict"])
    op.create_index("ix_p2p_orders_decided_at", "p2p_orders", ["decided_at"])

    op.create_table(
        "counterparties",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("buyer_key", sa.String(128), nullable=False),
        sa.Column("binance_user", sa.String(128), nullable=True),
        sa.Column("verified_name", sa.String(256), nullable=True),
        sa.Column("seen", sa.Integer(), nullable=False),
        sa.Column("flagged", sa.Integer(), nullable=False),
        sa.Column("clean_streak", sa.Integer(), nullable=False),
        sa.Column("last_risk", sa.Float(), nullable=True),
        sa.Column("last_verdict", sa.String(8), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    # Unique index, no separate unique constraint — mirrors the ORM, where these
    # columns are declared ``unique=True, index=True``.
    op.create_index("ix_counterparties_buyer_key", "counterparties", ["buyer_key"], unique=True)

    op.create_table(
        "vendor_calls",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("category", sa.String(24), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("risk", sa.Float(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_vendor_calls_order_id", "vendor_calls", ["order_id"])
    op.create_index("ix_vendor_calls_provider", "vendor_calls", ["provider"])
    op.create_index("ix_vendor_calls_order_provider", "vendor_calls", ["order_id", "provider"])

    op.create_table(
        "evidence_bundles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("reference", sa.String(32), nullable=False),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("merchant_id", sa.String(64), nullable=False),
        sa.Column("phase", sa.String(16), nullable=False),
        sa.Column("verdict", sa.String(8), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_evidence_bundles_reference", "evidence_bundles", ["reference"], unique=True)
    op.create_index("ix_evidence_bundles_order_id", "evidence_bundles", ["order_id"])

    op.create_table(
        "settlement_vouchers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("voucher_ref", sa.String(64), nullable=False),
        sa.Column("virtual_account", sa.String(64), nullable=True),
        sa.Column("vpa", sa.String(128), nullable=True),
        sa.Column("utr", sa.String(64), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("pool", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("credited_at", sa.DateTime(), nullable=True),
        sa.Column("sweep_after", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_settlement_vouchers_order_id", "settlement_vouchers", ["order_id"], unique=True)
    op.create_index("ix_settlement_vouchers_voucher_ref", "settlement_vouchers", ["voucher_ref"])
    op.create_index("ix_settlement_vouchers_utr", "settlement_vouchers", ["utr"])
    op.create_index("ix_vouchers_pool_status", "settlement_vouchers", ["pool", "status"])

    op.create_table(
        "lien_cases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("case_ref", sa.String(32), nullable=False),
        sa.Column("order_id", sa.String(64), nullable=True),
        sa.Column("utr", sa.String(64), nullable=True),
        sa.Column("account_no_masked", sa.String(16), nullable=True),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("notice_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("evidence_reference", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_lien_cases_case_ref", "lien_cases", ["case_ref"], unique=True)
    op.create_index("ix_lien_cases_order_id", "lien_cases", ["order_id"])
    op.create_index("ix_lien_cases_utr", "lien_cases", ["utr"])
    op.create_index("ix_lien_cases_status", "lien_cases", ["status"])

    op.create_table(
        "compliance_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_compliance_events_order_id", "compliance_events", ["order_id"])
    op.create_index("ix_compliance_events_event_type", "compliance_events", ["event_type"])


def downgrade() -> None:
    for table in (
        "compliance_events",
        "lien_cases",
        "settlement_vouchers",
        "evidence_bundles",
        "vendor_calls",
        "counterparties",
        "p2p_orders",
    ):
        op.drop_table(table)
