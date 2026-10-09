"""Request/response schemas for the merchant portal.

These are the exact shapes the frontend consumes, and their field names are kept
aligned with ``docs/WEBSITE_CONTENT_BRIEF.md`` so the mockups and the API never
drift apart. Two deliberate choices:

* **Risk and confidence stay 0-1 floats** — the engine's native range. The
  frontend formats ``93%``; the API does not invent a 0-100 scale that the guard
  never produces.
* **Money is returned as a number, never a pre-formatted string.** Indian digit
  grouping (``₹4,52,250``) is a view concern.

One module per capability (``common``, ``auth``, ``integration``, ``ledger``,
``insights``); this façade re-exports them, so callers keep importing from
``src.portal.schemas`` whichever file a model lives in.
"""

from __future__ import annotations

from src.portal.schemas.auth import (
    AuthResponse,
    CreateMerchantRequest,
    LoginRequest,
    MerchantRef,
    MeResponse,
    OAuthLinkRequest,
    RefreshRequest,
    SignupRequest,
    UserInfo,
)
from src.portal.schemas.common import (
    Page,
    T,
)
from src.portal.schemas.insights import (
    OverviewResponse,
    ProviderStat,
    RiskBucket,
    RuleStat,
    Sparkline,
    StatsSummary,
    TimeseriesPoint,
    TrendPoint,
    VerdictCounts,
)
from src.portal.schemas.integration import (
    ApiKeyRow,
    ConnectionTestRequest,
    ConnectionTestResponse,
    CreatedApiKey,
    CreateKeyRequest,
    EndpointInfo,
    IntegrationStatus,
)
from src.portal.schemas.ledger import (
    BuyerBlock,
    ComplianceRow,
    CounterpartyRow,
    DecisionBlock,
    EvidenceMeta,
    LienCaseFile,
    LienCreateRequest,
    LienRow,
    LienUpdateRequest,
    OrderDetail,
    OrderRow,
    OverrideRequest,
    OverrideRow,
    PaymentBlock,
    TimelineNode,
    VendorCallRow,
    VoucherRow,
    WalletBlock,
)

__all__ = [
    "AuthResponse",
    "CreateMerchantRequest",
    "LoginRequest",
    "MeResponse",
    "MerchantRef",
    "RefreshRequest",
    "SignupRequest",
    "OAuthLinkRequest",
    "UserInfo",
    "Page",
    "T",
    "OverviewResponse",
    "ProviderStat",
    "RiskBucket",
    "RuleStat",
    "Sparkline",
    "StatsSummary",
    "TimeseriesPoint",
    "TrendPoint",
    "VerdictCounts",
    "ApiKeyRow",
    "ConnectionTestRequest",
    "ConnectionTestResponse",
    "CreateKeyRequest",
    "CreatedApiKey",
    "EndpointInfo",
    "IntegrationStatus",
    "BuyerBlock",
    "ComplianceRow",
    "CounterpartyRow",
    "DecisionBlock",
    "EvidenceMeta",
    "LienCaseFile",
    "LienCreateRequest",
    "LienRow",
    "LienUpdateRequest",
    "OrderDetail",
    "OrderRow",
    "OverrideRequest",
    "OverrideRow",
    "PaymentBlock",
    "TimelineNode",
    "VendorCallRow",
    "VoucherRow",
    "WalletBlock",
]
