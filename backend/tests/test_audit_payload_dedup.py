"""Audit payload must not list the same substance in Avoid and Safe (E-numbers, aliases)."""
from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.response_composer import build_ingredient_audit_payload, count_safe_audit_ingredients


class _Profile:
    dietary_preference = "Hindu Vegetarian"
    allergens = []
    lifestyle = []


def _group_names(payload, status):
    return [
        item["name"]
        for group in payload.get("groups", [])
        if group.get("status") == status
        for item in group.get("items", [])
    ]


def test_format_audit_item_name_e_number_shows_both():
    from core.response_composer import format_audit_item_name

    assert format_audit_item_name("e441", "gelatin") == "E441 · Gelatin"
    assert format_audit_item_name("E441", "gelatin") == "E441 · Gelatin"
    assert format_audit_item_name("gelatin", "gelatin") == "Gelatin"
    assert format_audit_item_name("E120", "carmine") == "E120 · Carmine"


def test_e120_avoid_only_not_also_safe():
    verdict = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["hindu_vegetarian"],
        triggered_ingredients=["carmine"],
        triggered_ingredient_to_input={"carmine": "E120"},
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=_Profile(),
        ingredients=["E120"],
    )
    assert _group_names(payload, "avoid") == ["E120 · Carmine"]
    assert _group_names(payload, "safe") == []
    assert count_safe_audit_ingredients(["E120"], verdict) == 0


def test_e441_end_to_end_shows_user_input_in_avoid():
    """Typing E441 should show E441 in audit cards, not the resolved name Gelatin."""
    from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids

    profile = _Profile()
    rids = user_profile_model_to_restriction_ids(profile)
    verdict = run_new_engine_chat(["e441"], user_profile=profile, restriction_ids=rids, use_api_fallback=False)
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=profile,
        ingredients=["e441"],
    )
    assert _group_names(payload, "avoid") == ["E441 · Gelatin"]
    assert verdict.triggered_ingredient_to_input == {"gelatin": "e441"}


def test_e441_gelatin_alias_not_duplicated_in_safe():
    verdict = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["vegetarian"],
        triggered_ingredients=["gelatin"],
        triggered_ingredient_to_input={"gelatin": "E441"},
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=_Profile(),
        ingredients=["E441"],
    )
    assert _group_names(payload, "avoid") == ["E441 · Gelatin"]
    assert _group_names(payload, "safe") == []


def test_mixed_list_excludes_triggered_from_safe():
    verdict = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["hindu_vegetarian"],
        triggered_ingredients=["carmine"],
        triggered_ingredient_to_input={"carmine": "E120"},
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=_Profile(),
        ingredients=["E120", "Sugar", "Salt"],
    )
    assert _group_names(payload, "avoid") == ["E120 · Carmine"]
    safe = _group_names(payload, "safe")
    assert "E120" not in safe
    assert "Sugar" in safe
    assert "Salt" in safe
    assert count_safe_audit_ingredients(["E120", "Sugar", "Salt"], verdict) == 2


def test_triggered_without_input_mapping_still_excludes_alias():
    """When mapping is missing, canonical triggered name still excludes E-number input."""
    verdict = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["hindu_vegetarian"],
        triggered_ingredients=["carmine"],
        triggered_ingredient_to_input=None,
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=_Profile(),
        ingredients=["e120"],
    )
    assert _group_names(payload, "avoid") == ["Carmine"]
    assert _group_names(payload, "safe") == []
