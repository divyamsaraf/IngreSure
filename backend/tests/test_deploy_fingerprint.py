"""Deploy fingerprint on GET /health."""
from fastapi.testclient import TestClient

from app import app
from core.deploy_fingerprint import shipped_schema_version

client = TestClient(app)


def test_health_exposes_deploy_fingerprint():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["engine"] == "ike2"
    assert "git_sha" in body and body["git_sha"]
    assert body["ike2_schema_version"] == shipped_schema_version()
    assert body["ike2_schema_version_shipped"].startswith("20")
    assert "environment" in body
    assert "production" in body
    assert isinstance(body["production"], bool)
    assert "ike2_live_audit" in body
    assert body["ike2_live_audit"]["status"] in ("never", "ok", "stale", "error")


def test_git_sha_prefers_env(monkeypatch):
    monkeypatch.setenv("GIT_SHA", "abc123deadbeef")
    from core import deploy_fingerprint as df

    assert df.git_sha() == "abc123deadbeef"


def test_schema_version_fail_safe_when_db_probe_fails(monkeypatch):
    from core import deploy_fingerprint as df

    monkeypatch.setattr(df, "applied_schema_version", lambda: None)
    shipped = df.shipped_schema_version()
    fp = df.fingerprint()
    assert fp["ike2_schema_version_applied"] is None
    assert fp["ike2_schema_version"] == shipped
    assert fp["ike2_schema_version"] != ""
