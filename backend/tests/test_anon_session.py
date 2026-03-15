"""Tests for server-issued anonymous session (GET /anon-session, token sign/verify)."""
import os
import pytest
from fastapi.testclient import TestClient


def test_anon_session_returns_user_id_and_token_when_secret_set():
    """When ANON_SESSION_SECRET is set, GET /anon-session returns user_id and a non-null token."""
    os.environ["ANON_SESSION_SECRET"] = "test-secret-at-least-32-characters-long"
    try:
        from app import app
        client = TestClient(app)
        r = client.get("/anon-session")
        assert r.status_code == 200
        data = r.json()
        assert "user_id" in data
        assert data["user_id"].startswith("anon-")
        assert len(data["user_id"]) == 17  # anon- + 12 hex
        assert "token" in data
        assert data["token"] is not None
        assert isinstance(data["token"], str)
    finally:
        os.environ.pop("ANON_SESSION_SECRET", None)


def test_anon_session_returns_user_id_when_secret_unset():
    """When ANON_SESSION_SECRET is unset, GET /anon-session still returns user_id; token is null."""
    os.environ.pop("ANON_SESSION_SECRET", None)
    from app import app
    client = TestClient(app)
    r = client.get("/anon-session")
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"].startswith("anon-")
    assert data.get("token") is None


def test_verify_token_roundtrip():
    """sign_anon_token and verify_anon_token roundtrip when secret is set."""
    os.environ["ANON_SESSION_SECRET"] = "roundtrip-secret-at-least-32-chars"
    try:
        from core.anon_session import sign_anon_token, verify_anon_token
        user_id = "anon-abc123def456"
        token = sign_anon_token(user_id)
        assert token is not None
        out = verify_anon_token(token)
        assert out == user_id
        assert verify_anon_token("bad.token") is None
        assert verify_anon_token("") is None
    finally:
        os.environ.pop("ANON_SESSION_SECRET", None)
