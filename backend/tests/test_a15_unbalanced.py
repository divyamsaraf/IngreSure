"""A15: unbalanced brackets must recover members, not drop them."""
from core.parsing.ingredient_parser import preprocess_ingredients_to_strings


def test_unbalanced_parens_keep_wheat_and_sugar():
    atoms = preprocess_ingredients_to_strings("flour (wheat, sugar (unbalanced brackets)")
    blob = " ".join(atoms).lower()
    assert "wheat" in blob
    assert "sugar" in blob
    assert "flour" in blob


def test_unbalanced_nested_does_not_crash():
    atoms = preprocess_ingredients_to_strings("flour (wheat, sugar (cane")
    blob = " ".join(atoms).lower()
    assert "wheat" in blob
    assert "sugar" in blob or "cane" in blob
