"""B04: capture vegan + no nuts + gluten free. A17/B03: do not glue away milk."""
from core.intent_detector import detect_intent
from core.parsing.ingredient_parser import preprocess_ingredients_to_strings
from core.parsing.restriction_statement import parse_restriction_statement


def test_b04_captures_vegan_nuts_and_gluten_free():
    stmt = parse_restriction_statement("vegan, no nuts, gluten free")
    assert stmt.action == "apply"
    assert "vegan" in stmt.restriction_ids
    assert "gluten_free" in stmt.restriction_ids
    assert "nuts" in stmt.allergens
    parsed = detect_intent("vegan, no nuts, gluten free")
    pref = (parsed.profile_updates.get("dietary_preference") or "").lower()
    allergens = [a.lower() for a in (parsed.profile_updates.get("allergens") or [])]
    assert "vegan" in pref
    assert any("nut" in a for a in allergens)
    assert any("gluten" in a for a in allergens) or pref == "gluten-free"


def test_lactose_sentence_keeps_milk_atom():
    parsed = detect_intent("lactose intolerant, not dairy allergy. Milk, sugar.")
    blob = " ".join(parsed.ingredients).lower()
    assert "milk" in blob
    assert "sugar" in blob
    assert "lactose intolerant" not in blob
    assert "dairy allergy" not in blob


def test_flavouring_contains_milk_keeps_milk():
    atoms = preprocess_ingredients_to_strings("flavouring (contains milk)")
    blob = " ".join(atoms).lower()
    assert "milk" in blob
