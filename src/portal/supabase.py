"""Supabase Auth as the credential authority for the merchant portal.

Passwords are Sentinel's single largest liability, so the portal stopped holding
them. Supabase owns the credential (bcrypt hash, email verification, lockout,
recovery, future OAuth/MFA); Sentinel keeps only the *workspace* facts — which
merchant keys a human may read, and in what role.

Three boundaries matter here:

* **Verification is local.** Every request verifies the Supabase access token
  against the project's JWKS, so a request costs one cache lookup rather than a
  round trip to GoTrue. The algorithm is taken from the JWK that matches the
  token's ``kid`` and intersected with :data:`ALLOWED_ALGORITHMS`; ``alg`` from
  the token header is never trusted on its own, which is what makes an HS256
  downgrade impossible even if a caller sends one.
* **The service-role key never leaves the server.** It can create and delete
  authenticated users, so it is used only for outbound admin calls, never
  returned to a client and never logged.
* **Signup provisions two things or nothing.** A GoTrue user plus the
  ``portal_users`` row must stay in step; :func:`create_verified_user` is the
  only path that mints credentials, and the router rolls back its local row when
  the remote call fails.

The legacy ``service_role`` JWT is used rather than the newer ``sb_secret_*``
key: Supabase only reveals the latter once, at creation, and returns it redacted
from every listing endpoint afterwards.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import quote
from weakref import WeakKeyDictionary

import httpx
import jwt
from pydantic_settings import BaseSettings

# Only asymmetric signing is accepted. A project configured for the legacy HS256
# secret would have to be migrated before the portal could verify its tokens.
ALLOWED_ALGORITHMS = frozenset({"ES256", "RS256", "RS512", "EdDSA"})

# How long a fetched key set stays fresh. Supabase rotates signing keys on a
# scale of days, and an unknown ``kid`` forces a refresh ahead of this timer.
_JWKS_TTL_SECONDS = 300


class SupabaseSettings(BaseSettings):
    """``SUPABASE_*`` from the environment. Mirrors ``.env.example``."""

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_audience: str = "authenticated"
    supabase_jwt_issuer: str = ""
    supabase_timeout_seconds: float = 10.0
    app_env: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "ignore"}

    @property
    def jwt_issuer(self) -> str:
        # GoTrue stamps ``iss`` with the project's auth endpoint. The override
        # exists for custom domains, where the published issuer is not the URL
        # the portal happens to know.
        return self.supabase_jwt_issuer.strip() or f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_supabase_settings() -> SupabaseSettings:
    return SupabaseSettings()


def configured() -> bool:
    """True when the portal can authenticate anyone at all."""
    s = get_supabase_settings()
    return bool(s.supabase_url and s.supabase_anon_key and s.supabase_service_role_key)


class SupabaseAuthError(RuntimeError):
    """Raised for every rejected credential or failed GoTrue call.

    ``status_code`` is what the router should forward; ``detail`` is written to
    be shown to the merchant, so it never carries the token, the key, or a
    reason that would reveal whether an email is registered.
    """

    def __init__(self, detail: str, *, status_code: int = 401) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _require_configured() -> SupabaseSettings:
    settings = get_supabase_settings()
    if not configured():
        # Loud failure, not a silent 401: an unconfigured deployment otherwise
        # looks exactly like a database full of bad passwords.
        raise SupabaseAuthError(
            "Supabase Auth is not configured (SUPABASE_URL / SUPABASE_ANON_KEY / SUPABASE_SERVICE_ROLE_KEY)",
            status_code=503,
        )
    return settings


# ─── HTTP ─────────────────────────────────────────────────────────────────────

# One client for the process, so connections are pooled and kept alive. Building
# an ``AsyncClient`` per request means a fresh TCP+TLS handshake to the project's
# region on every single call: measured on this project, that turned a 40-second
# test run into a 35-minute one and made cold-start read timeouts common enough to
# fail a merchant's signup.
_RETRIES = 2
_TRANSIENT = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
)

# A pooled client belongs to the event loop that opened it, so it is keyed by loop
# rather than held in one global: pytest-asyncio gives every test its own loop, and
# reusing a client across loops fails with "Event loop is closed". A weak key lets
# the client (and its sockets) go away with the loop that owned it.
_clients: WeakKeyDictionary[asyncio.AbstractEventLoop, httpx.AsyncClient] = WeakKeyDictionary()


def _http() -> httpx.AsyncClient:
    """The pooled client for the running loop, created on first use."""
    timeout = get_supabase_settings().supabase_timeout_seconds
    loop = asyncio.get_running_loop()
    client = _clients.get(loop)
    if client is None or client.is_closed:
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=max(10.0, timeout)),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
        _clients[loop] = client
    return client


async def close_client() -> None:
    """Release the running loop's pooled connections (app shutdown, test teardown)."""
    client = _clients.pop(asyncio.get_running_loop(), None)
    if client is not None and not client.is_closed:
        await client.aclose()


