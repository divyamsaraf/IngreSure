"""
Server-issued anonymous session tokens (see docs/auth-and-identity.md).

When ANON_SESSION_SECRET is set, the backend can issue signed tokens that encode
a user_id; clients send the token in Authorization and the backend uses the
embedded identity instead of client-supplied user_id. No JWT dependency:
HMAC-SHA256 signed payload (user_id|expiry_ts).
"""
from __future__ import annotations

import base64
import hmac
import hashlib
import os
import time
from typing import Optional

# Default expiry: 365 days so the same device keeps the same id until token is cleared
ANON_TOKEN_EXPIRY_SECONDS = 365 * 24 * 3600


def _b64_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64_decode(s: str) -> Optional[bytes]:
    try:
        pad = 4 - len(s) % 4
        if pad != 4:
            s += "=" * pad
        return base64.urlsafe_b64decode(s)
    except Exception:
        return None


def _get_secret() -> bytes:
    secret = os.environ.get("ANON_SESSION_SECRET", "").strip().encode("utf-8")
    if not secret:
        return b""
    return secret


def sign_anon_token(user_id: str, expiry_seconds: int = ANON_TOKEN_EXPIRY_SECONDS) -> Optional[str]:
    """Create a signed token containing user_id and expiry. Returns None if ANON_SESSION_SECRET is unset."""
    secret = _get_secret()
    if not secret:
        return None
    expiry_ts = int(time.time()) + expiry_seconds
    payload = f"{user_id}|{expiry_ts}"
    payload_b = payload.encode("utf-8")
    sig = hmac.new(secret, payload_b, hashlib.sha256).digest()
    return f"{_b64_encode(payload_b)}.{_b64_encode(sig)}"


def verify_anon_token(token: str) -> Optional[str]:
    """Verify token and return user_id if valid and not expired; else None."""
    secret = _get_secret()
    if not secret or not token:
        return None
    parts = token.split(".")
    if len(parts) != 2:
        return None
    payload_b = _b64_decode(parts[0])
    sig_b = _b64_decode(parts[1])
    if not payload_b or not sig_b or len(sig_b) != 32:
        return None
    expected = hmac.new(secret, payload_b, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, sig_b):
        return None
    try:
        payload = payload_b.decode("utf-8")
    except Exception:
        return None
    segs = payload.split("|")
    if len(segs) != 2:
        return None
    user_id, expiry_str = segs[0], segs[1]
    try:
        expiry_ts = int(expiry_str)
    except ValueError:
        return None
    if time.time() > expiry_ts:
        return None
    return user_id if user_id else None
