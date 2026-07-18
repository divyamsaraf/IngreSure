"""Task 6: reason_category + diet-vs-allergen copy attribution (spec §7-8).

Uses hand-built ComplianceVerdict objects where possible so these stay fast
and independent of the full IKE-2 pipeline; the golden matrix
(tests/ike2/test_audit_matrix.py) covers the end-to-end path.
"""
from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.response_composer import (
    build_ingredient_audit_payload,
    compose_verdict_explanation,
    _reason_category_for_uncertain,
)

_BLANKET_PHRASE = "may conflict with your dietary requirements"


class _Profile:
    def __init__(self, dietary_preference="No rules", allergens=None):
        self.dietary_preference = dietary_preference
        self.allergens = allergens or []
        self.lifestyle = []


def _items(payload, status):
    for group in payload.get("groups", []):
        if group.get("status") == status:
            return group.get("items", [])
    return []


def test_unknown_ingredient_depends_gets_unknown_category_not_diet_conflict():
    verdict = ComplianceVerdict(
        status=VerdictStatus.UNCERTAIN,
        uncertain_ingredients=["zzzx_unknown_fixture_ingredient"],
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=_Profile("Vegan"),
        ingredients=["zzzx_unknown_fixture_ingredient"],
    )
    items = _items(payload, "depends")
    assert len(items) == 1
    assert items[0]["reason_category"] == "unknown_ingredient"
    assert _BLANKET_PHRASE not in items[0]["reason"]


def test_resolved_ingredient_without_special_flags_is_unverified_not_diet_conflict():
    # Direct unit test of the classifier: "beef" resolves in Tier 1 with a
    # known species (no compound cap, no missing-species ambiguity), so a
    # Depends bucket for it (were it ever uncertain) must read "unverified",
    # never diet_conflict language.
    assert _reason_category_for_uncertain("beef") == "unverified"


def test_compound_umbrella_category_for_natural_flavors():
    verdict = ComplianceVerdict(
        status=VerdictStatus.UNCERTAIN,
        uncertain_ingredients=["natural flavors"],
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=_Profile("Vegan"),
        ingredients=["natural flavors"],
    )
    items = _items(payload, "depends")
    assert items[0]["reason_category"] == "compound_umbrella"
    assert _BLANKET_PHRASE not in items[0]["reason"]


def test_source_ambiguous_category_for_species_unknown_collagen():
    verdict = ComplianceVerdict(
        status=VerdictStatus.UNCERTAIN,
        uncertain_ingredients=["collagen"],
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=_Profile("Halal"),
        ingredients=["collagen"],
    )
    items = _items(payload, "depends")
    assert items[0]["reason_category"] == "source_ambiguous"
    assert _BLANKET_PHRASE not in items[0]["reason"]


def test_gelatin_hindu_veg_with_fish_allergen_is_diet_primary_not_allergen():
    """Spec §7: gelatin FAILs both hindu_vegetarian (diet) and fish_allergy
    (allergen) -- copy must stay diet-primary, never 'your allergens'."""
    verdict = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["hindu_vegetarian", "fish_allergy"],
        triggered_ingredients=["gelatin"],
    )
    profile = _Profile("Hindu Vegetarian", allergens=["Fish"])

    explanation = compose_verdict_explanation(verdict, profile, ["gelatin"])
    assert "allergen" not in explanation.lower()

    payload = build_ingredient_audit_payload(
        verdict=verdict, profile=profile, ingredients=["gelatin"],
    )
    items = _items(payload, "avoid")
    assert items[0]["reason_category"] == "diet_conflict"


def test_allergen_only_fail_gets_allergen_conflict_category():
    verdict = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["peanut_allergy"],
        triggered_ingredients=["peanut"],
    )
    profile = _Profile("No rules", allergens=["Peanut"])
    payload = build_ingredient_audit_payload(
        verdict=verdict, profile=profile, ingredients=["peanut"],
    )
    items = _items(payload, "avoid")
    assert items[0]["reason_category"] == "allergen_conflict"


def test_no_blanket_phrase_on_safe_verdict():
    verdict = ComplianceVerdict(status=VerdictStatus.SAFE)
    payload = build_ingredient_audit_payload(
        verdict=verdict, profile=_Profile("Vegan"), ingredients=["sugar"],
    )
    assert _BLANKET_PHRASE not in str(payload)


def test_no_blanket_phrase_on_unknown_depends():
    verdict = ComplianceVerdict(
        status=VerdictStatus.UNCERTAIN,
        uncertain_ingredients=["zzzx_unknown_fixture_ingredient"],
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=_Profile("Vegan"),
        ingredients=["zzzx_unknown_fixture_ingredient"],
    )
    assert _BLANKET_PHRASE not in str(payload)