async def _request(
    method: str, url: str, *, headers: dict[str, str], body: dict[str, Any] | None = None
) -> httpx.Response:
    """Call GoTrue, retrying transport failures with a short backoff.

    Only connection-level faults are retried — a 401 is never re-attempted, so a
    wrong password cannot be turned into a slow denial of service on ourselves.
    The exception *type* is reported because ``httpx.ReadTimeout`` has an empty
    message, which previously surfaced as "cannot reach the auth server:" with
    nothing after the colon.
    """
    last: Exception | None = None
    for attempt in range(_RETRIES + 1):
        try:
            return await _http().request(method, url, headers=headers, json=body)
        except _TRANSIENT as exc:
            last = exc
            if attempt < _RETRIES:
                await asyncio.sleep(0.4 * (2**attempt))
    raise SupabaseAuthError(f"cannot reach the auth server: {type(last).__name__}", status_code=503)


def _anon_headers(settings: SupabaseSettings) -> dict[str, str]:
    return {"apikey": settings.supabase_anon_key, "Content-Type": "application/json"}


def _admin_headers(settings: SupabaseSettings) -> dict[str, str]:
    key = settings.supabase_service_role_key
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


# ─── Token verification ───────────────────────────────────────────────────────

# url -> (fetched_at, {kid: jwk}). One dict per project; a refresh replaces it whole.
_jwks_cache: dict[str, tuple[float, dict[str, dict[str, Any]]]] = {}


async def _fetch_jwks(url: str, *, force: bool = False) -> dict[str, dict[str, Any]]:
    """Return the project's ``kid -> JWK`` map, cached for :data:`_JWKS_TTL_SECONDS`."""
    cached = _jwks_cache.get(url)
    if not force and cached and (time.monotonic() - cached[0]) < _JWKS_TTL_SECONDS:
        return cached[1]

    response = await _request("GET", url, headers={})  # the JWKS endpoint is public
    try:
        response.raise_for_status()
        keys = response.json().get("keys", [])
    except (httpx.HTTPError, ValueError) as exc:
        raise SupabaseAuthError(f"cannot read the auth server's keys: {exc}", status_code=503) from exc

    by_kid = {k["kid"]: k for k in keys if isinstance(k, dict) and k.get("kid")}
    if not by_kid:
        raise SupabaseAuthError("the auth server published no verification keys", status_code=503)
    _jwks_cache[url] = (time.monotonic(), by_kid)
    return by_kid


def _key_for(by_kid: dict[str, dict[str, Any]], kid: str, claimed_alg: str) -> Any:
    """Resolve the verification key for ``kid``, refusing any algorithm not allowed."""
    jwk = by_kid.get(kid)
    if jwk is None:
        raise SupabaseAuthError("signing key no longer available", status_code=401)
    jwk_alg = jwk.get("alg") or claimed_alg
    if jwk_alg not in ALLOWED_ALGORITHMS:
        raise SupabaseAuthError("unsupported token algorithm", status_code=401)
    if claimed_alg != jwk_alg:
        # The header is attacker-controlled; the published key is not.
        raise SupabaseAuthError("token algorithm does not match the signing key", status_code=401)
    try:
        return jwt.PyJWK(jwk).key
    except Exception as exc:  # noqa: BLE001 - a malformed JWK is a verification failure
        raise SupabaseAuthError(f"unusable signing key: {exc}", status_code=503) from exc


