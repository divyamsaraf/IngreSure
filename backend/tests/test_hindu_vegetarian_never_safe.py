"""Ontology false-safe pins: bonito flakes, bottarga, broth, stock.

Fish rows must not be SAFE on meat/fish diets or fish_allergy. They stay SAFE
on pescatarian / halal / hindu_non_vegetarian (fish is permitted). Generic
broth/stock must never be firm SAFE on vegan/jain/hindu_vegetarian/vegetarian.
Vegetable broth stays plant SAFE. No evaluator keyword blocklist.
"""
from __future__ import annotations

import pytest

from core.api.v1_evaluate import evaluate_ingredients
from core.models.verdict import VerdictStatus

FISH_ROWS = ("bonito flakes", "bottarga")
FISH_NOT_SAFE = (
    "vegan",
    "jain",
    "hindu_vegetarian",
    "vegetarian",
    "lacto_vegetarian",
    "ovo_vegetarian",
    "fish_allergy",
)
FISH_STAY_SAFE = (
    "pescatarian",
    "hindu_non_vegetarian",
)
BROTH_STOCK = ("broth", "stock")
BROTH_NEVER_SAFE = (
    "vegan",
    "jain",
    "hindu_vegetarian",
    "vegetarian",
)
ALL_FRAMEWORKS = (
    "vegan",
    "jain",
    "hindu_vegetarian",
    "hindu_non_vegetarian",
    "halal",
    "kosher",
    "pescatarian",
    "vegetarian",
    "lacto_vegetarian",
    "ovo_vegetarian",
    "fish_allergy",
    "shellfish_allergy",
    "peanut_allergy",
    "egg_free",
    "dairy_free",
    "gluten_free",
    "soy_allergy",
    "sesame_allergy",
)


def _status(ingredient: str, restriction: str) -> VerdictStatus:
    return evaluate_ingredients(
        [ingredient], [restriction], use_api_fallback=False
    ).status


@pytest.mark.parametrize("ingredient", FISH_ROWS)
@pytest.mark.parametrize("restriction", FISH_NOT_SAFE)
def test_fish_rows_not_safe_on_meat_fish_diets(ingredient: str, restriction: str) -> None:
    st = _status(ingredient, restriction)
    assert st != VerdictStatus.SAFE, (ingredient, restriction, st.value)


@pytest.mark.parametrize("ingredient", FISH_ROWS)
@pytest.mark.parametrize("restriction", FISH_STAY_SAFE)
def test_fish_rows_safe_where_fish_is_permitted(ingredient: str, restriction: str) -> None:
    st = _status(ingredient, restriction)
    assert st == VerdictStatus.SAFE, (ingredient, restriction, st.value)


@pytest.mark.parametrize("ingredient", FISH_ROWS)
def test_fish_rows_not_avoid_on_halal(ingredient: str) -> None:
    """Halal permits fish; R06 keeps uncertified fish UNCERTAIN, never NOT_SAFE."""
    st = _status(ingredient, "halal")
    assert st != VerdictStatus.NOT_SAFE, (ingredient, st.value)
    # Kosher: report-only (processed fish / certification nuance). No assertion.


@pytest.mark.parametrize("ingredient", BROTH_STOCK)
@pytest.mark.parametrize("restriction", BROTH_NEVER_SAFE)
def test_broth_stock_never_firm_safe_on_veg_diets(ingredient: str, restriction: str) -> None:
    st = _status(ingredient, restriction)
    assert st != VerdictStatus.SAFE, (ingredient, restriction, st.value)


@pytest.mark.parametrize("restriction", ALL_FRAMEWORKS)
def test_vegetable_broth_stays_safe_everywhere(restriction: str) -> None:
    st = _status("vegetable broth", restriction)
    assert st == VerdictStatus.SAFE, (restriction, st.value)
