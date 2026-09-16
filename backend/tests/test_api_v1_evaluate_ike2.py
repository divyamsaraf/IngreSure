"""IKE-2 path coverage for /api/v1/evaluate-* (Item 16 Prompt 5).

These assert the IKE-2 evaluation path for both endpoints. Served behavior under
default ``shadow`` still comes from legacy; ``primary`` serves IKE-2. Tests
force mode explicitly so they do not depend on ambient ``.env``.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app import app
from core.models.verdict import ComplianceVerdict, VerdictStatus


client = TestClient(app)


def test_evaluate_compliance_shadow_serves_legacy_shape(monkeypatch):
    monkeypatch.setenv("IKE2_MODE", "shadow")
    # Force re-read via get_ike2_mode in evaluate path (reads env each call).
    from core.api import v1_evaluate as mod

    served = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["vegan"],
        triggered_ingredients=["gelatin"],
    )
    ike2 = ComplianceVerdict(status=VerdictStatus.NOT_SAFE, triggered_restrictions=["vegan"])
    monkeypatch.setattr(mod, "_run_legacy_evaluate", lambda *a, **k: served)
    monkeypatch.setattr(mod, "_run_ike2_evaluate", lambda *a, **k: ike2)
    logged = []
    monkeypatch.setattr(mod, "_log_shadow_diff", lambda *a, **k: logged.append(a))

    r = client.post(
        "/api/v1/evaluate-compliance",
        json={"ingredients": ["gelatin"], "restriction_ids": ["vegan"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert "verdict" in body
    assert body["verdict"]["status"] == "NOT_SAFE"
    assert body["verdict"]["triggered_ingredients"] == ["gelatin"]
    assert logged  # shadow computed both sides


def test_evaluate_compliance_primary_serves_ike2(monkeypatch):
    monkeypatch.setenv("IKE2_MODE", "primary")
    from core.api import v1_evaluate as mod

    ike2 = ComplianceVerdict(
        status=VerdictStatus.SAFE,
        triggered_restrictions=[],
        triggered_ingredients=[],
        uncertain_ingredients=[],
        evidence_tier="standard",
    )
    monkeypatch.setattr(mod, "_run_ike2_evaluate", lambda *a, **k: ike2)
    monkeypatch.setattr(mod, "_schedule_primary_legacy_diff", lambda *a, **k: None)
    monkeypatch.setattr(
        mod,
        "_run_legacy_evaluate",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("legacy must not serve in primary")),
    )

    r = client.post(
        "/api/v1/evaluate-compliance",
        json={"ingredients": ["water", "salt"], "restriction_ids": ["vegan"]},
    )
    assert r.status_code == 200
    assert r.json()["verdict"]["status"] == "SAFE"


def test_evaluate_product_shadow_parses_then_evaluates(monkeypatch):
    monkeypatch.setenv("IKE2_MODE", "shadow")
    from core.api import v1_evaluate as mod

    served = ComplianceVerdict(status=VerdictStatus.UNCERTAIN)
    monkeypatch.setattr(mod, "_run_legacy_evaluate", lambda *a, **k: served)
    monkeypatch.setattr(mod, "_run_ike2_evaluate", lambda *a, **k: served)
    monkeypatch.setattr(mod, "_log_shadow_diff", lambda *a, **k: None)

    r = client.post(
        "/api/v1/evaluate-product",
        json={
            "ingredients_text": "Ingredients: Water, Salt.",
            "restriction_ids": ["vegan"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "parsed_ingredients" in body
    assert isinstance(body["parsed_ingredients"], list)
    assert len(body["parsed_ingredients"]) >= 1
    assert body["verdict"]["status"] == "UNCERTAIN"


def test_evaluate_product_primary_serves_ike2_contract(monkeypatch):
    monkeypatch.setenv("IKE2_MODE", "primary")
    from core.api import v1_evaluate as mod

    ike2 = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["dairy_free"],
        triggered_ingredients=["milk"],
    )
    monkeypatch.setattr(mod, "_run_ike2_evaluate", lambda *a, **k: ike2)
    monkeypatch.setattr(mod, "_schedule_primary_legacy_diff", lambda *a, **k: None)

    r = client.post(
        "/api/v1/evaluate-product",
        json={
            "ingredients_text": "Milk, sugar",
            "restriction_ids": ["dairy_free"],
        },
    )
    assert r.status_code == 200
    v = r.json()["verdict"]
    assert v["status"] == "NOT_SAFE"
    assert "triggered_restrictions" in v
    assert "triggered_ingredients" in v
    assert "uncertain_ingredients" in v
    assert "confidence_score" in v
    assert "evidence_tier" in v


def test_ike2_evaluate_real_path_gelatin_vegan_not_safe(monkeypatch):
    """Integration-ish: real IKE-2 pipeline for a clear FAIL case (primary mode)."""
    monkeypatch.setenv("IKE2_MODE", "primary")
    from core.api import v1_evaluate as mod

    monkeypatch.setattr(mod, "_schedule_primary_legacy_diff", lambda *a, **k: None)

    verdict = mod.evaluate_ingredients(["gelatin"], ["vegan"])
    assert verdict.status == VerdictStatus.NOT_SAFE
    assert "vegan" in (verdict.triggered_restrictions or []) or verdict.triggered_ingredients
