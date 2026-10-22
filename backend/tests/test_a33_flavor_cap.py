"""A33: class terms like natural flavors must not firm-SAFE diet restrictions."""
from fastapi.testclient import TestClient

from app import app

client = TestClient(app, raise_server_exceptions=False)

_TEXT = (
    "citric acid (to preserve freshness), annatto (color), "
    "cocoa processed with alkali, natural and artificial flavors, color added"
)


def test_a33_natural_flavors_not_safe_on_diet_restrictions():
    for rid in ("vegan", "vegetarian", "jain", "halal"):
        r = client.post(
            "/api/v1/evaluate-product",
            json={"ingredients_text": _TEXT, "restriction_ids": [rid]},
        )
        assert r.status_code == 200, rid
        status = r.json()["verdict"]["status"]
        assert status != "SAFE", (rid, status)


def test_class_terms_spices_seasoning_not_safe():
    text = "water, spices, seasoning"
    for rid in ("vegan", "vegetarian", "jain", "halal"):
        r = client.post(
            "/api/v1/evaluate-product",
            json={"ingredients_text": text, "restriction_ids": [rid]},
        )
        assert r.status_code == 200, rid
        status = r.json()["verdict"]["status"]
        assert status != "SAFE", (rid, status)
