"""Environment-backed configuration for vendor adapters.

Keys are optional: an adapter with no key reports itself unavailable and the
aggregator either falls back to a mock (dev) or applies the provider's fail
policy (prod). This keeps the codebase runnable before commercial contracts are
signed and lets CI exercise the full pipeline.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class VendorSettings(BaseSettings):
    # on-chain analytics
    chainalysis_api_key: str | None = None
    elliptic_api_key: str | None = None
    cryptoauthet_api_key: str | None = None
    cryptoauthet_base_url: str = "https://api.cryptoauthet.com/v1"

    # India mule / bank / name intelligence
    idfy_client_id: str | None = None
    idfy_client_secret: str | None = None
    signzy_private_key: str | None = None
    signzy_public_key: str | None = None
    hyperverge_api_key: str | None = None

    # sanctions / PEP feed
    sanctions_feed_url: str | None = None  # World-Check / LSEG / Dow Jones
    sanctions_api_key: str | None = None

    # account aggregator (consented bank-credit verification)
    aa_client_id: str | None = None
    aa_client_secret: str | None = None

    # behaviour
    use_mocks_when_unconfigured: bool = True   # dev-friendly default
    max_vendor_latency_ms: int = 6000          # total fan-out budget per order
    cache_default_ttl: int = 300

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "ignore"}


@lru_cache
def get_vendor_settings() -> VendorSettings:
    return VendorSettings()
