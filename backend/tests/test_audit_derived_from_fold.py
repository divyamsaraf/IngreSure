# backend/tests/test_audit_derived_from_fold.py
from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.response_composer import build_ingredient_audit_payload


class _Profile:
    dietary_preference = "Vegan"
    allergens = ["Tree Nuts"]
    lifestyle = []


def test_almond_yogurt_single_avoid_card_when_almond_triggers():
    verdict = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["tree_nut_allergy"],
        triggered_ingredients=["almond"],
        triggered_ingredient_to_input={"almond": "almond"},
        triggered_restrictions_by_ingredient={
            "almond": ["tree_nut_allergy"],
        },
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=_Profile(),
        ingredients=["almond yogurt", "almond", "sugar"],
        display_names={
            "almond yogurt": "almond yogurt",
            "almond": "almond yogurt",
            "sugar": "sugar",
        },
        derived_from={"almond": "almond yogurt"},
    )
    avoid_names = [
        i["name"]
        for g in payload["groups"]
        if g["status"] == "avoid"
        for i in g["items"]
    ]
    assert sum(1 for n in avoid_names if "almond" in n.lower()) == 1
    all_names = [i["name"] for g in payload["groups"] for i in g["items"]]
    assert any("sugar" in n.lower() for n in all_names)
    # Derived child must not appear as its own top-level avoid card alongside parent.
    assert not any(n.lower().strip() == "almond" for n in avoid_names)
