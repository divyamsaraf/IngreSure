"""
Tenant/caller identity resolution for B2B API partners and anonymous/token consumer users.

B2B_API_KEYS env var (JSON; shared with core.security.rate_limit, see that module's
docstring for the legacy shorthand form): maps an API key to its tenant info, e.g.

    {"sk_live_xxx": {"org_id": "org_acme", "tier": "starter", "rpm": 60}}

Caller resolution precedence (mirrors core.security.rate_limit.rate_limit_key_func):
    1. X-API-Key header, or Authorization: Bearer <key>, matching a B2B_API_KEYS entry
       -> org-scoped caller. The end-user within that org is taken from the optional
       X-User-Id header (a B2B backend calling on behalf of one of its own users).
    2. Authorization: Bearer <token>, verified as a signed anon-session token
       (core.anon_session) -> user-scoped caller.
    3. Neither -> caller with no server-verified identity (org_id=None, user_id=None).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from starlette.requests import Request

from core.anon_session import verify_anon_token
from core.security.rate_limit import get_api_key_entry


@dataclass(frozen=True)
class CallerContext:
    """Resolved caller identity for the current request."""
    org_id: Optional[str] = None
    user_id: Optional[str] = None
    api_key_id: Optional[str] = None
    tier: Optional[str] = None

    @property
    def is_b2b(self) -> bool:
        return self.org_id is not None


def _extract_api_key_candidate(request: Request) -> Optional[str]:
    key = request.headers.get("x-api-key")
    if key and key.strip():
        return key.strip()
    auth = request.headers.get("authorization")
    if auth and auth.startswith("Bearer "):
        token = auth[7:].strip()
        return token or None
    return None


def _extract_bearer_token(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization")
    if auth and auth.startswith("Bearer "):
        token = auth[7:].strip()
        return token or None
    return None


def resolve_caller(request: Request) -> CallerContext:
    """Resolve the calling identity for a request. See module docstring for precedence."""
    candidate_key = _extract_api_key_candidate(request)
    if candidate_key:
        entry = get_api_key_entry(candidate_key)
        if entry and entry.get("org_id"):
            end_user_id = request.headers.get("x-user-id")
            return CallerContext(
                org_id=str(entry["org_id"]),
                user_id=str(end_user_id).strip() if end_user_id and end_user_id.strip() else None,
                api_key_id=candidate_key,
                tier=entry.get("tier"),
            )

    token = _extract_bearer_token(request)
    if token:
        user_id = verify_anon_token(token)
        if user_id:
            return CallerContext(user_id=user_id)

    return CallerContext()