async def verify_access_token(token: str) -> dict[str, Any]:
    """Verify a Supabase access token and return its claims.

    Raises :class:`SupabaseAuthError` for anything that is not a current,
    correctly-signed session token for *this* project: bad signature, unknown
    ``kid``, disallowed or mismatched ``alg``, wrong ``aud``/``iss``, or a missing
    time claim.
    """
    settings = _require_configured()
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise SupabaseAuthError("malformed token", status_code=401) from exc

    kid, alg = header.get("kid"), header.get("alg")
    if not kid or not alg:
        raise SupabaseAuthError("token is missing its key identifier", status_code=401)

    by_kid = await _fetch_jwks(settings.jwks_url)
    try:
        key = _key_for(by_kid, kid, alg)
    except SupabaseAuthError:
        # Supabase can rotate a signing key at any time; an unknown kid is
        # refreshed for once before being rejected, so rotation is not an
        # outage for already-issued sessions.
        by_kid = await _fetch_jwks(settings.jwks_url, force=True)
        key = _key_for(by_kid, kid, alg)

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience=settings.supabase_jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "aud", "iss", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise SupabaseAuthError("token is not valid", status_code=401) from exc

    if claims.get("role") != settings.supabase_jwt_audience:
        raise SupabaseAuthError("token is not a user session", status_code=401)
    return claims


# ─── Sessions ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Session:
    """A GoTrue session, shaped for the portal's ``AuthResponse``."""

    access_token: str
    refresh_token: str
    expires_in: int
    user_id: str
    email: str


