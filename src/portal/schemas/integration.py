"""API-key and connectivity models behind the "connect your bot" wizard.
"""


from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.p2p.schemas import GuardDecision


class ApiKeyRow(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: list[str] = Field(default_factory=list)
    mode: str = "observe"
    created_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    active: bool = True


class CreatedApiKey(BaseModel):
    """Returned once. ``hmac_secret`` is unrecoverable after this response."""

    id: str
    name: str
    key_prefix: str
    hmac_secret: str
    display_once: bool = True
    note: str = "Copy this secret now. Sentinel stores only its hash."


class CreateKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128, description="e.g. 'prod bot'")
    scopes: list[str] = Field(default_factory=lambda: ["guard:call"])
    mode: str = Field("observe", description="observe | enforce")


class EndpointInfo(BaseModel):
    method: str
    path: str
    purpose: str


class IntegrationStatus(BaseModel):
    merchant_key: str
    transport: str = Field(description="rest | kafka")
    connected: bool = Field(False, description="At least one live (non-sandbox) order seen")
    has_api_key: bool = False
    hmac_enforced: bool = Field(False, description="GUARD_HMAC_SECRET is set server-side")
    orders_total: int = 0
    first_order_at: datetime | None = None
    last_order_at: datetime | None = None
    endpoints: list[EndpointInfo] = Field(default_factory=list)
    kafka_topics: list[str] = Field(default_factory=list)
    signature_help: str = ""
    sandbox_available: bool = True


class ConnectionTestRequest(BaseModel):
    """Wizard step 4: run a real decision through the real pipeline.

    ``order`` is the raw ``P2POrder`` payload; ``phase`` selects the gate. Nothing
    is persisted and nothing is published, so a test can never pollute the ledger.
    """

    order: dict
    phase: str = Field("pre_screen", description="pre_screen | release_gate")


class ConnectionTestResponse(BaseModel):
    decision: GuardDecision
    persisted: bool = False
    published: bool = False
