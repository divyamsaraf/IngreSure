"""Asserted clears must be enumerated exceptions — never drop a real positive.

Reconcile's sticky-OR is the default. Transform-emitted asserted falses are the
only way to clear a stored true; they must come from a reviewed list, and must
not clear a flag when the name matches that family's positive lexicon unless
the name is an explicit exception.
"""
from core.external_apis.usda_fdc import (
    REVIEWED_SHELLFISH_FALSE_FRIENDS,
    asserted_clear_allowed,
    _infer_flags_from_text,
)
from core.normalization.normalizer import normalize_ingredient_key
from scripts.transform_usda_fdc_bulk import _food_to_layer1_row


def test_oyster_sauce_not_on_false_friend_list_and_stays_shellfish():
    norm = normalize_ingredient_key("Oyster sauce")
    assert norm not in REVIEWED_SHELLFISH_FALSE_FRIENDS
    flags = _infer_flags_from_text("Oyster sauce", category="Soups, Sauces, and Gravies")
    assert flags["shellfish_source"] is True


def test_asserted_false_cannot_clear_shellfish_on_lexicon_hit_unless_exception():
    assert asserted_clear_allowed("oyster sauce", "shellfish_source") is False
    assert asserted_clear_allowed("mushrooms oyster raw", "shellfish_source") is True


def test_asserted_false_cannot_clear_egg_on_eggnog_or_custard():
    for name in ("eggnog", "custard dry mix", "quiche lorraine", "cheese souffle"):
        assert asserted_clear_allowed(name, "egg_source") is False, name
        assert asserted_clear_allowed(name, "dairy_source") is False, name


def test_butter_clear_egg_only_if_reviewed():
    """Dairy↔egg asserted clears are list-gated, not category-wide."""
    from core.external_apis.usda_fdc import REVIEWED_ASSERTED_CLEARS

    butter = normalize_ingredient_key("Butter, without salt")
    assert (butter, "egg_source") in REVIEWED_ASSERTED_CLEARS
    assert asserted_clear_allowed(butter, "egg_source") is True


def test_transform_does_not_assert_clear_processed_or_unlisted():
    cheese_sauce = _food_to_layer1_row(
        {
            "description": "Cheese sauce, prepared from recipe",
            "foodCategory": {"description": "Dairy and Egg Products"},
        },
        strict=False,
    )
    # May omit egg_source (true-only emit), but must not assert-clear it.
    af = cheese_sauce.get("asserted_flags") or []
    assert "egg_source" not in af
    assert asserted_clear_allowed(
        cheese_sauce["canonical_name"], "egg_source"
    ) is False


def test_transform_emits_clear_only_for_reviewed_shellfish_false_friend():
    mushroom = _food_to_layer1_row(
        {
            "description": "Mushrooms, oyster, raw",
            "foodCategory": {"description": "Vegetables and Vegetable Products"},
        },
        strict=False,
    )
    assert mushroom["shellfish_source"] is False
    assert "shellfish_source" in mushroom["asserted_flags"]

    # Unlisted oyster-ish name must not get an asserted shellfish clear.
    # (If somehow inferred false, still no asserted_flags clear entry.)
    row = _food_to_layer1_row(
        {
            "description": "Oyster sauce",
            "foodCategory": {"description": "Soups, Sauces, and Gravies"},
        },
        strict=False,
    )
    assert row.get("shellfish_source") is True
    assert "shellfish_source" not in (row.get("asserted_flags") or [])
