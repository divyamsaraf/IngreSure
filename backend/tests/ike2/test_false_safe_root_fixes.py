"""Regressions for principal-engineer false-Safe findings."""
from types import SimpleNamespace

from core.bridge import profile_to_restriction_ids, run_new_engine_chat
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.seam import ComplianceInput
from core.knowledge.ike2.verdict import to_external
from core.response_composer import build_ingredient_audit_payload


def _bucket(diet: str, atom: str) -> str:
    profile = {"dietary_preference": diet, "allergens": [], "lifestyle": []}
    rids = profile_to_restriction_ids(profile)
    v = run_new_engine_chat([atom], restriction_ids=rids, use_api_fallback=False)
    a = build_ingredient_audit_payload(v, SimpleNamespace(**profile), [atom])
    for g in a["groups"]:
        if g.get("items"):
            return g["status"]
    return "missing"


def test_glycerin_uncertainty_never_safe_for_religious_diets():
    """Uncertainty allowlist used to miss mono_diglycerides → false Safe."""
    for diet in ("Jain", "Halal", "Kosher", "Vegan", "Hindu Vegetarian"):
        assert _bucket(diet, "glycerin") != "safe", diet
        assert _bucket(diet, "glycerol") != "safe", diet


def test_explicit_null_flag_is_uncertain_not_safe():
    """NULL peanut_source must not be treated as verified-absent."""
    ci = ComplianceInput(
        canonical_name="mystery_spread",
        flags={"peanut_source": None},
        knowledge_state="AUTO_CLASSIFIED",
        trusted=True,
        alcohol_role="none",
        verdict_cap=None,
        trace=False,
        may_contain=False,
    )
    got = to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={"peanut_allergy": "medical"}),
            rules_module.seeded_rules(),
        ).verdict
    )
    assert got == "UNCERTAIN"


def test_pescatarian_avoids_land_meat_not_just_five_species():
    """Species allowlist missed turkey/duck; composite catches animal_origin land meat."""
    assert _bucket("Pescatarian", "duck") == "avoid"
    assert _bucket("Pescatarian", "beef") == "avoid"
    assert _bucket("Pescatarian", "tuna") == "safe"
    assert _bucket("Pescatarian", "shrimp") == "safe"


def test_load_rules_drops_unknown_trigger_fields():
    bad = {
        "category": "peanut_allergy",
        "field": "peanutsource_typo",
        "operator": "eq",
        "value": "true",
        "action": "FAIL",
        "min_knowledge_state": "AUTO_CLASSIFIED",
    }
    good = {
        "category": "peanut_allergy",
        "field": "peanut_source",
        "operator": "eq",
        "value": "true",
        "action": "FAIL",
        "min_knowledge_state": "AUTO_CLASSIFIED",
    }

    class _FakeClient:
        def table(self, _name):
            return self

        def select(self, _cols):
            return self

        def execute(self):
            return SimpleNamespace(data=[bad, good])

    loaded = rules_module.load_rules(client=_FakeClient())
    fields = {getattr(r, "trigger_flag", None) for r in loaded}
    assert "peanut_source" in fields
    assert "peanutsource_typo" not in fields
