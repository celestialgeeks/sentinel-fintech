"""Environment-backed configuration for the merchant portal.

Field names mirror the keys already documented in ``.env.example``
(``JWT_SECRET``, ``JWT_EXPIRE_MINUTES``, ``CORS_ORIGINS``) so there is one place
to set them and no new vocabulary.
"""

from __future__ import annotations

import logging
import secrets
from functools import lru_cache

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class PortalSettings(BaseSettings):
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    app_env: str = "development"
    cors_origins: str = "*"
    demo_mode: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "ignore"}


# Ephemeral dev key: stable for the life of the process, never reused on restart.
_ephemeral_secret: str | None = None


@lru_cache
def get_portal_settings() -> PortalSettings:
    return PortalSettings()


def signing_secret() -> str:
    """Return the HMAC key for session tokens.

    In production an unset ``JWT_SECRET`` is a hard error rather than a silent
    fallback — a guessable signing key means anyone can mint a merchant session.
    Outside production we generate a per-process random key so the portal works
    out of the box (sessions simply end on restart).
    """
    global _ephemeral_secret

    secret = get_portal_settings().jwt_secret.strip()
    if secret:
        return secret
    if get_portal_settings().app_env.lower() in {"production", "prod"}:
        raise RuntimeError("JWT_SECRET must be set in production")
    if _ephemeral_secret is None:
        _ephemeral_secret = secrets.token_hex(32)
        logger.warning("JWT_SECRET unset — using an ephemeral dev key. Sessions end on restart.")
    return _ephemeral_secret


def token_ttl_minutes() -> int:
    return max(1, get_portal_settings().jwt_expire_minutes)


def cors_origin_list() -> list[str]:
    """CORS origins from ``CORS_ORIGINS`` (comma-separated). ``*`` stays ``*``."""
    raw = get_portal_settings().cors_origins.strip()
    if not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


# ─── Supabase Auth ────────────────────────────────────────────────────────────


def supabase_auth_enabled() -> bool:
    """True when a Supabase project is configured, i.e. Google sign-in is live."""
    return bool(get_portal_settings().supabase_url.strip())


def supabase_issuer() -> str:
    """The ``iss`` every accepted token must carry.

    GoTrue identifies itself by ``<project url>/auth/v1``; ``SUPABASE_JWT_ISSUER``
    overrides that for a project behind a custom domain. Checking the issuer is
    what stops a token from some other Supabase project — with its own valid JWKS
    and the same ``aud`` — from being honoured here.
    """
    settings = get_portal_settings()
    explicit = settings.supabase_jwt_issuer.strip().rstrip("/")
    if explicit:
        return explicit
    return f"{settings.supabase_url.strip().rstrip('/')}/auth/v1"


def supabase_audience() -> str:
    """The ``aud`` Supabase puts on user access tokens (``authenticated``)."""
    return get_portal_settings().supabase_jwt_audience.strip() or "authenticated"


def supabase_jwks_url() -> str:
    """Where the ES256 signing keys are published — Supabase's own OIDC endpoint."""
    return f"{supabase_issuer()}/.well-known/jwks.json"

