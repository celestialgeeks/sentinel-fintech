"""Core platform tables

Adds the schema Sentinel's risk-intelligence side has always had but never had a
migration for: transactions, screening results, fraud alerts, merchants, user
profiles and the entity graph.

This revision is deliberately the *root* of the chain. ``p2pguard0001`` and
``portal0001`` both assume these tables exist (``portal0001`` adds
``merchants.merchant_key`` to an existing ``merchants`` row set), so until now
``alembic upgrade head`` could only ever succeed against a database that had been
built by ``Base.metadata.create_all`` — a fresh PostgreSQL database could not be
migrated at all.

``merchants`` is created WITHOUT ``merchant_key``: that column belongs to
``portal0001``, which is what introduced the workspace concept.

Revision ID: platform0001
Create Date: 2026-09-26
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op
from src.core.models.enums import (
    AlertStatusEnum,
    KYBStatusEnum,
    KYCStatusEnum,
    MerchantStatusEnum,
    RecommendationEnum,
    SeverityEnum,
    TransactionStatusEnum,
)

revision = "platform0001"
down_revision = None
branch_labels = None
depends_on = None

# Native PostgreSQL enum types, keyed by the ORM class that owns them. Kept here so
# downgrade can drop them too — alembic removes the table, not the type.
_ENUMS = (
    TransactionStatusEnum,
    RecommendationEnum,
    SeverityEnum,
    AlertStatusEnum,
    MerchantStatusEnum,
    KYBStatusEnum,
    KYCStatusEnum,
)


def upgrade() -> None:
    # ─── transactions ────────────────────────────────────────────────────────
    op.create_table(
        "transactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("transaction_id", sa.String(64), nullable=False),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("sender_id", sa.String(128), nullable=True),
        sa.Column("sender_name", sa.String(256), nullable=True),
        sa.Column("sender_country", sa.String(2), nullable=True),
        sa.Column("receiver_id", sa.String(128), nullable=True),
        sa.Column("receiver_name", sa.String(256), nullable=True),
        sa.Column("receiver_country", sa.String(2), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("device_fingerprint", sa.String(256), nullable=True),
        sa.Column("status", sa.Enum(TransactionStatusEnum), server_default="PENDING", nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_transactions_transaction_id", "transactions", ["transaction_id"], unique=True)
    op.create_index("ix_transactions_sender_id", "transactions", ["sender_id"])
    op.create_index("ix_transactions_receiver_id", "transactions", ["receiver_id"])
    op.create_index("ix_txns_sender_country", "transactions", ["sender_country"])
    op.create_index("ix_txns_receiver_country", "transactions", ["receiver_country"])
    op.create_index("ix_txns_status_risk", "transactions", ["status", "risk_score"])
    op.create_index("ix_txns_created_at", "transactions", ["created_at"])

    # ─── screening_results (child of transactions) ───────────────────────────
    op.create_table(
        "screening_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("transaction_id", sa.BigInteger(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("flags", sa.JSON(), nullable=True),
        sa.Column("matched_entities", sa.JSON(), nullable=True),
        sa.Column("recommendation", sa.Enum(RecommendationEnum), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], name="fk_screening_results_transaction_id", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_screening_results_transaction_id", "screening_results", ["transaction_id"])
    op.create_index("ix_screening_txn_id", "screening_results", ["transaction_id"])
    op.create_index("ix_screening_recommendation", "screening_results", ["recommendation"])
    op.create_index("ix_screening_created_at", "screening_results", ["created_at"])

    # ─── fraud_alerts (optional child of transactions) ───────────────────────
    op.create_table(
        "fraud_alerts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("transaction_id", sa.BigInteger(), nullable=True),
        sa.Column("alert_type", sa.String(128), nullable=False),
        sa.Column("severity", sa.Enum(SeverityEnum), nullable=False),
        sa.Column("status", sa.Enum(AlertStatusEnum), server_default="OPEN", nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("triage_recommendation", sa.String(256), nullable=True),
        sa.Column("agent_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["transactions.id"], name="fk_fraud_alerts_transaction_id", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_fraud_alerts_transaction_id", "fraud_alerts", ["transaction_id"])
    op.create_index("ix_alerts_transaction_id", "fraud_alerts", ["transaction_id"])
    op.create_index("ix_fraud_alerts_alert_type", "fraud_alerts", ["alert_type"])
    op.create_index("ix_fraud_alerts_status", "fraud_alerts", ["status"])
    op.create_index("ix_alerts_severity_status", "fraud_alerts", ["severity", "status"])
    op.create_index("ix_alerts_created_at", "fraud_alerts", ["created_at"])

    # ─── merchants ───────────────────────────────────────────────────────────
    # No merchant_key here: portal0001 owns that column and its unique index.
    op.create_table(
        "merchants",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("business_name", sa.String(256), nullable=False),
        sa.Column("registration_number", sa.String(64), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("industry", sa.String(128), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("status", sa.Enum(MerchantStatusEnum), server_default="PENDING", nullable=False),
        sa.Column("kyb_status", sa.Enum(KYBStatusEnum), server_default="NOT_STARTED", nullable=False),
        sa.Column("kyc_status", sa.Enum(KYCStatusEnum), server_default="NOT_STARTED", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("registration_number", name="uq_merchants_reg_number"),
    )
    op.create_index("ix_merchants_registration_number", "merchants", ["registration_number"])
    op.create_index("ix_merchants_status", "merchants", ["status"])
    op.create_index("ix_merchants_country", "merchants", ["country"])
    op.create_index("ix_merchants_created_at", "merchants", ["created_at"])

    # ─── user_profiles ───────────────────────────────────────────────────────
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("name", sa.String(256), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("device_fingerprint", sa.String(256), nullable=True),
        sa.Column("typical_amount_min", sa.Float(), nullable=True),
        sa.Column("typical_amount_max", sa.Float(), nullable=True),
        sa.Column("typical_countries", sa.JSON(), nullable=True),
        sa.Column("profile_updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=True)
    op.create_index("ix_profiles_device_fp", "user_profiles", ["device_fingerprint"])

    # ─── entity_graph ────────────────────────────────────────────────────────
    op.create_table(
        "entity_graph",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("source_entity_id", sa.String(128), nullable=False),
        sa.Column("target_entity_id", sa.String(128), nullable=False),
        sa.Column("relationship_type", sa.String(128), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_entity_graph_source_entity_id", "entity_graph", ["source_entity_id"])
    op.create_index("ix_entity_graph_target_entity_id", "entity_graph", ["target_entity_id"])
    op.create_index("ix_entity_graph_relationship_type", "entity_graph", ["relationship_type"])
    op.create_index(
        "ix_entity_graph_unique", "entity_graph", ["source_entity_id", "target_entity_id", "relationship_type"],
        unique=True,
    )
    op.create_index("ix_entity_graph_source", "entity_graph", ["source_entity_id", "relationship_type"])
    op.create_index("ix_entity_graph_target", "entity_graph", ["target_entity_id", "relationship_type"])


def downgrade() -> None:
    for table in ("entity_graph", "user_profiles", "merchants", "fraud_alerts", "screening_results", "transactions"):
        op.drop_table(table)
    for enum_cls in _ENUMS:
        # The type is schema-level, so dropping the tables leaves it behind.
        op.execute(f"DROP TYPE IF EXISTS {enum_cls.__name__.lower()}")
