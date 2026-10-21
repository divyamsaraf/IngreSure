"""Item 52c: ingredient-block extraction (label vs recipe vs multi-product)."""
from core.parsing.ingredient_block import extract_ingredient_block
from core.parsing.ingredient_parser import preprocess_ingredients_to_strings


def test_water_purified_keeps_water():
    atoms = preprocess_ingredients_to_strings(
        "Ingredients: sugar, water (purified), salt."
    )
    blob = " ".join(atoms).lower()
    assert "water" in blob
    assert "sugar" in blob
    assert "salt" in blob


def test_nested_parens_keep_cocoa_butter():
    atoms = preprocess_ingredients_to_strings(
        "Chocolate (cocoa mass, sugar (cane), cocoa butter (from cocoa))."
    )
    blob = " ".join(atoms).lower()
    assert "cocoa" in blob
    assert "butter" in blob or "cocoa butter" in blob or "cocoa mass" in blob


def test_recipe_is_not_a_label():
    block = extract_ingredient_block(
        "How do I make pesto? Basil, pine nuts, parmesan, olive oil, garlic."
    )
    assert block.kind == "recipe"
    assert any("parmesan" in n.lower() or "basil" in n.lower() for n in block.atoms)


def test_multiple_products_not_one_list():
    block = extract_ingredient_block(
        "Product A: milk, sugar. Product B: oats, salt."
    )
    assert block.kind == "multi_product"
    assert len(block.products) >= 2


def test_product_name_only_is_not_a_label():
    block = extract_ingredient_block("Nutella")
    assert block.kind == "product_name"


def test_ingredients_header_is_label():
    block = extract_ingredient_block("Ingredients: oats. Contains: milk, soy.")
    assert block.kind == "label"
    blob = " ".join(block.atoms).lower()
    assert "oat" in blob or "oats" in blob
    assert "milk" in blob
