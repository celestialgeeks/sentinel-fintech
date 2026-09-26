"""Sentinel ORM schema, one module per bounded context.

Importing this package registers every table on ``Base.metadata``, which is
what Alembic autogenerates against and what the test harness creates in
SQLite. Modules import the symbols they need from here (or from the
submodule directly); nothing outside ``core`` should declare a table.
"""

from __future__ import annotations

from src.core.models.base import (
    PkBigInt,
    TimestampMixin,
)
from src.core.models.enums import (
    AlertStatusEnum,
    KYBStatusEnum,
    KYCStatusEnum,
    MerchantStatusEnum,
    RecommendationEnum,
    SeverityEnum,
    TransactionStatusEnum,
)
from src.core.models.guard import (
    ComplianceEvent,
    Counterparty,
    EvidenceBundle,
    LienCase,
    P2POrderRecord,
    SettlementVoucher,
    VendorCall,
)
from src.core.models.platform import (
    EntityGraph,
    FraudAlert,
    Merchant,
    ScreeningResult,
    Transaction,
    UserProfile,
)
from src.core.models.portal import (
    ApiKey,
    MerchantMembership,
    OverrideNote,
    PortalUser,
)

__all__ = [
    "Transaction",
    "ScreeningResult",
    "FraudAlert",
    "Merchant",
    "UserProfile",
    "EntityGraph",
    "P2POrderRecord",
    "Counterparty",
    "VendorCall",
    "EvidenceBundle",
    "SettlementVoucher",
    "LienCase",
    "ComplianceEvent",
    "PortalUser",
    "MerchantMembership",
    "ApiKey",
    "OverrideNote",
    "AlertStatusEnum",
    "KYBStatusEnum",
    "KYCStatusEnum",
    "MerchantStatusEnum",
    "RecommendationEnum",
    "SeverityEnum",
    "TransactionStatusEnum",
    "PkBigInt",
    "TimestampMixin",
]
