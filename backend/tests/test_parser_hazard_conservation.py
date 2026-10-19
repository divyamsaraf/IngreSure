"""CI: hazard tokens in raw lists must survive flatten (parser conservation)."""
from __future__ import annotations

import pytest

from core.normalization.parser import flatten_ingredients
from core.parsing.hazard_lexicon import conservation_misses

# Committed sample — real OFF-shaped strings that previously dropped hazards.
_CONSERVATION_SAMPLE = [
    (
        "PEANUTS (49.5%), honey, dark chocolate (12%) (cocoa mass, cane sugar, cocoa butter), salt",
        {"peanut"},
    ),
    (
        "Cooked Wheatberries (22%) (Water, Wheatberries), Cooked Black Barley (14%) (Water, Barley), salt",
        {"gluten"},
    ),
    (
        "wheat flour (min. 62%), water, yeast, salt",
        {"gluten"},
    ),
    (
        "milk 3.5%, sugar, cocoa",
        {"dairy"},
    ),
    (
        "peanuts 49.5%, rice syrup",
        {"peanut"},
    ),
    (
        "peanuts (49,5 %), salt",
        {"peanut"},
    ),
    (
        "Ingredients: almonds, cashews, dates. Contains: Eggs, Almonds.",
        {"tree_nut", "egg"},
    ),
]


@pytest.mark.parametrize("raw,required", _CONSERVATION_SAMPLE)
def test_hazard_conservation_committed_sample(raw, required):
    atoms = flatten_ingredients(raw)
    lost = conservation_misses(raw, atoms)
    assert required.isdisjoint(lost), (raw, atoms, lost)


def test_hazard_conservation_peanut_bar_full_list():
    raw = (
        "PEANUTS (49.5%), honey, dark chocolate (12%) (cocoa mass, cane sugar, cocoa butter), "
        "SOYA crispies (10.5%), desiccated coconut (7.5%), rice syrup, salt."
    )
    atoms = flatten_ingredients(raw)
    assert "peanut" in atoms or "peanuts" in atoms
    assert not conservation_misses(raw, atoms) & {"peanut", "soy"}


@pytest.mark.parametrize(
    "raw,required",
    [
        ("Refined Wheat Flour (Maida), salt", {"gluten"}),
        ("Peanut Butter (Unsweetened)", {"peanut"}),
        (
            "Unbleached Enriched Flour (Wheat Flour, Niacin, Reduced Iron, "
            "Thiamine Mononitrate {Vitamin B1}, Riboflavin {Vitamin B2}, Folic Acid), Sugar",
            {"gluten"},
        ),
        ("WATER, SOYABEANS(13.6%), SUGAR", {"soy"}),
    ],
)
def test_hazard_conservation_synonym_and_brace_patterns(raw, required):
    atoms = flatten_ingredients(raw)
    lost = conservation_misses(raw, atoms)
    assert required.isdisjoint(lost), (raw, atoms, lost)
