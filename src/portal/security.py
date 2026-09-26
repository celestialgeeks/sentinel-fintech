"""Cryptographic primitives for the merchant portal — standard library only.

``requirements.txt`` lists ``python-jose`` and ``passlib[bcrypt]``, but neither is
installed in the working venv, and adding a dependency to ship a read API would be
the wrong trade. Everything a portal needs here is small and well-trodden:

* **Passwords** — PBKDF2-HMAC-SHA256 with a per-password salt (``hashlib``),
  stored in a self-describing string so the iteration count can be raised later
  without a migration.
* **Sessions** — a compact HS256 JWT (``hmac`` + ``base64url`` + ``json``) with
  ``exp``/``iat``/``nbf`` enforced and constant-time signature comparison.
* **Bot credentials** — ``secrets``-generated HMAC secrets; only their SHA-256
  digest is persisted, the plaintext is returned once at creation.

All comparisons that touch a secret use :func:`hmac.compare_digest`, never ``==``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

# ─── Passwords ────────────────────────────────────────────────────────────────

_PBKDF2_ITERATIONS = 240_000
_ALGORITHM = "pbkdf2_sha256"


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def hash_password(password: str, *, iterations: int = _PBKDF2_ITERATIONS) -> str:
    """Return a self-describing PBKDF2 hash: ``algo$iterations$salt$digest``."""
    if not password:
        raise ValueError("password must not be empty")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"{_ALGORITHM}${iterations}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    """Check ``password`` against a stored hash. Unknown formats fail closed."""
    try:
        algo, iters, salt_b64, digest_b64 = stored.split("$")
        if algo != _ALGORITHM:
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), _b64_decode(salt_b64), int(iters))
        return hmac.compare_digest(_b64(candidate), digest_b64)
    except (ValueError, TypeError, AttributeError):
        return False


# ─── Tokens ───────────────────────────────────────────────────────────────────


class TokenError(ValueError):
    """Raised for any invalid, expired, or tampered token."""


def _secret_key(secret: str) -> bytes:
    key = secret.strip()
    if not key:
        # Never fall back to an empty key: an unconfigured JWT secret must not
        # silently mint tokens anyone can forge. Fail loudly instead.
        raise TokenError("JWT_SECRET is not configured")
    return key.encode()


def encode_jwt(claims: dict[str, Any], secret: str, *, ttl_minutes: int = 720) -> str:
    """Sign ``claims`` as an HS256 JWT valid for ``ttl_minutes``."""
    now = int(time.time())
    payload = {**claims, "iat": now, "nbf": now, "exp": now + ttl_minutes * 60}
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
    payload_b64 = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(_secret_key(secret), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64(signature)}"


def decode_jwt(token: str, secret: str) -> dict[str, Any]:
    """Verify signature and time claims, returning the payload.

    Raises :class:`TokenError` on any failure — a missing segment, a bad base64,
    a non-HS256 ``alg`` (algorithm-confusion guard), a mismatched signature, or
    an expired / not-yet-valid token.
    """
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise TokenError("malformed token") from exc

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(_secret_key(secret), signing_input, hashlib.sha256).digest()
    try:
        provided = _b64_decode(signature_b64)
        header = json.loads(_b64_decode(header_b64))
        payload = json.loads(_b64_decode(payload_b64))
    except (ValueError, TypeError) as exc:
        raise TokenError("malformed token") from exc

    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise TokenError("unsupported algorithm")
    if not hmac.compare_digest(expected, provided):
        raise TokenError("bad signature")

    now = time.time()
    if "exp" in payload and now >= float(payload["exp"]):
        raise TokenError("token expired")
    if "nbf" in payload and now < float(payload["nbf"]) - 1:
        raise TokenError("token not yet valid")
    if not isinstance(payload, dict):
        raise TokenError("malformed payload")
    return payload


# ─── Bot credentials ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NewCredential:
    """A freshly minted key. ``hmac_secret`` is never recoverable afterwards."""

    key_prefix: str
    hmac_secret: str
    secret_hash: str


def issue_credential() -> NewCredential:
    """Generate a guard integration credential.

    ``key_prefix`` is a stable public identifier safe to log and display;
    ``hmac_secret`` is what the bot puts in ``GUARD_HMAC_SECRET`` to sign
    ``X-Sentinel-Signature``; only ``secret_hash`` is stored.
    """
    raw = secrets.token_hex(32)
    return NewCredential(
        key_prefix=f"sent_{raw[:12]}",
        hmac_secret=raw,
        secret_hash=hashlib.sha256(raw.encode()).hexdigest(),
    )


def hash_secret(secret: str) -> str:
    """SHA-256 hex of a secret, for storage or comparison."""
    return hashlib.sha256(secret.encode()).hexdigest()


def token_matches(candidate: str, stored_hash: str) -> bool:
    """Constant-time check of a presented secret against its stored digest."""
    return hmac.compare_digest(hash_secret(candidate), stored_hash)


def new_slug(prefix: str, entropy_bytes: int = 5) -> str:
    """Short unique label, e.g. ``merch_a1b2c3`` for a workspace key."""
    return f"{prefix}_{secrets.token_hex(entropy_bytes)}"
