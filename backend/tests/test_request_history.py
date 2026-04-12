"""Unit tests for request_history helpers (no Supabase required)."""

from core.stream_tags import INGREDIENT_AUDIT_TAG, PROFILE_UPDATE_TAG
from core.request_history import strip_stream_tags_for_history, truncate_output


def test_strip_stream_tags_expands_audit_and_drops_profile_tag():
    audit_json = (
        '{"summary":"0 Safe, 1 Avoid, 0 Depends",'
        '"groups":[{"status":"avoid","items":[{"name":"Potato Chips"}]}],'
        '"explanation":"Based on your Jain diet, not suitable."}'
    )
    raw = (
        f"Hello\n\n{INGREDIENT_AUDIT_TAG}{audit_json}{INGREDIENT_AUDIT_TAG}"
        f"\n\n{PROFILE_UPDATE_TAG}{{\"user_id\":\"x\"}}{PROFILE_UPDATE_TAG}"
    )
    out = strip_stream_tags_for_history(raw)
    assert INGREDIENT_AUDIT_TAG not in out
    assert PROFILE_UPDATE_TAG not in out
    assert "Hello" in out
    assert "0 Safe, 1 Avoid, 0 Depends" in out
    assert "Avoid (1)" in out
    assert "Potato Chips" in out
    assert "Based on your Jain diet" in out


def test_truncate_output_appends_ellipsis():
    long = "a" * 10000
    cap_env_ignored = truncate_output(long)
    assert len(cap_env_ignored) < len(long)
    assert "truncated" in cap_env_ignored.lower() or "…" in cap_env_ignored


def test_request_history_writes_enabled_respects_env(monkeypatch):
    from core.request_history import request_history_writes_enabled

    monkeypatch.delenv("REQUEST_HISTORY_ENABLED", raising=False)
    assert request_history_writes_enabled() is True

    monkeypatch.setenv("REQUEST_HISTORY_ENABLED", "false")
    assert request_history_writes_enabled() is False

    monkeypatch.setenv("REQUEST_HISTORY_ENABLED", "0")
    assert request_history_writes_enabled() is False

    monkeypatch.setenv("REQUEST_HISTORY_ENABLED", "on")
    assert request_history_writes_enabled() is True
