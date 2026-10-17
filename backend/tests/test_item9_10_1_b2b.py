"""Item 9 + 10.1: production key gate, sibling ike2 body, contradictory diets."""
import json

from fastapi.testclient import TestClient

import core.config as config
from app import app

client = TestClient(app)


def test_production_requires_known_api_key(monkeypatch):
    monkeypatch.setattr(config, "PRODUCTION", True)
    monkeypatch.setenv("B2B_API_KEYS", json.dumps({"pilot-key": "starter"}))
    body = {"ingredients": ["water"], "restriction_ids": ["vegan"]}

    missing = client.post("/api/v1/evaluate-compliance", json=body)
    assert missing.status_code == 401

    unknown = client.post(
        "/api/v1/evaluate-compliance",
        json=body,
        headers={"X-API-Key": "not-a-key"},
    )
    assert unknown.status_code == 401

    known = client.post(
        "/api/v1/evaluate-compliance",
        json=body,
        headers={"X-API-Key": "pilot-key"},
    )
    assert known.status_code == 200
    assert known.json()["verdict"]["status"] == "SAFE"

    profile = client.post(
        "/profile",
        json={"user_id": "item9-no-key", "dietary_preference": "Vegan"},
    )
    assert profile.status_code != 401


def test_dev_evaluate_stays_open_without_a_key(monkeypatch):
    monkeypatch.setattr(config, "PRODUCTION", False)
    r = client.post(
        "/api/v1/evaluate-compliance",
        json={"ingredients": ["water"], "restriction_ids": ["vegan"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"]["status"] == "SAFE"
    assert isinstance(body["verdict"], dict)
    assert body["ike2"]["schema_version"] == "ike2.v1"
    assert isinstance(body["ike2"]["verdict"], int)


def test_vegan_and_pescatarian_rejected_on_evaluate_and_profile():
    rejected = client.post(
        "/api/v1/evaluate-compliance",
        json={
            "ingredients": ["water"],
            "restriction_ids": ["vegan", "pescatarian"],
        },
    )
    assert rejected.status_code == 400

    kept = client.post(
        "/api/v1/evaluate-compliance",
        json={
            "ingredients": ["water"],
            "restriction_ids": ["vegan", "peanut_allergy"],
        },
    )
    assert kept.status_code == 200

    profile = client.post(
        "/profile",
        json={
            "user_id": "item10-contradict",
            "dietary_preference": "Vegan",
            "lifestyle": ["pescatarian"],
        },
    )
    assert profile.status_code == 400


def test_catalog_category_keeps_religious_distinct():
    from core.knowledge.ike2.breakdown import restriction_categories

    cats = restriction_categories()
    assert cats["halal"] == "religious"
    assert cats["kosher"] == "religious"
    assert cats["jain"] == "religious"
    assert cats["vegan"] == "lifestyle"
    assert cats["peanut_allergy"] == "allergy"
    assert cats["gluten_free"] == "medical"


def test_breakdown_labels_and_most_severe_headline():
    r = client.post(
        "/api/v1/evaluate-compliance",
        json={
            "ingredients": ["beef", "peanut", "wheat", "water"],
            "restriction_ids": ["vegan", "peanut_allergy", "gluten_free"],
            "include_restriction_matrix": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"]["status"] == "NOT_SAFE"
    rows = {row["restriction_id"]: row for row in body["ike2"]["by_restriction"]}
    assert rows["vegan"]["category"] == "lifestyle"
    assert rows["vegan"]["verdict"] == "NOT_SAFE"
    assert rows["peanut_allergy"]["category"] == "allergy"
    assert rows["peanut_allergy"]["verdict"] == "NOT_SAFE"
    assert rows["gluten_free"]["category"] == "medical"
    assert rows["gluten_free"]["verdict"] == "NOT_SAFE"
    matrix = body["ike2"]["restriction_matrix"]

    def cell(ingredient, restriction):
        hits = [
            row["verdict"]
            for row in matrix
            if row["ingredient"] == ingredient and row["restriction_id"] == restriction
        ]
        assert len(hits) == 1, (ingredient, restriction, matrix)
        return hits[0]

    assert cell("beef", "vegan") == "NOT_SAFE"
    assert cell("beef", "peanut_allergy") == "SAFE"
    assert cell("beef", "gluten_free") == "SAFE"
    assert cell("peanut", "peanut_allergy") == "NOT_SAFE"
    assert cell("peanut", "vegan") == "SAFE"
    assert cell("peanut", "gluten_free") == "SAFE"
    assert cell("wheat", "gluten_free") == "NOT_SAFE"
    assert cell("wheat", "vegan") == "SAFE"
    assert cell("wheat", "peanut_allergy") == "SAFE"
    assert cell("water", "vegan") == "SAFE"
    assert cell("water", "peanut_allergy") == "SAFE"
    assert cell("water", "gluten_free") == "SAFE"
    assert "restriction_matrix" not in client.post(
        "/api/v1/evaluate-compliance",
        json={
            "ingredients": ["water"],
            "restriction_ids": ["vegan"],
        },
    ).json()["ike2"]
