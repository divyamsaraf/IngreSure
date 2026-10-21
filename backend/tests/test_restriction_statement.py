"""Item 52b: restriction-statement parser with confirm-before-change."""
from core.intent_detector import detect_intent
from core.parsing.restriction_statement import parse_restriction_statement


def test_celiac_is_firm_gluten():
    stmt = parse_restriction_statement("I have celiac. Check: oats, salt.")
    assert stmt.action == "apply"
    assert "gluten_free" in stmt.restriction_ids


def test_allergic_is_firm():
    stmt = parse_restriction_statement("I am allergic to peanuts. Ingredients: peanuts, salt.")
    assert stmt.action == "apply"
    assert any("peanut" in a for a in stmt.allergens)


def test_gluten_sensitive_asks_confirm_not_apply():
    stmt = parse_restriction_statement(
        "I'm a bit gluten sensitive, not celiac. Is wheat bread ok?"
    )
    assert stmt.action in {"confirm", "tighten"}
    assert stmt.needs_confirm
    assert "gluten_free" not in stmt.restriction_ids or stmt.needs_confirm


def test_lactose_intolerant_asks_confirm():
    stmt = parse_restriction_statement("lactose intolerant, not dairy allergy. Milk, sugar.")
    assert stmt.action in {"confirm", "tighten"}
    assert stmt.needs_confirm
    assert "dairy_free" in (stmt.restriction_ids + stmt.tighten_ids)


def test_used_to_be_vegan_does_not_apply():
    stmt = parse_restriction_statement("I used to be vegan. Sugar, water.")
    assert stmt.action != "apply"
    assert "vegan" not in stmt.restriction_ids


def test_allergy_gone_confirms_before_remove():
    stmt = parse_restriction_statement("I think my peanut allergy is gone. PEANUTS (49.5%).")
    assert stmt.action == "confirm"
    assert not stmt.remove_allergens


def test_temporary_restriction_confirms():
    stmt = parse_restriction_statement("Just for this week skip dairy. Cheese, bread.")
    assert stmt.action == "confirm"


def test_someone_else_is_other_scope():
    stmt = parse_restriction_statement(
        "Check this for my kid who has a milk allergy: oats, whey."
    )
    assert stmt.scope == "other"


def test_unsupported_keto_diabetic_low_sodium():
    stmt = parse_restriction_statement(
        "I'm keto / diabetic / low sodium. Check: sugar, salt, bread."
    )
    assert stmt.action == "unsupported"
    assert set(stmt.unsupported) >= {"keto", "diabetic", "low_sodium"}


def test_not_vegan_does_not_add_vegan():
    stmt = parse_restriction_statement("I am not vegan. Milk is fine. Milk, sugar.")
    assert "vegan" not in stmt.restriction_ids
    parsed = detect_intent("I am not vegan. Milk is fine. Milk, sugar.")
    assert parsed.profile_updates.get("dietary_preference") != "Vegan"


def test_detect_intent_does_not_apply_gone_allergy():
    parsed = detect_intent("I think my peanut allergy is gone. PEANUTS (49.5%).")
    assert not parsed.profile_updates.get("remove_allergens")
    assert parsed.profile_updates.get("allergens") != []
