"""
Security Phase A: input sanitization, CORS production guard, profile list
validation, and rate-limit caller-key extraction.
"""
import json
import os

import pytest
from starlette.requests import Request

from core.security.cors_guard import validate_cors_origins
from core.security.input_sanitize import (
    PROFILE_LIST_ITEM_MAX_LENGTH,
    PROFILE_LIST_MAX_ITEMS,
    sanitize_chat_query,
    validate_profile_lists,
)
from core.security.rate_limit import (
    B2B_TIER_LIMITS,
    RATE_LIMIT_API_V1_DEFAULT,
    RATE_LIMIT_CHAT_ANON,
    RATE_LIMIT_CHAT_AUTH,
    api_v1_rate_limit,
    chat_rate_limit,
    rate_limit_key_func,
)
from core.anon_session import sign_anon_token


def _make_request(headers=None, client_host="127.0.0.1"):
    headers = headers or []
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers],
        "client": (client_host, 12345),
    }
    return Request(scope)


# --- sanitize_chat_query ---

def test_sanitize_strips_nul_and_control_chars():
    assert sanitize_chat_query("hello\x00world\x01\x02") == "helloworld"


def test_sanitize_keeps_newline_and_tab():
    raw = "line1\nline2\tindented"
    assert sanitize_chat_query(raw) == raw


def test_sanitize_collapses_extreme_inline_whitespace():
    raw = "hello" + " " * 50 + "world"
    assert sanitize_chat_query(raw) == "hello world"


def test_sanitize_collapses_extreme_blank_lines():
    raw = "hello" + "\n" * 20 + "world"
    out = sanitize_chat_query(raw)
    assert "\n" * 4 not in out
    assert "hello" in out and "world" in out


def test_sanitize_empty_string_unchanged():
    assert sanitize_chat_query("") == ""


def test_sanitize_normal_text_unchanged():
    raw = "Does this contain milk or peanuts?"
    assert sanitize_chat_query(raw) == raw


# --- CORS production guard ---

def test_cors_guard_noop_in_dev_even_with_wildcard_or_empty():
    validate_cors_origins(["*"], is_production=False)
    validate_cors_origins([], is_production=False)


def test_cors_guard_raises_on_empty_origins_in_production():
    with pytest.raises(RuntimeError):
        validate_cors_origins([], is_production=True)


def test_cors_guard_raises_on_wildcard_in_production():
    with pytest.raises(RuntimeError):
        validate_cors_origins(["*"], is_production=True)


def test_cors_guard_allows_specific_origins_in_production():
    validate_cors_origins(["https://app.example.com"], is_production=True)


# --- Profile list validation ---

def test_validate_profile_lists_accepts_none_and_empty():
    validate_profile_lists(None, None)
    validate_profile_lists([], [])


def test_validate_profile_lists_accepts_valid_input():
    validate_profile_lists(["peanuts", "dairy"], ["vegan"])


def test_validate_profile_lists_rejects_too_many_allergens():
    with pytest.raises(ValueError):
        validate_profile_lists(["a"] * (PROFILE_LIST_MAX_ITEMS + 1), None)


def test_validate_profile_lists_rejects_too_many_lifestyle_items():
    with pytest.raises(ValueError):
        validate_profile_lists(None, ["a"] * (PROFILE_LIST_MAX_ITEMS + 1))


def test_validate_profile_lists_rejects_oversized_item():
    with pytest.raises(ValueError):
        validate_profile_lists(None, ["x" * (PROFILE_LIST_ITEM_MAX_LENGTH + 1)])


def test_validate_profile_lists_allows_max_boundary():
    validate_profile_lists(["a"] * PROFILE_LIST_MAX_ITEMS, ["x" * PROFILE_LIST_ITEM_MAX_LENGTH])


# --- Rate-limit key extraction ---

def test_rate_limit_key_prefers_api_key_over_everything():
    req = _make_request(headers=[("X-API-Key", "b2b-key-123")], client_host="203.0.113.5")
    assert rate_limit_key_func(req) == "apikey:b2b-key-123"


def test_rate_limit_key_prefers_bearer_user_over_ip():
    os.environ["ANON_SESSION_SECRET"] = "test-secret-at-least-32-characters-long"
    try:
        token = sign_anon_token("anon-abc123def456")
        req = _make_request(headers=[("Authorization", f"Bearer {token}")], client_host="203.0.113.5")
        assert rate_limit_key_func(req) == "user:anon-abc123def456"
    finally:
        os.environ.pop("ANON_SESSION_SECRET", None)


def test_rate_limit_key_falls_back_to_ip_when_no_key_or_token():
    req = _make_request(client_host="203.0.113.5")
    assert rate_limit_key_func(req) == "ip:203.0.113.5"


def test_rate_limit_key_falls_back_to_ip_when_bearer_token_invalid():
    os.environ.pop("ANON_SESSION_SECRET", None)
    req = _make_request(headers=[("Authorization", "Bearer not-a-real-token")], client_host="198.51.100.1")
    assert rate_limit_key_func(req) == "ip:198.51.100.1"


def test_chat_rate_limit_anon_vs_authenticated():
    assert chat_rate_limit("ip:1.2.3.4") == RATE_LIMIT_CHAT_ANON
    assert chat_rate_limit("user:anon-xyz") == RATE_LIMIT_CHAT_AUTH
    assert chat_rate_limit("apikey:some-key") == RATE_LIMIT_CHAT_AUTH


def test_api_v1_rate_limit_uses_b2b_tier_from_api_key():
    os.environ["B2B_API_KEYS"] = json.dumps({"growth-key": "growth", "ent-key": "enterprise"})
    try:
        assert api_v1_rate_limit("apikey:growth-key") == B2B_TIER_LIMITS["growth"]
        assert api_v1_rate_limit("apikey:ent-key") == B2B_TIER_LIMITS["enterprise"]
    finally:
        os.environ.pop("B2B_API_KEYS", None)


def test_api_v1_rate_limit_falls_back_to_default_for_unknown_key():
    os.environ.pop("B2B_API_KEYS", None)
    assert api_v1_rate_limit("apikey:unknown-key") == RATE_LIMIT_API_V1_DEFAULT
    assert api_v1_rate_limit("ip:1.2.3.4") == RATE_LIMIT_API_V1_DEFAULT
