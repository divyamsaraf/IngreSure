"""
Rate limiting: caller identification (key_func) and per-route limit strings for slowapi.

Caller identification precedence (used both for bucketing and B2B tier lookup):
    1. X-API-Key header          -> B2B tier lookup via B2B_API_KEYS
    2. Authorization: Bearer ...  -> verified anon-session token -> user_id
    3. Client IP address          -> always-available fallback

Rate limit recommendation (why these defaults):
    - Anonymous chat: 20/minute. 60/min is too high for a real grocery chat UI;
      humans rarely send >10-15 messages/min, so a lower cap meaningfully
      reduces abuse/LLM cost with negligible impact on legitimate users.
    - Authenticated (anon-token) chat: 30/minute — a bit more headroom once a
      caller has a stable identity.
    - Profile read: 60/minute (cheap, frequently polled). Profile write:
      30/minute (mutates persisted state).
    - B2B /api/v1/* tiers (paid): starter 60/min, growth 300/min,
      enterprise 1000/min, from B2B_API_KEYS.

Env vars (all optional; defaults above apply when unset):
    RATE_LIMIT_CHAT_ANON        Anonymous /chat/grocery limit. Default "20/minute".
    RATE_LIMIT_CHAT_AUTH        Authenticated /chat/grocery limit. Default "30/minute".
    RATE_LIMIT_PROFILE_READ     GET /profile/{user_id} limit. Default "60/minute".
    RATE_LIMIT_PROFILE_WRITE    POST /profile limit. Default "30/minute".
    RATE_LIMIT_API_V1_DEFAULT   /api/v1/* limit when no/unknown API key. Default "60/minute".
    RATE_LIMIT_B2B_STARTER      /api/v1/* limit for "starter" tier keys. Default "60/minute".
    RATE_LIMIT_B2B_GROWTH       /api/v1/* limit for "growth" tier keys. Default "300/minute".
    RATE_LIMIT_B2B_ENTERPRISE   /api/v1/* limit for "enterprise" tier keys. Default "1000/minute".
    B2B_API_KEYS                JSON object mapping API key -> tenant info. Two forms supported:
                                 - Full (recommended; also used for tenant isolation, see
                                   core.security.tenancy): {"key_abc123": {"org_id": "org_acme",
                                   "tier": "starter", "rpm": 60}}.
                                 - Legacy shorthand (tier only, no org_id): {"key_abc123": "starter"}.
                                 Keys not present here fall back to RATE_LIMIT_API_V1_DEFAULT.
"""
from __future__ import annotations

import json
import os
from typing import Callable, Optional

from starlette.requests import Request

from core.anon_session import verify_anon_token

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
except ImportError:  # slowapi optional; rate limiting becomes a no-op (see rate_limit() below)
    Limiter = None

    def get_remote_address(request: Request) -> str:
        return request.client.host if request.client else "unknown"


def _env_limit(name: str, default: str) -> str:
    return os.environ.get(name, "").strip() or default


RATE_LIMIT_CHAT_ANON = _env_limit("RATE_LIMIT_CHAT_ANON", "20/minute")
RATE_LIMIT_CHAT_AUTH = _env_limit("RATE_LIMIT_CHAT_AUTH", "30/minute")
RATE_LIMIT_PROFILE_READ = _env_limit("RATE_LIMIT_PROFILE_READ", "60/minute")
RATE_LIMIT_PROFILE_WRITE = _env_limit("RATE_LIMIT_PROFILE_WRITE", "30/minute")
RATE_LIMIT_API_V1_DEFAULT = _env_limit("RATE_LIMIT_API_V1_DEFAULT", "60/minute")

B2B_TIER_LIMITS = {
    "starter": _env_limit("RATE_LIMIT_B2B_STARTER", "60/minute"),
    "growth": _env_limit("RATE_LIMIT_B2B_GROWTH", "300/minute"),
    "enterprise": _env_limit("RATE_LIMIT_B2B_ENTERPRISE", "1000/minute"),
}

