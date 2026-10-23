"""Uptime monitors probe HEAD /health; GET-only used to 405."""
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_head_health_is_ok():
    r = client.head("/health")
    assert r.status_code == 200
    assert r.content in (b"", b"null") or not r.content


def test_get_health_still_json():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["engine"] == "ike2"
