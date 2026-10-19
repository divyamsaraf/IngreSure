"""Raw-string hazard sweep + parse-quality ceiling (product-level backstops)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.seam import ComplianceInput, to_compliance_input
from core.knowledge.ike2.verdict import Verdict
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.resolver import resolve
from core.normalization.parser import flatten_ingredients
from core.parsing.parse_quality import assess_parse_quality
from core.parsing.hazard_lexicon import hazard_hits_in_text, label_text_hazard_inputs


def _profile(*rids: str, severity: str = "medical"):
    return SimpleNamespace(restrictions={r: severity for r in rids})


def _atoms_to_inputs(atoms: list[str]):
    return [to_compliance_input(resolve(a, None), query_atom=a) for a in atoms]


def test_raw_sweep_adds_peanut_when_parse_drops_it():
    """Product-level OR: raw PEANUTS (49.5%) must Avoid peanut_allergy even if atoms miss."""
    # Simulate a lost atom path: evaluate only honey, but raw still has peanuts.
    raw = "PEANUTS (49.5%), honey, salt"
    inputs = _atoms_to_inputs(["honey", "salt"])
    rules = rules_module.seeded_rules()
    before = evaluate(inputs, _profile("peanut_allergy"), rules)
    assert before.verdict == Verdict.SAFE
    after = evaluate(inputs, _profile("peanut_allergy"), rules, raw_label=raw)
    assert after.verdict == Verdict.FAIL
    assert any("label text" in (c or "") for c in after.matched_contains) or any(
        "label text" in str(k) for k in after.breakdown
    )


def test_raw_sweep_respects_gluten_free_negation():
    raw = "rice flour, corn starch. Gluten-free."
    inputs = _atoms_to_inputs(["rice flour", "corn starch"])
    rules = rules_module.seeded_rules()
    result = evaluate(inputs, _profile("gluten_free"), rules, raw_label=raw)
    assert result.verdict == Verdict.SAFE
    assert "gluten" not in hazard_hits_in_text(raw)


def test_raw_sweep_contains_footnote_soy():
    raw = "water, salt. Contains: soy."
    # Atoms without soy (footnote lost)
    inputs = _atoms_to_inputs(["water", "salt"])
    rules = rules_module.seeded_rules()
    result = evaluate(inputs, _profile("soy_allergy"), rules, raw_label=raw)
    assert result.verdict == Verdict.FAIL


def test_parse_quality_truncation_caps_safe_at_uncertain():
    raw = "wheat flour, sugar, vegetable oil ("
    atoms = flatten_ingredients(raw)
    q = assess_parse_quality(raw, atoms)
    assert not q.ok
    assert "truncation" in q.reasons or "unbalanced_parentheses" in q.reasons
    inputs = _atoms_to_inputs(["sugar"] if "sugar" in atoms else atoms or ["sugar"])
    # Force a clean SAFE atom set so ceiling is the only non-SAFE signal
    inputs = [
        ComplianceInput(
            canonical_name="sugar",
            flags={},
            knowledge_state="VERIFIED",
            trusted=True,
            alcohol_role=None,
            verdict_cap=None,
            trace=False,
        )
    ]
    rules = rules_module.seeded_rules()
    result = evaluate(
        inputs, _profile("peanut_allergy"), rules, raw_label=raw, parsed_atoms=atoms
    )
    assert result.verdict == Verdict.UNCERTAIN
    assert any("parse_quality" in c for c in result.caution_reasons)


def test_parse_quality_does_not_downgrade_fail():
    raw = "PEANUTS (49.5%), honey ("
    inputs = _atoms_to_inputs(["peanuts", "honey"])
    rules = rules_module.seeded_rules()
    result = evaluate(
        inputs,
        _profile("peanut_allergy"),
        rules,
        raw_label=raw,
        parsed_atoms=flatten_ingredients(raw),
    )
    assert result.verdict == Verdict.FAIL


def test_label_text_hazard_inputs_attribution():
    hits = label_text_hazard_inputs("Contains: Eggs, Almonds.")
    names = {h.canonical_name for h in hits}
    assert "label text" in names
    flags_union = {}
    for h in hits:
        flags_union.update({k: v for k, v in h.flags.items() if v})
    assert flags_union.get("egg_source") is True
    assert flags_union.get("tree_nut_source") is True


def test_may_contain_clause_is_trace_not_definite():
    hits = label_text_hazard_inputs("rice flour, salt. May contain: soy.")
    assert hits
    soy = [h for h in hits if h.flags.get("soy_source")]
    assert soy and all(h.may_contain for h in soy)


def test_http_evaluate_product_truncated_peanuts_not_safe():
    """Real route: truncated PEANUTS (49.5% → NOT_SAFE for peanut_allergy."""
    from fastapi.testclient import TestClient

    from app import app

    client = TestClient(app)
    r = client.post(
        "/api/v1/evaluate-product",
        json={
            "ingredients_text": "PEANUTS (49.5%, honey, salt",
            "restriction_ids": ["peanut_allergy"],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["verdict"]["status"] == "NOT_SAFE"
