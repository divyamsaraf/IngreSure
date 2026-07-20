"""Root-cause regressions: unresolved identity, umbrellas, empty Ingredients, for-me."""
from core.bridge import (
    _run_ike2_compliance,
    map_ike2_to_compliance_verdict,
    run_new_engine_chat,
    user_profile_model_to_restriction_ids,
)
from core.intent_detector import detect_intent
from core.knowledge.ike2.resolver import ResolvedIngredient
from core.knowledge.ike2.seam import to_compliance_input
from core.models.user_profile import UserProfile
from core.parsing.chat_ingredients import prepare_chat_ingredients
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


def test_unresolved_atoms_keep_distinct_identities():
    """Unresolved must not collapse to one empty canonical (Unknown + merge)."""
    result, inputs, dmap = _run_ike2_compliance(
        ["preservatives_xyz", "colors_xyz", "mystery_abc"], ["vegan"], None
    )
    names = [getattr(i, "canonical_name", "") for i in inputs]
    assert all(n for n in names), names
    assert len(set(names)) == 3, names
    keys = {name for (name, _rid) in (result.breakdown or {})}
    assert "" not in keys
    assert len(keys) == 3, keys
    v = map_ike2_to_compliance_verdict(result, inputs, input_display_map=dmap)
    assert "" not in (v.uncertain_ingredients or [])
    assert not any(
        (x or "").strip().lower() in {"", "unknown"} for x in (v.uncertain_ingredients or [])
    )


def test_seam_unresolved_uses_query_atom_as_identity():
    r = ResolvedIngredient(
        group=None,
        source="unknown_queue",
        confidence_band="none",
        trusted=False,
        resolution_layer="L5_unknown_queue",
        status="uncertain",
    )
    ci = to_compliance_input(r, query_atom="mystery powder")
    assert ci.canonical_name == "mystery powder"
    assert ci.knowledge_state == "UNCLASSIFIED"
    assert ci.trusted is False


def test_bare_preservatives_and_colors_are_compound_depends_not_safe():
    p = _profile("Vegan")
    rids = user_profile_model_to_restriction_ids(p)
    for term in ("preservatives", "colors", "colours"):
        v = run_new_engine_chat([term], user_profile=p, restriction_ids=rids, use_api_fallback=False)
        payload = build_ingredient_audit_payload(verdict=v, profile=p, ingredients=[term])
        b = _buckets(payload)
        assert not b["safe"], (term, b)
        assert b["depends"], (term, b)
        assert not any("unknown" == n for n in b["depends"]), (term, b)
        assert len(b["depends"]) == 1, (term, b)


def test_herbs_and_spices_maps_to_compound_depends():
    p = _profile("Jain")
    rids = user_profile_model_to_restriction_ids(p)
    v = run_new_engine_chat(
        ["herbs and spices"], user_profile=p, restriction_ids=rids, use_api_fallback=False
    )
    payload = build_ingredient_audit_payload(
        verdict=v, profile=p, ingredients=["herbs and spices"]
    )
    b = _buckets(payload)
    assert not b["safe"], b
    assert b["depends"], b
    assert not any("unknown" == n for n in b["depends"]), b


def test_halal_allows_apple_cider_and_balsamic_vinegar():
    p = _profile("Halal")
    rids = user_profile_model_to_restriction_ids(p)
    for term in ("apple cider vinegar", "balsamic vinegar"):
        v = run_new_engine_chat([term], user_profile=p, restriction_ids=rids, use_api_fallback=False)
        payload = build_ingredient_audit_payload(verdict=v, profile=p, ingredients=[term])
        b = _buckets(payload)
        assert any("vinegar" in n for n in b["safe"]), (term, b)
        assert not b["avoid"], (term, b)
        assert not any("unknown" == n for n in b["depends"]), (term, b)


def test_empty_ingredients_header_yields_no_atoms():
    for q in ("Ingredients:", "Ingredients: ", "Ingredients:   "):
        parsed = detect_intent(q)
        assert parsed.ingredients == [], (q, parsed.ingredients)
        prep = prepare_chat_ingredients(q, parsed)
        assert prep.eval_names == [], (q, prep.eval_names)


def test_trailing_for_me_stripped_from_ingredient_tokens():
    parsed = detect_intent("Check milk and eggs for me")
    lows = [n.lower() for n in parsed.ingredients]
    assert lows == ["milk", "eggs"], lows
    assert not any("for me" in n for n in lows)


def test_hindu_vegetarian_allows_honey():
    """Hindu Vegetarian is lacto-veg: honey is allowed (unlike Vegan/Jain)."""
    from core.models.verdict import VerdictStatus

    p = _profile("Hindu Vegetarian")
    rids = user_profile_model_to_restriction_ids(p)
    v = run_new_engine_chat(["honey"], user_profile=p, restriction_ids=rids, use_api_fallback=False)
    assert v.status == VerdictStatus.SAFE, (v.status, v.triggered_ingredients)
    payload = build_ingredient_audit_payload(verdict=v, profile=p, ingredients=["honey"])
    b = _buckets(payload)
    assert any("honey" in n for n in b["safe"]), b
    assert not any("honey" in n for n in b["avoid"]), b


def test_structural_header_with_children_not_emitted_as_atom():
    """Preservatives/Colors (A, B) must emit children only — not the header."""
    from core.knowledge.ike2.input_layer import parse_atoms

    colors = [a.name for a in parse_atoms("Ingredients: water, Colors (Red 40, Yellow 5), salt")]
    assert "colors" not in colors and "colours" not in colors, colors
    assert "red 40" in colors and "yellow 5" in colors

    preservatives = [
        a.name
        for a in parse_atoms(
            "Ingredients: flour, Preservatives (Calcium Propionate, Sorbic Acid), yeast"
        )
    ]
    assert "preservatives" not in preservatives, preservatives
    assert "calcium propionate" in preservatives
    assert "sorbic acid" in preservatives


def test_bare_preservatives_still_an_atom():
    from core.knowledge.ike2.input_layer import parse_atoms

    names = [a.name for a in parse_atoms("preservatives")]
    assert names == ["preservatives"]
