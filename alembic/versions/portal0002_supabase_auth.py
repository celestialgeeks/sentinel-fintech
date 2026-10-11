"""Move credentials out of Sentinel and into Supabase Auth

Adds ``portal_users.auth_user_id`` (the GoTrue subject) and drops
``portal_users.password_hash``. After this revision the portal holds no password
material of any kind: the PBKDF2 hashes it used to store are gone, and the only
credential it accepts is an access token verified against the project's JWKS.

The drop is not automatic on a populated table. An existing local hash cannot be
converted into a GoTrue user without that user's password, so the revision stops
with instructions rather than silently stranding accounts. Reset the demo data,
or migrate real users through Supabase's invite flow, then re-run.

Revision ID: portal0002
Create Date: 2026-09-26
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "portal0002"
down_revision = "portal0001"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column("portal_users", "password_hash"):
        return

    # A NOT NULL auth_user_id cannot be conjured for rows that exist.
    existing = bind.execute(sa.text("SELECT count(*) FROM portal_users")).scalar() or 0
    if existing:
        raise RuntimeError(
            f"portal0002 refuses to run: portal_users holds {existing} row(s) whose passwords live "
            "only in this table. Supabase cannot derive an auth user from a PBKDF2 hash. For the "
            "demo database, delete the rows (and their merchant_memberships) and re-run; for real "
            "accounts, create the users with Supabase's admin invite API first, backfill "
            "auth_user_id, then apply this revision."
        )

    op.add_column(
        "portal_users",
        sa.Column("auth_user_id", sa.Uuid(as_uuid=False), nullable=False),
    )
    op.create_index("ix_portal_users_auth_user_id", "portal_users", ["auth_user_id"], unique=True)
    op.drop_column("portal_users", "password_hash")


def downgrade() -> None:
    if not _has_column("portal_users", "auth_user_id"):
        return
    # The hash is unrecoverable, so downgrade restores the column empty rather
    # than pretending accounts can go back to local passwords.
    op.add_column("portal_users", sa.Column("password_hash", sa.String(512), nullable=False, server_default=""))
    op.drop_index("ix_portal_users_auth_user_id", table_name="portal_users")
    op.drop_column("portal_users", "auth_user_id")
