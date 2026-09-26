"""Merchant portal tables: users, memberships, API keys, override notes.

Membership rows are what a session token is allowed to see, so these tables are
the security boundary for every read in :mod:`src.portal`.
"""


from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db import Base

from .base import TimestampMixin


class PortalUser(Base, TimestampMixin):
    """A web account for the merchant portal.

    Deliberately separate from the bot identity: the bot authenticates with an
    HMAC-signed call to the guard gates (see :class:`ApiKey`), a human signs in
    through Supabase Auth to read the ledger. Nothing here grants trading or
    custody access — Sentinel never holds either.

    There is no password column. Credentials (hash, verification, recovery,
    lockout) live in Supabase's ``auth.users``; ``auth_user_id`` is the subject
    claim of the access token the portal verifies, and the only link between the
    two. ``email`` is kept as a display and audit copy, not as a credential.
    """

    __tablename__ = "portal_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auth_user_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        unique=True,
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime]

    # Relationships
    memberships: Mapped[list["MerchantMembership"]] = relationship(
        "MerchantMembership",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (Index("ix_portal_users_active", "is_active"),)


class MerchantMembership(Base, TimestampMixin):
    """Which portal user may see which merchant workspace, and in what role.

    ``merchant_key`` is the same string the bot sends as
    ``P2POrder.merchant_id``; it is the join key between a login and the guard
    history, so it must stay stable for a workspace.
    """

    __tablename__ = "merchant_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("portal_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    merchant_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="owner")

    # Relationships
    user: Mapped["PortalUser"] = relationship("PortalUser", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("user_id", "merchant_key", name="uq_membership_user_merchant"),
        Index("ix_membership_merchant_key", "merchant_key"),
    )


class ApiKey(Base, TimestampMixin):
    """A bot-facing integration credential: HMAC secret + reveal-once prefix.

    Only the SHA-256 hash of the secret is stored. The plaintext is returned a
    single time at creation; afterwards the portal can show the prefix, last use
    and revoke, but never the secret.
    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merchant_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    scopes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="observe")
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("portal_users.id", ondelete="SET NULL"), nullable=True
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime]

    __table_args__ = (Index("ix_api_keys_active", "merchant_key", "revoked_at"),)


class OverrideNote(Base, TimestampMixin):
    """Audit trail for a human overruling a guard verdict.

    The engine is not mutable: an override never rewrites ``verdict`` or the
    evidence bundle. It records *who disagreed, when, and why*, so the ledger
    still tells the truth about what the guard said.
    """

    __tablename__ = "override_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    merchant_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_email: Mapped[str] = mapped_column(String(256), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    from_verdict: Mapped[str] = mapped_column(String(8), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime]
