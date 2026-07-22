# backend/tests/test_compound_expansion_neutralize_wire.py
from core.compound_expansion import expand_compounds


def test_expand_compounds_passthrough_still_extracts_garlic():
    """Keyword tear lives in expansion, not neutralize — garlic pasta stays covered."""
    expanded, _dmap, _derived = expand_compounds(["garlic pasta"], role_index={})
    assert "garlic" in expanded


def test_expand_compounds_plant_mod_via_role_index():
    roles = {"almond": "plant_mod", "yogurt": "dairy_head"}
    expanded, dmap, derived = expand_compounds(
        ["almond yogurt"],
        role_index=roles,
    )
    assert "almond yogurt" in expanded
    assert "almond" in expanded
    assert "yogurt" not in expanded
    assert derived.get("almond") == "almond yogurt"
    assert dmap.get("almond") == "almond yogurt"


def test_expand_compounds_culinary_via_role_index():
    roles = {"vinegar": "culinary_keep"}
    expanded, _, _ = expand_compounds(["wine vinegar"], role_index=roles)
    assert expanded == ["wine vinegar"]
