"""Dairy/egg: name lexicon only — never Dairy and Egg Products alone."""
from core.external_apis.usda_fdc import _infer_flags_from_text


def test_dairy_egg_category_alone_sets_neither():
    flags = _infer_flags_from_text(
        "Food, prepared, unspecified",
        category="Dairy and Egg Products",
    )
    assert flags["dairy_source"] is False
    assert flags["egg_source"] is False


def test_butter_dairy_not_egg_by_name():
    flags = _infer_flags_from_text(
        "Butter, without salt", category="Dairy and Egg Products"
    )
    assert flags["dairy_source"] is True
    assert flags["egg_source"] is False


def test_egg_whole_egg_not_dairy_by_name():
    flags = _infer_flags_from_text(
        "Egg, whole, raw, fresh", category="Dairy and Egg Products"
    )
    assert flags["egg_source"] is True
    assert flags["dairy_source"] is False


def test_kefir_and_whipped_topping_not_egg():
    for name in (
        "Kefir, lowfat, plain, Lifeway",
        "Whipped topping, frozen, low fat",
        "Dessert topping, powdered",
    ):
        flags = _infer_flags_from_text(name, category="Dairy and Egg Products")
        assert flags["egg_source"] is False, name


def test_nut_implying_products_are_tree_nut():
    for name in (
        "Candies, marzipan",
        "Candies, nougat with almonds",
        "Chocolate, gianduja",
        "Frangipane filling",
        "Amaretto flavor syrup",
        "Sauce, pesto, ready-to-serve",
    ):
        flags = _infer_flags_from_text(name, category="Sweets")
        assert flags.get("tree_nut_source") is True, name


def test_custard_apple_fruit_not_dairy_egg():
    flags = _infer_flags_from_text(
        "Custard-apple, (bullock's-heart), raw",
        category="Fruits and Fruit Juices",
    )
    assert flags["dairy_source"] is False
    assert flags["egg_source"] is False
    assert flags["animal_origin"] is False
    assert flags["plant_origin"] is True


def test_dessert_custard_still_dairy_and_egg():
    flags = _infer_flags_from_text("Custard, prepared from recipe", category="Sweets")
    assert flags["dairy_source"] is True
    assert flags["egg_source"] is True
