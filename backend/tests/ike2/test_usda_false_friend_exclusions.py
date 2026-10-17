"""USDA false-friend exclusions (Item 42 follow-up).

Shellfish name false friends are a regression from the Item-37 name/category
kind splitter. Dairy↔egg swaps come from the original category rule on
\"Dairy and Egg Products\" (\"egg\" ∈ category string + dairy_source for all).
"""
from core.external_apis.usda_fdc import _infer_flags_from_text


def test_oyster_mushroom_word_orders_not_shellfish():
    for name in (
        "Mushrooms, oyster, raw",
        "oyster mushroom dried",
        "Oyster mushrooms, raw",
        "Mushroom, king oyster",
    ):
        flags = _infer_flags_from_text(name, category="Vegetables and Vegetable Products")
        assert flags["shellfish_source"] is False, name


def test_emu_ostrich_oyster_not_shellfish():
    for name in ("Emu, oyster, raw", "Ostrich, oyster, raw"):
        flags = _infer_flags_from_text(
            name, category="Lamb, Veal, and Game Products"
        )
        assert flags["shellfish_source"] is False, name


def test_squash_scallop_and_salsify_not_shellfish():
    for name, cat in (
        ("Squash, summer, scallop, raw", "Vegetables and Vegetable Products"),
        ("Salsify, (vegetable oyster), raw", "Vegetables and Vegetable Products"),
    ):
        flags = _infer_flags_from_text(name, category=cat)
        assert flags["shellfish_source"] is False, name


def test_real_oyster_still_shellfish():
    flags = _infer_flags_from_text(
        "Mollusks, oyster, eastern, wild, raw",
        category="Finfish and Shellfish Products",
    )
    assert flags["shellfish_source"] is True
    assert flags["fish_source"] is False


def test_dairy_egg_category_does_not_cross_flag():
    egg = _infer_flags_from_text(
        "Egg, whole, raw, fresh", category="Dairy and Egg Products"
    )
    assert egg["egg_source"] is True
    assert egg["dairy_source"] is False

    dairy = _infer_flags_from_text(
        "Butter, without salt", category="Dairy and Egg Products"
    )
    assert dairy["dairy_source"] is True
    assert dairy["egg_source"] is False


def test_real_shellfish_lexicon_expansions():
    for name in (
        "Crayfish, raw",
        "Crawfish, raw",
        "Langoustine, raw",
        "Krill, dried",
        "Yabby, raw",
    ):
        flags = _infer_flags_from_text(
            name, category="Finfish and Shellfish Products"
        )
        assert flags["shellfish_source"] is True, name


def test_layer1_emit_asserted_clears_for_sticky_or():
    """Transform must ship asserted falses so re-inject can clear sticky OR trues."""
    from scripts.transform_usda_fdc_bulk import _food_to_layer1_row

    mushroom = _food_to_layer1_row(
        {
            "description": "Mushrooms, oyster, raw",
            "foodCategory": {"description": "Vegetables and Vegetable Products"},
        },
        strict=False,
    )
    assert mushroom["shellfish_source"] is False
    assert mushroom["animal_origin"] is False
    assert "shellfish_source" in mushroom["asserted_flags"]
    assert "animal_origin" in mushroom["asserted_flags"]

    butter = _food_to_layer1_row(
        {
            "description": "Butter, without salt",
            "foodCategory": {"description": "Dairy and Egg Products"},
        },
        strict=False,
    )
    assert butter["dairy_source"] is True
    assert butter["egg_source"] is False
    assert "egg_source" in butter["asserted_flags"]

    egg = _food_to_layer1_row(
        {
            "description": "Egg, whole, raw, fresh",
            "foodCategory": {"description": "Dairy and Egg Products"},
        },
        strict=False,
    )
    assert egg["egg_source"] is True
    assert egg["dairy_source"] is False
    assert "dairy_source" in egg["asserted_flags"]
