"""Swallowed exceptions are UNCERTAIN with degraded=true, logged and counted."""
from fastapi.testclient import TestClient

from app import app
from core.models.verdict import VerdictStatus

client = TestClient(app, raise_server_exceptions=False)


def test_parser_exception_sets_degraded_true(monkeypatch):
    from core.api.v1 import routes as routes_mod
    from core import degraded as deg

    before = deg.snapshot()["count"]

    def boom(_text):
        raise RuntimeError("dictionary changed size during iteration")

    monkeypatch.setattr(routes_mod, "preprocess_ingredients_to_strings", boom)
    r = client.post(
        "/api/v1/evaluate-product",
        json={"ingredients_text": "water, salt", "restriction_ids": ["vegan"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"]["status"] == VerdictStatus.UNCERTAIN.value
    assert body["verdict"]["degraded"] is True
    assert deg.snapshot()["count"] == before + 1
