"""General diet × allergen attribution + mixed-chat parsing matrix.

Covers the general contract (not one recipe):
- Per-ingredient FAIL restrictions never cross-stamp onto other Avoid cards
- Milk/egg/wheat allergens (mapped to dairy_free/egg_free/gluten_free) still
  render under allergens when they came from the profile allergen list
- Same ingredient failing diet + allergen gets BOTH tags
- Trailing profile/allergen prose never becomes an ingredient atom
- Typo normalization must not corrupt ingredient names (shrimp ≠ shri amp)
"""
from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from core.intent_detector import detect_intent, normalize_query_for_typos
from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.parsing.chat_ingredients import prepare_chat_ingredients
from core.response_composer import build_ingredient_audit_payload


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


def _avoid_by_name(payload):
    return {(i.get("name") or "").lower(): i for i in _items(payload, "avoid")}


def _labels(values):
    return [str(v).lower() for v in (values or [])]


# ---------------------------------------------------------------------------
# Typo normalization must not destroy ingredient tokens
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "word",
    ["shrimp", "simple", "simmer", "cumin", "vitamin", "ingredients", "gelatin"],
)
def test_typo_normalization_preserves_ingredient_words(word):
    out = normalize_query_for_typos(word)
    assert "i am" not in out
    assert word in out or out == word


def test_typo_normalization_still_expands_bare_im():
    assert normalize_query_for_typos("im vegan") == "i am vegan"
    assert normalize_query_for_typos("I'm Jain") == "i am jain"


# ---------------------------------------------------------------------------
# Parsing: trailing prose must not glue onto last ingredient
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "query,expect_atom,forbid_substr",
    [
        (
            "Ingredients: Milk, Egg, Soy, Wheat, Peanut. I have a peanut allergy.",
            "peanut",
            "allerg",
        ),
        (
            "Ingredients: gelatin, sugar, water. I'm allergic to fish.",
            "gelatin",
            "allerg",
        ),
        (
            "Ingredients: milk, butter, flour. I am allergic to milk and soy.",
            "milk",
            "allerg",
        ),
        (
            "Ingredients: honey, oats. I follow a vegan diet.",
            "honey",
            "follow",
        ),
        (
            "Ingredients: Egg, Milk, Flour. Is this Jain?",
            "egg",
            "jain",
        ),
        (
            "Ingredients: shrimp, rice, oil. I'm allergic to shellfish.",
            "shrimp",
            "allerg",
        ),
        (
            "Ingredients: milk, egg. I'm allergic to eggs and I am Jain.",
            "egg",
            "allerg",
        ),
        (
            "Milk, onion, garlic. I have a soy allergy.",
            "onion",
            "allerg",
        ),
    ],
)
def test_trailing_profile_prose_never_glues_onto_atoms(query, expect_atom, forbid_substr):
    parsed = detect_intent(query)
    prepared = prepare_chat_ingredients(query, parsed)
    names = [n.lower() for n in prepared.eval_names]
    assert any(expect_atom in n for n in names), names
    assert not any(forbid_substr in n for n in names), names
    assert not any("i have" in n or "i am" in n or "i'm" in n for n in names), names


# ---------------------------------------------------------------------------
# Attribution unit matrix (hand-built verdicts — fast, exhaustive)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "diet,allergens,by_ingredient,expect",
    [
        # Diet-only FAIL
        (
            "Hindu Vegetarian",
            ["Peanut"],
            {"egg": ["hindu_vegetarian"]},
            {"egg": {"diets": ["hindu vegetarian"], "allergens": []}},
        ),
        # Allergen-only FAIL (_allergy suffix)
        (
            "Hindu Vegetarian",
            ["Peanut"],
            {"peanut": ["peanut_allergy"]},
            {"peanut": {"diets": [], "allergens": ["peanut"]}},
        ),
        # Milk allergen maps to dairy_free — must still show under allergens
        (
            "Vegan",
            ["Milk"],
            {"milk": ["dairy_free"]},
            {"milk": {"diets": [], "allergens": ["dairy"]}},
        ),
        # Egg allergen maps to egg_free
        (
            "Vegetarian",
            ["Egg"],
            {"egg": ["egg_free"]},
            {"egg": {"diets": [], "allergens": ["egg"]}},
        ),
        # Same ingredient: diet + allergen both FAIL → both tags
        (
            "Vegan",
            ["Milk"],
            {"milk": ["vegan", "dairy_free"]},
            {"milk": {"diets": ["vegan"], "allergens": ["dairy"]}},
        ),
        # Multi-ingredient: never cross-stamp
        (
            "Vegan",
            ["Soy", "Milk"],
            {
                "gelatin": ["vegan"],
                "soy": ["soy_allergy"],
                "milk": ["vegan", "dairy_free"],
            },
            {
                "gelatin": {"diets": ["vegan"], "allergens": []},
                "soy": {"diets": [], "allergens": ["soy"]},
                "milk": {"diets": ["vegan"], "allergens": ["dairy"]},
            },
        ),
        # Jain root veg + peanut allergy
        (
            "Jain",
            ["Peanut"],
            {"onion": ["jain"], "peanut": ["peanut_allergy"]},
            {
                "onion": {"diets": ["jain"], "allergens": []},
                "peanut": {"diets": [], "allergens": ["peanut"]},
            },
        ),
        # Tree nut allergy
        (
            "No rules",
            ["Tree nut"],
            {"almond": ["tree_nut_allergy"], "water": []},
            {"almond": {"diets": [], "allergens": ["tree"]}},
        ),
        # Shellfish allergy
        (
            "Kosher",
            ["Shellfish"],
            {"shrimp": ["kosher", "shellfish_allergy"]},
            {"shrimp": {"diets": ["kosher"], "allergens": ["shellfish"]}},
        ),
    ],
)
def test_attribution_matrix_no_cross_stamp(diet, allergens, by_ingredient, expect):
    triggered = [k for k, v in by_ingredient.items() if v]
    all_rids = []
    for rids in by_ingredient.values():
        for r in rids:
            if r not in all_rids:
                all_rids.append(r)
    verdict = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=all_rids,
        triggered_ingredients=triggered,
        triggered_restrictions_by_ingredient={
            k: v for k, v in by_ingredient.items() if v
        },
    )
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=_Profile(diet, allergens),
        ingredients=list(by_ingredient.keys()) + ["water"],
    )
    avoid = _avoid_by_name(payload)
    for name, want in expect.items():
        assert name in avoid, f"missing avoid item {name}: {list(avoid)}"
        diets = _labels(avoid[name].get("diets"))
        algs = _labels(avoid[name].get("allergens"))
        for d in want["diets"]:
            assert any(d in x for x in diets), f"{name} diets={diets} missing {d}"
        for a in want["allergens"]:
            assert any(a in x for x in algs), f"{name} allergens={algs} missing {a}"
        if not want["diets"]:
            assert avoid[name].get("diets") in (None, [])
        if not want["allergens"]:
            assert avoid[name].get("allergens") in (None, [])
    # Cross-stamp guard: no avoid item may carry a restriction that only
    # belongs to a different ingredient in this case.
    for name, item in avoid.items():
        mine = set(by_ingredient.get(name, []))
        for other, other_rids in by_ingredient.items():
            if other == name:
                continue
            foreign = set(other_rids) - mine
            blob = " ".join(_labels(item.get("diets")) + _labels(item.get("allergens")))
            for rid in foreign:
                # Only flag clear cross-stamps (peanut on egg, etc.)
                token = rid.replace("_allergy", "").replace("_", " ").split()[0]
                if token in ("dairy", "egg", "gluten", "vegan", "jain", "kosher", "hindu"):
                    # diet labels are shared vocabulary; rely on exact chip emptiness above
                    continue
                if token and token in blob and rid not in mine:
                    pytest.fail(f"{name} card leaked foreign restriction {rid}: {blob}")


