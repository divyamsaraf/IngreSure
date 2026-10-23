"""L3 API contract / property tests for POST /api/v1/evaluate-product."""
from __future__ import annotations

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from app import app
from core.models.verdict import VerdictStatus

client = TestClient(app, raise_server_exceptions=False)


def test_empty_restriction_ids_is_422():
    r = client.post(
        "/api/v1/evaluate-product",
        json={"ingredients_text": "water, salt", "restriction_ids": []},
    )
    assert r.status_code == 422


def test_unknown_atom_is_uncertain():
    r = client.post(
        "/api/v1/evaluate-product",
        json={
            "ingredients_text": "zzzx_unknown_l3_atom_xyz",
            "restriction_ids": ["vegan"],
        },
    )
    assert r.status_code == 200, r.text[:400]
    assert r.json()["verdict"]["status"] == VerdictStatus.UNCERTAIN.value


def test_peanut_plus_peanut_allergy_is_not_safe():
    r = client.post(
        "/api/v1/evaluate-product",
        json={
            "ingredients_text": "peanuts, salt",
            "restriction_ids": ["peanut_allergy"],
        },
    )
    assert r.status_code == 200, r.text[:400]
    assert r.json()["verdict"]["status"] == VerdictStatus.NOT_SAFE.value


@given(text=st.text(max_size=80))
@settings(max_examples=25, deadline=None)
def test_property_empty_restriction_ids_always_422(text):
    r = client.post(
        "/api/v1/evaluate-product",
        json={"ingredients_text": text or "x", "restriction_ids": []},
    )
    assert r.status_code == 422
