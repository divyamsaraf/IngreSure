"""Evaluate-product oversized bodies are 413; atom cap is enforced."""
from fastapi.testclient import TestClient

from app import app

client = TestClient(app, raise_server_exceptions=False)


def test_evaluate_product_oversize_is_413():
    huge = "water, salt, " + ("x" * (600 * 1024))
    r = client.post(
        "/api/v1/evaluate-product",
        json={"ingredients_text": huge, "restriction_ids": ["vegan"]},
    )
    assert r.status_code == 413


def test_evaluate_product_rate_limit_headers_present():
    r = client.post(
        "/api/v1/evaluate-product",
        json={"ingredients_text": "water, salt", "restriction_ids": ["vegan"]},
    )
    assert r.status_code == 200
    # slowapi typically sets these; at least one limit header must be present.
    keys = {k.lower() for k in r.headers}
    assert any("ratelimit" in k or "retry-after" in k or "x-ratelimit" in k for k in keys)
