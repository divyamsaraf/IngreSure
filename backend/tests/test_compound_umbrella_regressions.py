"""Break-test regressions: compound umbrellas, vinegar expand, safe leaks."""
from core.bridge import run_new_engine_chat, user_profile_model_to_restriction_ids
from core.compound_expansion import expand_compounds
from core.intent_detector import detect_intent
from core.knowledge.ike2.input_layer import parse_atoms
from core.models.user_profile import UserProfile
from core.parsing.chat_ingredients import prepare_chat_ingredients
from core.parsing.label_decomposer import decompose_label
from core.response_composer import build_ingredient_audit_payload


def _profile(diet="Vegan", allergens=None):
    return UserProfile(
        user_id="break",
        dietary_preference=diet,
        allergens=allergens or [],
        lifestyle=[],
    )


def _buckets(payload):
    out = {"avoid": [], "safe": [], "depends": []}
    for g in payload.get("groups") or []:
        for i in g.get("items") or []:
            out[g["status"]].append((i.get("name") or "").lower())
    return out


def test_spices_not_dropped_by_label_parser():
    assert parse_atoms("spices"), "bare 'spices' must be an atom"
    assert any(i.name == "spices" for i in decompose_label("spices"))
    names = [i.name for i in decompose_label("water, spices, salt")]
    assert "spices" in names


def test_spices_never_firm_safe_for_vegan():
    p = _profile("Vegan")
    rids = user_profile_model_to_restriction_ids(p)
    v = run_new_engine_chat(["spices"], user_profile=p, restriction_ids=rids, use_api_fallback=False)
    payload = build_ingredient_audit_payload(verdict=v, profile=p, ingredients=["spices"])
    b = _buckets(payload)
    assert not any("spice" in n for n in b["safe"]), b
    assert any("spice" in n for n in b["depends"]), b


def test_seasoning_alias_not_leaked_into_safe():
    p = _profile("Vegan")
    rids = user_profile_model_to_restriction_ids(p)
    v = run_new_engine_chat(["seasoning"], user_profile=p, restriction_ids=rids, use_api_fallback=False)
    payload = build_ingredient_audit_payload(verdict=v, profile=p, ingredients=["seasoning"])
    b = _buckets(payload)
    assert not any("season" in n for n in b["safe"]), b
    assert b["depends"], b


def test_wine_vinegar_not_collapsed_to_wine():
    expanded, display = expand_compounds(["wine vinegar", "red wine vinegar", "sugar"])
    assert "wine vinegar" in [e.lower() for e in expanded] or any(
        "vinegar" in e.lower() for e in expanded
    )
    assert not (expanded == ["wine", "sugar"] or set(x.lower() for x in expanded) == {"wine", "sugar"})


def test_soy_lecithin_not_collapsed_to_soy_only():
    expanded, _ = expand_compounds(["soy lecithin", "sunflower lecithin"])
    lows = [e.lower() for e in expanded]
    assert "soy lecithin" in lows
    assert "sunflower lecithin" in lows


def test_halal_wine_vinegar_chat_keeps_vinegar_atom():
    q = "Ingredients: wine vinegar, sugar. Is this Halal?"
    parsed = detect_intent(q)
    prep = prepare_chat_ingredients(q, parsed)
    lows = [n.lower() for n in prep.eval_names]
    assert any("vinegar" in n for n in lows), lows
    assert "wine" not in lows or any("vinegar" in n for n in lows)


def test_protected_and_phrases_stay_whole():
    from core.intent_detector import detect_intent
    from core.parsing.chat_ingredients import prepare_chat_ingredients

    q = "Ingredients: mono and diglycerides, herbs and spices, salt."
    parsed = detect_intent(q)
    prep = prepare_chat_ingredients(q, parsed)
    lows = [n.lower() for n in prep.eval_names]
    assert any("mono" in n and "di" in n for n in lows), lows
    assert any("herb" in n and "spice" in n for n in lows), lows
    assert "mono" not in lows


def test_halal_avoids_wine_vinegar():
    p = _profile("Halal")
    rids = user_profile_model_to_restriction_ids(p)
    v = run_new_engine_chat(
        ["wine vinegar", "sugar"], user_profile=p, restriction_ids=rids, use_api_fallback=False
    )
    payload = build_ingredient_audit_payload(
        verdict=v, profile=p, ingredients=["wine vinegar", "sugar"]
    )
    b = _buckets(payload)
    assert any("vinegar" in n or "wine" in n for n in b["avoid"]), b
    assert any("sugar" in n for n in b["safe"]), b
    assert not any("unknown" in n for n in b["depends"]), b