# ---------------------------------------------------------------------------
# End-to-end chat: several diet × allergen combos
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "diet,allergens,query,expect_avoid,forbid_safe",
    [
        (
            "Hindu Vegetarian",
            ["Peanut"],
            "Ingredients: Milk, Egg, Soy, Wheat, Peanut. I have a peanut allergy.",
            {
                "egg": {"has_diet": True, "has_allergen": False},
                "peanut": {"has_diet": False, "has_allergen": True},
            },
            ["peanut", "egg"],
        ),
        (
            "Vegan",
            ["Milk", "Soy"],
            "Ingredients: Water, Milk, Soy, Peanut, Gelatin.",
            {
                "milk": {"has_diet": True, "has_allergen": True},
                "soy": {"has_diet": False, "has_allergen": True},
                "gelatin": {"has_diet": True, "has_allergen": False},
            },
            ["milk", "soy", "gelatin"],
        ),
        (
            "Jain",
            ["Peanut"],
            "Ingredients: Onion, Potato, Peanut, Water.",
            {
                "onion": {"has_diet": True, "has_allergen": False},
                "potato": {"has_diet": True, "has_allergen": False},
                "peanut": {"has_diet": False, "has_allergen": True},
            },
            ["onion", "potato", "peanut"],
        ),
        (
            "Kosher",
            ["Shellfish"],
            "Ingredients: Shrimp, Rice, Oil. I'm allergic to shellfish.",
            {
                "shrimp": {"has_diet": True, "has_allergen": True},
            },
            ["shrimp"],
        ),
    ],
)
def test_e2e_diet_allergen_matrix(diet, allergens, query, expect_avoid, forbid_safe):
    from app import app

    client = TestClient(app)
    uid = f"matrix-{diet}-{'-'.join(allergens)}".lower().replace(" ", "")[:40]
    r = client.post(
        "/profile",
        json={
            "user_id": uid,
            "dietary_preference": diet,
            "allergens": allergens,
            "lifestyle": [],
        },
    )
    assert r.status_code == 200
    r = client.post("/chat/grocery", json={"user_id": uid, "query": query})
    assert r.status_code == 200
    m = re.search(r"<<<INGREDIENT_AUDIT>>>(.*?)<<<INGREDIENT_AUDIT>>>", r.text, re.S)
    assert m, r.text[:400]
    payload = json.loads(m.group(1))
    avoid = _avoid_by_name(payload)
    safe = [(i.get("name") or "").lower() for i in _items(payload, "safe")]
    depends = [(i.get("name") or "").lower() for i in _items(payload, "depends")]

    for name, want in expect_avoid.items():
        assert name in avoid, f"expected {name} in avoid, got {list(avoid)}"
        diets = _labels(avoid[name].get("diets"))
        algs = _labels(avoid[name].get("allergens"))
        if want["has_diet"]:
            assert diets, f"{name} should have diet tags"
        else:
            assert avoid[name].get("diets") in (None, [])
        if want["has_allergen"]:
            assert algs, f"{name} should have allergen tags"
        else:
            assert avoid[name].get("allergens") in (None, [])

    for name in forbid_safe:
        assert not any(name in s for s in safe), f"{name} leaked into safe: {safe}"
    assert not any("allerg" in d or "i have" in d for d in depends)
