"""Regression: Ingredients list + inline allergen sentence must not corrupt atoms
or stamp every Avoid card with every triggered restriction.

User report (Hindu Vegetarian + peanut allergy):
  "Ingredients: Milk, Egg, Soy, Wheat, Peanut. I have a peanut allergy."
Incorrectly put Peanut in Safe (or Depends as 'peanut i have…'), tagged Egg
with peanut allergy, and tagged Peanut with Hindu Vegetarian.
"""
from fastapi.testclient import TestClient

from core.intent_detector import detect_intent
from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.parsing.chat_ingredients import prepare_chat_ingredients
from core.response_composer import build_ingredient_audit_payload


class _Profile:
    def __init__(self, dietary_preference="Hindu Vegetarian", allergens=None):
        self.dietary_preference = dietary_preference
        self.allergens = allergens or ["Peanut"]
        self.lifestyle = []


def _items(payload, status):
    for group in payload.get("groups", []):
        if group.get("status") == status:
            return group.get("items", [])
    return []


def _names(items):
    return [(i.get("name") or "").lower() for i in items]


QUERY = "Ingredients: Milk, Egg, Soy, Wheat, Peanut. I have a peanut allergy."


def test_intent_strips_allergen_sentence_and_trailing_period_from_peanut():
    parsed = detect_intent(QUERY)
    assert parsed.profile_updates.get("allergens") == ["peanut"]
    keys = [i.lower().strip().rstrip(".") for i in parsed.ingredients]
    assert "peanut" in keys
    assert not any("allergy" in i.lower() for i in parsed.ingredients)
    assert not any(i.rstrip().endswith(".") for i in parsed.ingredients)


def test_prepare_chat_ingredients_does_not_glue_allergy_sentence_onto_peanut():
    parsed = detect_intent(QUERY)
    prepared = prepare_chat_ingredients(QUERY, parsed)
    names = [n.lower() for n in prepared.eval_names]
    assert "peanut" in names
    assert not any("allergy" in n for n in names)
    assert not any("i have" in n for n in names)


def test_audit_cards_attribute_restrictions_per_ingredient():
    """Egg → diet only; Peanut → allergen only. Never cross-stamp."""
    verdict = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["hindu_vegetarian", "peanut_allergy"],
        triggered_ingredients=["egg", "peanut"],
        triggered_restrictions_by_ingredient={
            "egg": ["hindu_vegetarian"],
            "peanut": ["peanut_allergy"],
        },
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=_Profile(),
        ingredients=["milk", "egg", "soy", "wheat", "peanut"],
    )
    avoid = { (i["name"] or "").lower(): i for i in _items(payload, "avoid") }
    assert "egg" in avoid
    assert "peanut" in avoid
    assert avoid["egg"].get("diets") == ["Hindu Vegetarian"]
    assert avoid["egg"].get("allergens") in (None, [])
    peanut_allergens = [a.lower() for a in (avoid["peanut"].get("allergens") or [])]
    assert any("peanut" in a for a in peanut_allergens)
    assert avoid["peanut"].get("diets") in (None, [])
    safe = _names(_items(payload, "safe"))
    assert any("milk" in n for n in safe)
    assert not any("peanut" in n for n in safe)
    assert not any("egg" in n for n in safe)


def test_end_to_end_hindu_veg_peanut_allergy_chat():
    from app import app

    client = TestClient(app)
    uid = "hv-peanut-mixed-chat"
    r = client.post(
        "/profile",
        json={
            "user_id": uid,
            "dietary_preference": "Hindu Vegetarian",
            "allergens": ["Peanut"],
            "lifestyle": [],
        },
    )
    assert r.status_code == 200

    r = client.post("/chat/grocery", json={"user_id": uid, "query": QUERY})
    assert r.status_code == 200
    body = r.text
    start = body.find("<<<INGREDIENT_AUDIT>>>")
    assert start != -1
    end = body.find("<<<INGREDIENT_AUDIT>>>", start + 1)
    import json

    payload = json.loads(body[start + len("<<<INGREDIENT_AUDIT>>>") : end])
    avoid = { (i.get("name") or "").lower(): i for i in _items(payload, "avoid") }
    safe = _names(_items(payload, "safe"))
    depends = _names(_items(payload, "depends"))

    assert "egg" in avoid
    assert "peanut" in avoid
    assert not any("peanut" in n for n in safe)
    assert not any("allergy" in n for n in depends)
    assert not any("i have" in n for n in depends)

    egg = avoid["egg"]
    peanut = avoid["peanut"]
    assert egg.get("diets") == ["Hindu Vegetarian"]
    assert egg.get("allergens") in (None, [])
    peanut_allergens = [a.lower() for a in (peanut.get("allergens") or [])]
    assert any("peanut" in a for a in peanut_allergens)
    assert peanut.get("diets") in (None, [])