def _session(payload: dict[str, Any]) -> Session:
    try:
        user = payload["user"] or {}
        return Session(
            access_token=payload["access_token"],
            refresh_token=payload["refresh_token"],
            expires_in=int(payload.get("expires_in") or 3600),
            user_id=user["id"],
            email=(user.get("email") or "").lower(),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SupabaseAuthError("the auth server returned an incomplete session", status_code=502) from exc


async def _post(settings: SupabaseSettings, path: str, body: dict[str, Any], *, admin: bool = False) -> Any:
    headers = _admin_headers(settings) if admin else _anon_headers(settings)
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1{path}"
    response = await _request("POST", url, headers=headers, body=body)

    if response.status_code >= 400:
        raise _gotrue_error(response)
    try:
        return response.json()
    except ValueError as exc:
        raise SupabaseAuthError("the auth server returned an unreadable response", status_code=502) from exc


def _gotrue_error(response: httpx.Response) -> SupabaseAuthError:
    """Map a GoTrue error onto a portal error without leaking account existence.

    GoTrue already answers a wrong password and an unknown account with the same
    ``invalid_credentials``, and the portal keeps that property: both become one
    message. Order matters — an "already exists" reply is a 422 too, so it has to
    be tested before the weak-password fallback.
    """
    try:
        payload = response.json() or {}
    except ValueError:
        payload = {}
    code = str(payload.get("error_code") or "")
    message = str(payload.get("msg") or payload.get("error_description") or "").lower()

    if code in {"invalid_credentials", "email_not_confirmed"} or "invalid login credentials" in message:
        return SupabaseAuthError("email or password is incorrect", status_code=401)
    if code in {"refresh_token_not_found", "refresh_token_already_used"}:
        return SupabaseAuthError("this session can no longer be refreshed", status_code=401)
    exists = code in {"user_already_exists", "email_exists"} or "already registered" in message
    if exists or "already been registered" in message:
        return SupabaseAuthError("an account for that email already exists", status_code=409)
    if code == "weak_password" or "password should be at least" in message:
        return SupabaseAuthError("that password is not strong enough", status_code=422)
    if response.status_code == 429:
        return SupabaseAuthError("too many attempts, try again shortly", status_code=429)
    return SupabaseAuthError("the auth server could not complete this request", status_code=502)


async def sign_in(email: str, password: str) -> Session:
    """Exchange email + password for a session. The password is never stored."""
    settings = _require_configured()
    return _session(await _post(settings, "/token?grant_type=password", {"email": email, "password": password}))


async def refresh_session(refresh_token: str) -> Session:
    """Rotate a refresh token for a new session."""
    settings = _require_configured()
    payload = await _post(settings, "/token?grant_type=refresh_token", {"refresh_token": refresh_token})
    return _session(payload)


async def create_verified_user(email: str, password: str, *, name: str | None = None) -> Session:
    """Create a confirmed GoTrue user, then sign it in.

    Signup goes through the admin API because the project has email confirmation
    on and no SMTP configured, so a public ``/signup`` would park the account in
    an unverifiable state: no session, and no way to sign in. Creating the user
    confirmed and then performing the password grant keeps the portal's
    "signup signs you in" contract.

    When SMTP is wired up, swapping this for ``/signup`` plus a confirmation link
    is a one-function change; nothing else in the portal assumes the account was
    auto-confirmed.
    """
    settings = _require_configured()
    body: dict[str, Any] = {
        "email": email,
        "password": password,
        "email_confirm": True,
        "app_metadata": {"provider": "email"},
    }
    if name:
        body["data"] = {"name": name}
    created = await _post(settings, "/admin/users", body, admin=True)
    try:
        user_id = created["id"]
    except (KeyError, TypeError) as exc:
        raise SupabaseAuthError("the auth server did not return a user id", status_code=502) from exc

    session = await sign_in(email, password)
    # The admin response is authoritative for the id; if the two ever disagree,
    # the local profile would be filed under the wrong subject and the account
    # would be unreadable forever.
    if session.user_id != user_id:
        raise SupabaseAuthError("the auth server returned an inconsistent session", status_code=502)
    return session


async def delete_user(user_id: str) -> None:
    """Remove a GoTrue user. Used by the seeder and the test harness to clean up."""
    settings = _require_configured()
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{user_id}"
    response = await _request("DELETE", url, headers=_admin_headers(settings))
    if response.status_code not in {200, 204, 404}:
        raise SupabaseAuthError("the auth server could not delete this user", status_code=502)


async def find_user(email: str) -> dict[str, Any] | None:
    """Look up one address by email, or ``None``.

    Filtered server-side rather than paging through everyone: the seeder and the
    test harness call this per signup, and a full listing there is both slower and
    stale the moment a user is created mid-run.
    """
    settings = _require_configured()
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users?per_page=10&filter={quote(email)}"
    response = await _request("GET", url, headers=_admin_headers(settings))
    if response.status_code >= 400:
        raise _gotrue_error(response)
    wanted = email.strip().lower()
    for user in response.json().get("users", []):
        if (user.get("email") or "").strip().lower() == wanted:
            return user
    return None


async def list_users(*, per_page: int = 1000) -> list[dict[str, Any]]:
    """Admin user listing, for the test harness and support tooling."""
    settings = _require_configured()
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users?page=1&per_page={per_page}"
    response = await _request("GET", url, headers=_admin_headers(settings))
    if response.status_code >= 400:
        raise _gotrue_error(response)
    payload = response.json()
    return payload.get("users", payload if isinstance(payload, list) else [])


async def sign_out(access_token: str) -> None:
    """Revoke the caller's session server-side."""
    settings = _require_configured()
    url = f"{settings.supabase_url.rstrip('/')}/auth/v1/logout"
    headers = {"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {access_token}"}
    response = await _request("POST", url, headers=headers)
    # A session that is already gone is a successful logout, not an error.
    if response.status_code >= 400 and response.status_code != 401:
        raise _gotrue_error(response)


def reset_jwks_cache() -> None:
    """Drop cached signing keys (tests, and after a project's keys are rotated)."""
    _jwks_cache.clear()