_API_KEY_PREFIX = "apikey:"
_USER_PREFIX = "user:"
_IP_PREFIX = "ip:"


def _load_b2b_api_keys() -> dict:
    """Parse B2B_API_KEYS (JSON object: {api_key: tier}). Returns {} when unset/invalid."""
    raw = os.environ.get("B2B_API_KEYS", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _normalize_api_key_entry(raw) -> dict:
    """
    Normalize a B2B_API_KEYS value to {"org_id", "tier", "rpm"}.
    Accepts the legacy shorthand (a bare tier-name string) or the full object
    form ({"org_id": ..., "tier": ..., "rpm": ...}); unrecognized shapes normalize to all-None.
    """
    if isinstance(raw, str):
        return {"org_id": None, "tier": raw, "rpm": None}
    if isinstance(raw, dict):
        return {"org_id": raw.get("org_id"), "tier": raw.get("tier"), "rpm": raw.get("rpm")}
    return {"org_id": None, "tier": None, "rpm": None}


def get_api_key_entry(api_key: str) -> Optional[dict]:
    """Return the normalized {"org_id", "tier", "rpm"} entry for api_key, or None if unrecognized."""
    raw = _load_b2b_api_keys().get(api_key)
    if raw is None:
        return None
    return _normalize_api_key_entry(raw)


def get_api_key_tier(api_key: str) -> Optional[str]:
    """Return the B2B tier name for api_key ('starter'/'growth'/'enterprise'), or None if unrecognized."""
    entry = get_api_key_entry(api_key)
    tier = entry.get("tier") if entry else None
    return tier if tier in B2B_TIER_LIMITS else None


def rate_limit_key_func(request: Request) -> str:
    """
    slowapi key_func: identifies the caller for rate-limit bucketing.

    Precedence: X-API-Key > Authorization Bearer (verified anon-session user_id) > client IP.
    The prefix on the returned key lets the dynamic-limit callables below
    (chat_rate_limit, api_v1_rate_limit) pick the right tier without
    re-parsing headers.
    """
    api_key = request.headers.get("x-api-key")
    if api_key:
        return f"{_API_KEY_PREFIX}{api_key}"

    auth = request.headers.get("authorization")
    if auth and auth.startswith("Bearer "):
        token = auth[7:].strip()
        user_id = verify_anon_token(token) if token else None
        if user_id:
            return f"{_USER_PREFIX}{user_id}"

    return f"{_IP_PREFIX}{get_remote_address(request)}"


def chat_rate_limit(key: str) -> str:
    """Dynamic /chat/grocery limit: authenticated callers (API key or user token) get a higher cap than anonymous IPs."""
    if key.startswith(_USER_PREFIX) or key.startswith(_API_KEY_PREFIX):
        return RATE_LIMIT_CHAT_AUTH
    return RATE_LIMIT_CHAT_ANON


def api_v1_rate_limit(key: str) -> str:
    """Dynamic /api/v1/* limit: B2B tier resolved from the API key, else the shared default."""
    if key.startswith(_API_KEY_PREFIX):
        api_key = key[len(_API_KEY_PREFIX):]
        tier = get_api_key_tier(api_key)
        if tier:
            return B2B_TIER_LIMITS[tier]
    return RATE_LIMIT_API_V1_DEFAULT


# Shared limiter instance: created once so app.py and core/api/v1/routes.py both
# attach limits to the same limiter (required for slowapi's app.state.limiter wiring).
limiter = Limiter(key_func=rate_limit_key_func) if Limiter is not None else None


def rate_limit(limit_value) -> Callable:
    """Route decorator: apply limiter.limit(limit_value) when slowapi is installed; no-op otherwise.

    limit_value may be a rate-limit string (e.g. "20/minute") or a callable
    like chat_rate_limit/api_v1_rate_limit that takes the resolved key and
    returns a rate-limit string.
    """
    return limiter.limit(limit_value) if limiter else (lambda f: f)
