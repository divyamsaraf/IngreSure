"""IKE-2 path coverage for /api/v1/evaluate-* (Item 16 Prompt 5/7)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app import app
from core.models.verdict import ComplianceVerdict, VerdictStatus


client = TestClient(app)


def test_evaluate_compliance_serves_ike2(monkeypatch):
    from core.api import v1_evaluate as mod

    ike2 = ComplianceVerdict(
        status=VerdictStatus.SAFE,
        triggered_restrictions=[],
        triggered_ingredients=[],
        uncertain_ingredients=[],
        evidence_tier="standard",
    )
    monkeypatch.setattr(
        mod, "_run_ike2_evaluate_with_flags", lambda *a, **k: (ike2, [])
    )

    r = client.post(
        "/api/v1/evaluate-compliance",
        json={"ingredients": ["water", "salt"], "restriction_ids": ["vegan"]},
    )
    assert r.status_code == 200
    assert r.json()["verdict"]["status"] == "SAFE"


def test_evaluate_product_serves_ike2_contract(monkeypatch):
    from core.api import v1_evaluate as mod

    ike2 = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["dairy_free"],
        triggered_ingredients=["milk"],
    )
    monkeypatch.setattr(
        mod, "_run_ike2_evaluate_with_flags", lambda *a, **k: (ike2, [])
    )

    r = client.post(
        "/api/v1/evaluate-product",
        json={
            "ingredients_text": "Milk, sugar",
            "restriction_ids": ["dairy_free"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "parsed_ingredients" in body
    assert isinstance(body["parsed_ingredients"], list)
    assert len(body["parsed_ingredients"]) >= 1
    v = body["verdict"]
    assert v["status"] == "NOT_SAFE"
    assert "triggered_restrictions" in v
    assert "triggered_ingredients" in v
    assert "uncertain_ingredients" in v
    assert "confidence_score" in v
    assert "evidence_tier" in v


def test_ike2_evaluate_real_path_gelatin_vegan_not_safe():
    """Integration-ish: real IKE-2 pipeline for a clear FAIL case."""
    from core.api import v1_evaluate as mod

    verdict = mod.evaluate_ingredients(["gelatin"], ["vegan"])
    assert verdict.status == VerdictStatus.NOT_SAFE
    assert "vegan" in (verdict.triggered_restrictions or []) or verdict.triggered_ingredients
