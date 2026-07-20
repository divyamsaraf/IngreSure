"""Adversarial regressions: allergen prose leaks, egg-noodle expansion."""
from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
from core.intent_detector import detect_intent
from core.knowledge.ike2.input_layer import parse_atoms
from core.models.user_profile import UserProfile
from core.models.verdict import VerdictStatus
from core.parsing.chat_ingredients import prepare_chat_ingredients
from core.response_composer import build_ingredient_audit_payload


def _prep(q: str):
    parsed = detect_intent(q)
    prep = prepare_chat_ingredients(q, parsed)
    return parsed, prep


def test_allergic_to_prose_not_glued_onto_ingredients():
    """'Ingredients: rice. Allergic to milk.' must not audit milk as the food."""
    parsed, prep = _prep("Ingredients: rice. Allergic to milk.")
    assert "milk" in (parsed.profile_updates.get("allergens") or []) or any(
        "milk" in str(a).lower()
        for a in (parsed.profile_updates.get("allergens") or [])
    )
    lows = [n.lower() for n in prep.eval_names]
    assert "rice" in lows
    assert lows == ["rice"] or (lows == ["rice"] and "milk" not in lows)
    assert not any("allergic" in n for n in lows)
    assert "milk" not in lows


def test_and_allergic_to_after_diet_updates_profile_not_ingredients():
    q = "gelatin, honey, onion. I am Jain and allergic to fish."
    parsed, prep = _prep(q)
    assert parsed.profile_updates.get("dietary_preference") == "Jain"
    algs = [str(a).lower() for a in (parsed.profile_updates.get("allergens") or [])]
    assert any("fish" in a for a in algs), parsed.profile_updates
    lows = [n.lower() for n in prep.eval_names]
    assert "gelatin" in lows and "honey" in lows and "onion" in lows
    assert "fish" not in lows
    assert not any("allergic" in n for n in lows)


def test_allergic_to_peanuts_after_ingredient_list():
    parsed, prep = _prep("Ingredients: water, salt. Allergic to peanuts.")
    algs = [str(a).lower() for a in (parsed.profile_updates.get("allergens") or [])]
    assert any("peanut" in a for a in algs), parsed.profile_updates
    lows = [n.lower() for n in prep.eval_names]
    assert "water" in lows and "salt" in lows
    assert not any("peanut" in n or "allergic" in n for n in lows)


def test_vegan_and_allergic_to_soy_does_not_add_soy_ingredient():
    parsed, prep = _prep("Ingredients: sugar. I follow vegan and allergic to soy.")
    assert parsed.profile_updates.get("dietary_preference") == "Vegan"
    algs = [str(a).lower() for a in (parsed.profile_updates.get("allergens") or [])]
    assert any("soy" in a for a in algs)
    lows = [n.lower() for n in prep.eval_names]
    assert lows == ["sugar"]


def test_egg_noodles_avoid_for_vegan_via_engine():
    """Direct engine path must expand egg noodles → egg (not unknown Depends)."""
    atoms = [a.name for a in parse_atoms("egg noodles")]
    assert "egg" in [a.lower() for a in atoms], atoms

    p = UserProfile(user_id="t", dietary_preference="Vegan", allergens=[], lifestyle=[])
    rids = user_profile_model_to_restriction_ids(p)
    v = run_new_engine_chat(
        ["egg noodles"], user_profile=p, restriction_ids=rids, use_api_fallback=False
    )
    assert v.status == VerdictStatus.NOT_SAFE, (v.status, v.triggered_ingredients)
    payload = build_ingredient_audit_payload(
        verdict=v, profile=p, ingredients=["egg noodles"]
    )
    avoid = [
        (i.get("name") or "").lower()
        for g in payload.get("groups") or []
        if g["status"] == "avoid"
        for i in g["items"]
    ]
    assert any("egg" in n for n in avoid), avoid


def test_multi_allergy_prose_does_not_leave_also_residue():
    q = (
        "Ingredients: milk, egg, peanut. I am Hindu Vegetarian. "
        "I have a peanut allergy. Also allergic to soy."
    )
    parsed, prep = _prep(q)
    assert parsed.profile_updates.get("dietary_preference") == "Hindu Vegetarian"
    algs = [str(a).lower() for a in (parsed.profile_updates.get("allergens") or [])]
    assert any("peanut" in a for a in algs)
    assert any("soy" in a for a in algs)
    lows = [n.lower() for n in prep.eval_names]
    assert sorted(lows) == ["egg", "milk", "peanut"], lows
    assert not any("also" in n for n in lows)


def test_bare_peanut_allergy_plus_also_allergic_captures_both():
    """Bare 'peanut allergy' (no 'I have') must not be dropped when soy follows."""
    q = "peanut allergy. Also allergic to soy. Ingredients: oil, sugar, soy lecithin, peanut oil"
    parsed, prep = _prep(q)
    algs = [str(a).lower() for a in (parsed.profile_updates.get("allergens") or [])]
    assert any("peanut" in a for a in algs), parsed.profile_updates
    assert any("soy" in a for a in algs), parsed.profile_updates
    lows = [n.lower() for n in prep.eval_names]
    assert "oil" in lows and "sugar" in lows
    assert not any("allergy" in n or "allergic" in n for n in lows)


def test_check_colon_list_does_not_keep_check_prefix():
    q = "I follow Jain and allergic to fish. Check: potato, honey, fish sauce"
    parsed, prep = _prep(q)
    assert parsed.profile_updates.get("dietary_preference") == "Jain"
    algs = [str(a).lower() for a in (parsed.profile_updates.get("allergens") or [])]
    assert any("fish" in a for a in algs)
    lows = [n.lower() for n in prep.eval_names]
    assert "potato" in lows and "honey" in lows
    assert not any(n.startswith("check") for n in lows)


def test_multi_allergen_list_forms_capture_all():
    """Systemic: comma/and lists before allergy/allergies must not drop earlier items."""
    cases = [
        "I have peanut, soy, and egg allergies",
        "I have peanut, soy and egg allergies",
        "I am allergic to peanut, soy, and egg",
        "allergies: peanut, soy, egg",
        "my allergies are peanut, soy, and egg",
        "peanut, soy, and egg allergy",
        "I have allergies to milk and eggs",
        "Allergic to peanuts, tree nuts, and shellfish",
    ]
    for q in cases:
        parsed, _ = _prep(q)
        algs = [str(a).lower() for a in (parsed.profile_updates.get("allergens") or [])]
        joined = " ".join(algs)
        if "shellfish" in q.lower():
            assert any("peanut" in a for a in algs), (q, algs)
            assert any("nut" in a for a in algs), (q, algs)
            assert any("shellfish" in a for a in algs), (q, algs)
        elif "milk" in q.lower() and "eggs" in q.lower():
            assert any("milk" in a for a in algs), (q, algs)
            assert any("egg" in a for a in algs), (q, algs)
        else:
            assert any("peanut" in a for a in algs), (q, algs)
            assert any("soy" in a for a in algs), (q, algs)
            assert any("egg" in a for a in algs), (q, algs)
        assert "allergy" not in joined and "allergies" not in joined
