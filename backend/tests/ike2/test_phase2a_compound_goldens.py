# backend/tests/ike2/test_phase2a_compound_goldens.py
import pytest

from core.compound_expansion import expand_compounds


@pytest.mark.parametrize(
    "phrase,role_index,expect_phrase,forbidden_bare",
    [
        (
            "plant yogurt",
            {"plant": "plant_mod", "yogurt": "dairy_head"},
            True,
            ["yogurt"],
        ),
        (
            "yogurt plant",
            {"plant": "plant_mod", "yogurt": "dairy_head"},
            True,
            ["yogurt"],
        ),
        (
            "almond yogurt",
            {"almond": "plant_mod", "yogurt": "dairy_head"},
            True,
            ["yogurt"],
        ),
        (
            "wine vinegar",
            {"vinegar": "culinary_keep"},
            True,
            ["wine"],
        ),
        (
            "soy lecithin",
            {"lecithin": "culinary_keep"},
            True,
            ["soy"],
        ),
    ],
)
def test_phase2a_compound_goldens(phrase, role_index, expect_phrase, forbidden_bare):
    expanded, _dmap, derived = expand_compounds([phrase], role_index=role_index)
    lows = [e.lower() for e in expanded]
    if expect_phrase:
        assert phrase.lower() in lows
    for bad in forbidden_bare:
        assert bad not in lows
    plant_tokens = [
        t for t, r in role_index.items()
        if r == "plant_mod" and t in phrase.split()
    ]
    for pt in plant_tokens:
        assert pt in lows
        assert derived.get(pt) == phrase.lower()
