"""
Tenant isolation (Security Phase B): core.security.tenancy.resolve_caller, profile storage
namespacing, and the /profile GET/POST endpoints' enforcement.

Covers:
  - resolve_caller: B2B API key (X-API-Key / Authorization Bearer) -> org-scoped caller;
    anon-session token -> user-scoped caller; neither -> no identity.
  - profile_storage: org-namespaced keys, legacy bare-key read fallback (non-org only).
  - /profile endpoints: user A's token cannot read/write user B's profile (403);
    API key org A cannot read org B's profile data (even for the same raw user_id).
"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from core.anon_session import sign_anon_token


def _make_request(headers=None):
    headers = headers or []
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.fixture()
def b2b_keys(monkeypatch):
    """Two B2B orgs with distinct API keys (full schema: org_id + tier + rpm)."""
    keys = {
        "sk_live_org_a": {"org_id": "org_a", "tier": "starter", "rpm": 60},
        "sk_live_org_b": {"org_id": "org_b", "tier": "growth", "rpm": 300},
    }
    monkeypatch.setenv("B2B_API_KEYS", json.dumps(keys))
    return keys


@pytest.fixture()
def anon_secret(monkeypatch):
    monkeypatch.setenv("ANON_SESSION_SECRET", "test-tenancy-secret-at-least-32-chars")


@pytest.fixture()
def temp_profiles_path():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "profiles.json"
        with patch("core.profile_storage._PROFILES_PATH", path):
            yield path


# --- resolve_caller unit tests ---

def test_resolve_caller_returns_no_identity_when_nothing_present():
    from core.security.tenancy import resolve_caller
    caller = resolve_caller(_make_request())
    assert caller.org_id is None
    assert caller.user_id is None
    assert caller.is_b2b is False


def test_resolve_caller_x_api_key_header_resolves_org(b2b_keys):
    from core.security.tenancy import resolve_caller
    req = _make_request(headers=[("X-API-Key", "sk_live_org_a")])
    caller = resolve_caller(req)
    assert caller.org_id == "org_a"
    assert caller.tier == "starter"
    assert caller.api_key_id == "sk_live_org_a"
    assert caller.user_id is None
    assert caller.is_b2b is True


def test_resolve_caller_bearer_api_key_resolves_org(b2b_keys):
    """API key may also be sent via Authorization: Bearer <key> (not just X-API-Key)."""
    from core.security.tenancy import resolve_caller
    req = _make_request(headers=[("Authorization", "Bearer sk_live_org_b")])
    caller = resolve_caller(req)
    assert caller.org_id == "org_b"
    assert caller.tier == "growth"


def test_resolve_caller_x_user_id_scopes_end_user_within_org(b2b_keys):
    from core.security.tenancy import resolve_caller
    req = _make_request(headers=[("X-API-Key", "sk_live_org_a"), ("X-User-Id", "customer42")])
    caller = resolve_caller(req)
    assert caller.org_id == "org_a"
    assert caller.user_id == "customer42"


def test_resolve_caller_falls_back_to_anon_token_when_key_unrecognized(b2b_keys, anon_secret):
    from core.security.tenancy import resolve_caller
    token = sign_anon_token("anon-abc123def456")
    req = _make_request(headers=[("Authorization", f"Bearer {token}")])
    caller = resolve_caller(req)
    assert caller.org_id is None
    assert caller.user_id == "anon-abc123def456"


def test_resolve_caller_invalid_bearer_token_yields_no_identity():
    from core.security.tenancy import resolve_caller
    req = _make_request(headers=[("Authorization", "Bearer not-a-real-token")])
    caller = resolve_caller(req)
    assert caller.org_id is None
    assert caller.user_id is None


# --- profile_storage namespacing ---

def test_profile_storage_org_namespaced_keys_are_isolated(temp_profiles_path):
    from core.profile_storage import save_profile, get_profile
    from core.models.user_profile import UserProfile

    save_profile(UserProfile(user_id="shared_id", dietary_preference="Vegan"), org_id="org_a")
    save_profile(UserProfile(user_id="shared_id", dietary_preference="Jain"), org_id="org_b")

    assert get_profile("shared_id", org_id="org_a").dietary_preference == "Vegan"
    assert get_profile("shared_id", org_id="org_b").dietary_preference == "Jain"
    # No org context (e.g. legacy/anon caller) must not see either org's namespaced data.
    assert get_profile("shared_id") is None


def test_profile_storage_legacy_bare_key_read_fallback(temp_profiles_path):
    """Pre-namespacing data (bare user_id key) is still readable when no org_id is given."""
    temp_profiles_path.write_text(json.dumps({"legacy_user": {"dietary_preference": "Halal", "allergens": [], "lifestyle": []}}))
    from core.profile_storage import get_profile
    profile = get_profile("legacy_user")
    assert profile is not None
    assert profile.dietary_preference == "Halal"


def test_profile_storage_org_lookup_does_not_fall_back_to_bare_key(temp_profiles_path):
    """Isolation: an org-scoped lookup must never fall back to a bare (non-namespaced) key."""
    temp_profiles_path.write_text(json.dumps({"shared_id": {"dietary_preference": "Halal", "allergens": [], "lifestyle": []}}))
    from core.profile_storage import get_profile
    assert get_profile("shared_id", org_id="org_a") is None


def test_profile_storage_new_writes_use_namespaced_key_not_bare(temp_profiles_path):
    from core.profile_storage import save_profile
    from core.models.user_profile import UserProfile
    save_profile(UserProfile(user_id="new_user", dietary_preference="Vegan"))
    data = json.loads(temp_profiles_path.read_text())
    assert "user:new_user" in data
    assert "new_user" not in data


# --- /profile endpoint enforcement ---

def test_get_profile_token_user_cannot_read_other_users_profile(anon_secret, temp_profiles_path):
    from app import app
    client = TestClient(app)
    token_a = sign_anon_token("user-a")

    client.post(
        "/profile",
        json={"user_id": "user-b", "dietary_preference": "Jain", "allergens": [], "lifestyle": []},
    )
    r = client.get("/profile/user-b", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 403


def test_post_profile_token_user_cannot_write_other_users_profile(anon_secret, temp_profiles_path):
    from app import app
    client = TestClient(app)
    token_a = sign_anon_token("user-a")

    r = client.post(
        "/profile",
        json={"user_id": "user-b", "dietary_preference": "Jain", "allergens": [], "lifestyle": []},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r.status_code == 403


def test_profile_token_user_can_read_and_write_own_profile(anon_secret, temp_profiles_path):
    from app import app
    client = TestClient(app)
    token_a = sign_anon_token("user-a")

    r_post = client.post(
        "/profile",
        json={"user_id": "user-a", "dietary_preference": "Vegan", "allergens": [], "lifestyle": []},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r_post.status_code == 200
    assert r_post.json()["profile"]["dietary_preference"] == "Vegan"

    r_get = client.get("/profile/user-a", headers={"Authorization": f"Bearer {token_a}"})
    assert r_get.status_code == 200
    assert r_get.json()["dietary_preference"] == "Vegan"


def test_get_profile_without_any_auth_still_works_legacy_behaviour(temp_profiles_path):
    """Documented legacy behaviour (docs/auth-and-identity.md): with no server-verified
    identity (no token, no API key), the client-supplied user_id is trusted as before."""
    from app import app
    client = TestClient(app)
    r = client.get("/profile/anonymous-no-auth-user")
    assert r.status_code == 200
    assert r.json()["user_id"] == "anonymous-no-auth-user"


def test_b2b_api_key_org_a_cannot_read_org_b_profile(b2b_keys, temp_profiles_path):
    from app import app
    client = TestClient(app)

    r_post = client.post(
        "/profile",
        json={"user_id": "shared-end-user", "dietary_preference": "Jain", "allergens": [], "lifestyle": []},
        headers={"X-API-Key": "sk_live_org_a"},
    )
    assert r_post.status_code == 200
    assert r_post.json()["profile"]["dietary_preference"] == "Jain"

    # Same end-user id, but authenticated as org_b -> must not see org_a's data.
    r_get_org_b = client.get(
        "/profile/shared-end-user",
        headers={"X-API-Key": "sk_live_org_b"},
    )
    assert r_get_org_b.status_code == 200
    assert r_get_org_b.json()["dietary_preference"] == "No rules"  # default, not org_a's "Jain"

    # org_a reading its own end-user back sees the real data.
    r_get_org_a = client.get(
        "/profile/shared-end-user",
        headers={"X-API-Key": "sk_live_org_a"},
    )
    assert r_get_org_a.status_code == 200
    assert r_get_org_a.json()["dietary_preference"] == "Jain"


def test_b2b_api_key_with_x_user_id_overrides_path_user_id(b2b_keys, temp_profiles_path):
    from app import app
    client = TestClient(app)

    r_post = client.post(
        "/profile",
        json={"user_id": "placeholder", "dietary_preference": "Halal", "allergens": [], "lifestyle": []},
        headers={"X-API-Key": "sk_live_org_a", "X-User-Id": "real-end-user"},
    )
    assert r_post.status_code == 200

    r_get = client.get(
        "/profile/placeholder",
        headers={"X-API-Key": "sk_live_org_a", "X-User-Id": "real-end-user"},
    )
    assert r_get.status_code == 200
    assert r_get.json()["dietary_preference"] == "Halal"
