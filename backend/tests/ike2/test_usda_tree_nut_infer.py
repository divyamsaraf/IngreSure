"""USDA tree_nut_source: name lexicon ∩ evidence — never category alone."""
from core.external_apis.usda_fdc import _infer_flags_from_text


def test_almond_in_nut_category_is_tree_nut():
    flags = _infer_flags_from_text(
        "Nuts, almonds", category="Nut and Seed Products"
    )
    assert flags["nut_source"] == "tree_nut"
    assert flags.get("tree_nut_source") is True


def test_sunflower_seed_not_tree_nut():
    for name in (
        "Seeds, sunflower seed kernels, dried",
        "Seeds, pumpkin and squash seed kernels, roasted",
        "Seeds, sesame seeds, whole, dried",
        "Seeds, flaxseed",
        "Seeds, chia seeds, dried",
    ):
        flags = _infer_flags_from_text(name, category="Nut and Seed Products")
        assert flags.get("tree_nut_source") is not True, name
        assert flags.get("nut_source") != "tree_nut", name


def test_nut_and_seed_category_alone_not_tree_nut():
    flags = _infer_flags_from_text(
        "Seeds, mixed, roasted", category="Nut and Seed Products"
    )
    assert flags.get("tree_nut_source") is not True
    assert flags.get("nut_source") != "tree_nut"


def test_coconut_and_nutmeg_not_tree_nut():
    for name, cat in (
        ("Nuts, coconut meat, raw", "Nut and Seed Products"),
        ("Spices, nutmeg, ground", "Spices and Herbs"),
    ):
        flags = _infer_flags_from_text(name, category=cat)
        assert flags.get("tree_nut_source") is not True, name
        assert flags.get("nut_source") != "tree_nut", name


def test_pine_brazil_chestnut_filbert_are_tree_nut():
    for name in (
        "Nuts, pine nuts, dried",
        "Nuts, brazilnuts, dried",
        "Nuts, chestnuts, european, raw, peeled",
        "Nuts, hazelnuts or filberts",
    ):
        flags = _infer_flags_from_text(name, category="Nut and Seed Products")
        assert flags.get("tree_nut_source") is True, name


def test_almond_milk_beverage_still_tree_nut_by_name():
    """Name lexicon fires outside Nut and Seed Products; category alone never does."""
    flags = _infer_flags_from_text(
        "Almond milk, unsweetened, plain, refrigerated",
        category="Beverages",
    )
    assert flags.get("tree_nut_source") is True
