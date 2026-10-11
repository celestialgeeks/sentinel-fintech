"""Merchant portal: auth, workspaces, keys, overrides + ledger columns

Adds the web-portal tables (portal_users, merchant_memberships, api_keys,
override_notes) and the columns the ledger screens need to filter on:

* ``merchants.merchant_key`` — the stable workspace key a bot sends as
  ``P2POrder.merchant_id``.
* ``p2p_orders`` — the observed credit flattened onto the row (UTR, payer name,
  masked account, method, confirmed), plus ``step_up``, ``behavioural_score`` and
  ``evidence_ref`` so the HOLD worklist and the evidence link need no JSON reads.
* ``lien_cases.merchant_id`` — freeze cases are now scoped to a workspace.
* ``p2p_orders`` — the unique key becomes ``(order_id, phase)``. The old
  ``order_id``-only constraint silently swallowed the *second* gate of every
  order: the pre-screen row blocked the release-gate insert, the shared session
  rolled back, and that gate's evidence bundle was lost with it.

Target dialect is PostgreSQL. A SQLite database (tests, quick local runs) is
built from the models by ``init_db()`` / ``Base.metadata.create_all``, which is
always current; SQLite cannot drop a named UNIQUE constraint through ALTER, so
this migration refuses to run there instead of half-applying.

Revision ID: portal0001
Create Date: 2026-09-26
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "portal0001"
down_revision = "p2pguard0001"
branch_labels = None
depends_on = None


def _dialect() -> str:
    return op.get_context().dialect.name


def _probe(sql: str) -> list[tuple]:
    """Run a catalog SELECT. Alembic resolves this synchronously for us.

    Offline mode (``alembic upgrade --sql``) has no connection to ask, so a failed
    probe reports "nothing exists" — which is the right answer when generating DDL
    for a database that does not exist yet.
    """
    try:
        return [tuple(row) for row in op.get_bind().execute(sa.text(sql)).fetchall()]
    except Exception:  # noqa: BLE001 - offline/permission paths all mean "assume absent"
        return []


def _has_table(name: str) -> bool:
    return bool(_probe(f"SELECT table_name FROM information_schema.tables WHERE table_name = '{name}'"))


def _columns(table: str) -> set[str]:
    return {
        row[0]
        for row in _probe(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'")
    }


def _named_objects(table: str) -> set[str]:
    """Constraint and index names on a table — used to keep this re-runnable."""
    names = {row[0] for row in _probe(f"SELECT conname FROM pg_constraint WHERE conrelid = '{table}'::regclass")}
    names |= {row[0] for row in _probe(f"SELECT indexname FROM pg_indexes WHERE tablename = '{table}'")}
    return names


def _add(table: str, *columns: sa.Column) -> None:
    existing = _columns(table)
    for column in columns:
        if column.name not in existing:
            op.add_column(table, column.copy())


def _create_index_if_missing(name: str, table: str, *cols: str, unique: bool = False) -> None:
    if name not in _named_objects(table):
        op.create_index(name, table, list(cols), unique=unique)


def upgrade() -> None:
    if _dialect() != "postgresql":
        raise RuntimeError(
            "portal0001 targets PostgreSQL. For SQLite (tests / local), build the "
            "schema from the models: python -c \"import asyncio; from src.core.db import "
            "init_db; asyncio.run(init_db())\""
        )

    # ── portal tables ────────────────────────────────────────────────────────
    if not _has_table("portal_users"):
        op.create_table(
            "portal_users",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("email", sa.String(256), nullable=False),
            sa.Column("password_hash", sa.String(512), nullable=False),
            sa.Column("name", sa.String(256), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("last_login_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        )
        # A unique index, not a unique constraint: ``PortalUser.email`` is declared
        # ``unique=True, index=True``, so the ORM's own schema (and every DB built by
        # create_all) has one unique index here, not a constraint plus a plain index.
        op.create_index("ix_portal_users_email", "portal_users", ["email"], unique=True)
        op.create_index("ix_portal_users_active", "portal_users", ["is_active"])

    if not _has_table("merchant_memberships"):
        op.create_table(
            "merchant_memberships",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column(
                "user_id", sa.Integer(), sa.ForeignKey("portal_users.id", ondelete="CASCADE"), nullable=False
            ),
            sa.Column("merchant_key", sa.String(64), nullable=False),
            sa.Column("role", sa.String(16), nullable=False, server_default="owner"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("user_id", "merchant_key", name="uq_membership_user_merchant"),
        )
        op.create_index("ix_merchant_memberships_user_id", "merchant_memberships", ["user_id"])
        op.create_index("ix_membership_merchant_key", "merchant_memberships", ["merchant_key"])
        # ``MerchantMembership.merchant_key`` also sets index=True, which SQLAlchemy
        # names after the table; both indexes exist in the ORM schema.
        op.create_index("ix_merchant_memberships_merchant_key", "merchant_memberships", ["merchant_key"])

    if not _has_table("api_keys"):
        op.create_table(
            "api_keys",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("merchant_key", sa.String(64), nullable=False),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("key_prefix", sa.String(24), nullable=False),
            sa.Column("secret_hash", sa.String(64), nullable=False),
            sa.Column("scopes", sa.JSON(), nullable=True),
            sa.Column("mode", sa.String(16), nullable=False, server_default="observe"),
            sa.Column(
                "created_by", sa.Integer(), sa.ForeignKey("portal_users.id", ondelete="SET NULL"), nullable=True
            ),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_api_keys_merchant_key", "api_keys", ["merchant_key"])
        op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])
        op.create_index("ix_api_keys_active", "api_keys", ["merchant_key", "revoked_at"])

    if not _has_table("override_notes"):
        op.create_table(
            "override_notes",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("order_id", sa.String(64), nullable=False),
            sa.Column("merchant_key", sa.String(64), nullable=False),
            sa.Column("actor_email", sa.String(256), nullable=False),
            sa.Column("action", sa.String(16), nullable=False),
            sa.Column("from_verdict", sa.String(8), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_override_notes_order_id", "override_notes", ["order_id"])
        op.create_index("ix_override_notes_merchant_key", "override_notes", ["merchant_key"])

    # ── workspace key on the KYB merchant row ────────────────────────────────
    _add("merchants", sa.Column("merchant_key", sa.String(64), nullable=True))
    _create_index_if_missing("ix_merchants_merchant_key", "merchants", "merchant_key", unique=True)

    # ── two-gate fix: one row per (order, gate), not one row per order ───────
    objects = _named_objects("p2p_orders")
    if "uq_p2p_orders_order_id" in objects:
        op.drop_constraint("uq_p2p_orders_order_id", "p2p_orders", type_="unique")
    if "uq_p2p_orders_order_phase" not in _named_objects("p2p_orders"):
        op.create_unique_constraint("uq_p2p_orders_order_phase", "p2p_orders", ["order_id", "phase"])

    _add(
        "p2p_orders",
        sa.Column("step_up", sa.JSON(), nullable=True),
        sa.Column("behavioural_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("evidence_ref", sa.String(32), nullable=True),
        sa.Column("payment_method", sa.String(24), nullable=True),
        sa.Column("payer_name", sa.String(256), nullable=True),
        sa.Column("account_no_masked", sa.String(16), nullable=True),
        sa.Column("vpa", sa.String(128), nullable=True),
        sa.Column("utr", sa.String(64), nullable=True),
        sa.Column("credit_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    _create_index_if_missing("ix_p2p_orders_evidence_ref", "p2p_orders", "evidence_ref")
    _create_index_if_missing("ix_p2p_orders_utr", "p2p_orders", "utr")
    _create_index_if_missing("ix_p2p_orders_merchant_decided", "p2p_orders", "merchant_id", "decided_at")
    _create_index_if_missing("ix_p2p_orders_buyer_user", "p2p_orders", "buyer_user")

    # ── per-gate attribution, so a two-gate order does not double-count ──────
    _add("vendor_calls", sa.Column("phase", sa.String(16), nullable=False, server_default="release_gate"))
    _add("compliance_events", sa.Column("phase", sa.String(16), nullable=False, server_default="release_gate"))

    # ── freeze cases belong to a workspace ───────────────────────────────────
    _add("lien_cases", sa.Column("merchant_id", sa.String(64), nullable=False, server_default="default"))
    _create_index_if_missing("ix_lien_cases_merchant_id", "lien_cases", "merchant_id")


def downgrade() -> None:
    if _dialect() != "postgresql":
        raise RuntimeError("portal0001 downgrade targets PostgreSQL only.")

    for table in ("vendor_calls", "compliance_events"):
        if "phase" in _columns(table):
            op.drop_column(table, "phase")

    if "ix_lien_cases_merchant_id" in _named_objects("lien_cases"):
        op.drop_index("ix_lien_cases_merchant_id", table_name="lien_cases")
    if "merchant_id" in _columns("lien_cases"):
        op.drop_column("lien_cases", "merchant_id")

    if "uq_p2p_orders_order_phase" in _named_objects("p2p_orders"):
        op.drop_constraint("uq_p2p_orders_order_phase", "p2p_orders", type_="unique")
    if "uq_p2p_orders_order_id" not in _named_objects("p2p_orders"):
        op.create_unique_constraint("uq_p2p_orders_order_id", "p2p_orders", ["order_id"])
    for name in (
        "evidence_ref", "payment_method", "payer_name", "account_no_masked", "vpa", "utr",
        "credit_confirmed", "step_up", "behavioural_score",
    ):
        if name in _columns("p2p_orders"):
            op.drop_column("p2p_orders", name)
    for index in ("ix_p2p_orders_utr", "ix_p2p_orders_evidence_ref", "ix_p2p_orders_merchant_decided"):
        if index in _named_objects("p2p_orders"):
            op.drop_index(index, table_name="p2p_orders")

    if "ix_merchants_merchant_key" in _named_objects("merchants"):
        op.drop_index("ix_merchants_merchant_key", table_name="merchants")
    if "merchant_key" in _columns("merchants"):
        op.drop_column("merchants", "merchant_key")

    for table in ("override_notes", "api_keys", "merchant_memberships", "portal_users"):
        if _has_table(table):
            op.drop_table(table)
