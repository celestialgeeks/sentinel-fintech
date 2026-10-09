"""Session and workspace models: signup, login, ``/auth/me``, merchant creation.

``OAuthLinkRequest`` is the odd one out: it carries no credential, because
Supabase already vouched for the caller before this request was made.
"""


from __future__ import annotations

from pydantic import BaseModel, Field


class MerchantRef(BaseModel):
    """A workspace the caller can see. ``merchant_key`` is the bot's merchant_id."""

    merchant_key: str
    business_name: str
    role: str = "owner"
    country: str = "IN"
    orders: int = 0


class UserInfo(BaseModel):
    user_id: int
    email: str
    name: str | None = None


class SignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=256)
    name: str | None = None
    business_name: str | None = None
    country: str = Field("IN", min_length=2, max_length=2)
    monthly_volume_inr: float | None = Field(None, ge=0)
    runs_bot: str | None = Field(None, description="own_code | tool | not_yet")
    merchant_key: str | None = Field(
        None,
        max_length=64,
        description=(
            "The merchant_id your bot already sends. Omit to get a generated key; "
            "set it to keep an existing bot's payloads working unchanged."
        ),
    )


class LoginRequest(BaseModel):
    email: str
    password: str


class OAuthLinkRequest(BaseModel):
    """First-run details for an identity that arrived through Google.

    A Google sign-in authenticates the *person* at Supabase but says nothing about
    which merchant desk they own, so the portal asks for the same two facts the
    signup form collects. Everything is optional: omitting ``business_name`` yields
    the same placeholder signup uses, and omitting ``merchant_key`` yields a
    generated one.
    """

    business_name: str | None = Field(None, min_length=2, max_length=256)
    country: str = Field("IN", min_length=2, max_length=2)
    merchant_key: str | None = Field(
        None,
        max_length=64,
        description="The merchant_id your bot already sends. Generated when omitted.",
    )


class RefreshRequest(BaseModel):
    """Swap a refresh token for a new session.

    Supabase access tokens live an hour (``jwt_exp``), so the frontend needs this
    to keep a merchant signed in across a working session.
    """

    refresh_token: str = Field(min_length=16)


class AuthResponse(BaseModel):
    access_token: str = Field(..., description="Supabase access token; send it as the Bearer credential")
    refresh_token: str = Field(..., description="Opaque token for /auth/refresh; store it like a password")
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Seconds until the token expires")
    user: UserInfo
    merchants: list[MerchantRef] = Field(default_factory=list)


class MeResponse(BaseModel):
    user: UserInfo
    merchants: list[MerchantRef] = Field(default_factory=list)


class CreateMerchantRequest(BaseModel):
    business_name: str = Field(min_length=2, max_length=256)
    country: str = Field("IN", min_length=2, max_length=2)
    industry: str | None = None
    merchant_key: str | None = Field(
        None,
        max_length=64,
        description="Optional stable key. Generated when omitted; must match what the bot sends.",
    )
