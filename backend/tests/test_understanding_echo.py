"""Item 52d: understanding echo — say what was parsed and what was not."""
from core.parsing.understanding_echo import compose_understanding_echo


def test_echo_lists_understood_atoms_and_unparsed():
    text = compose_understanding_echo(
        eval_names=["oats", "salt"],
        unparsed=["barcode 8901030865999"],
        block_kind="label",
        restriction_ids=["gluten_free"],
    )
    low = text.lower()
    assert "oats" in low
    assert "salt" in low
    assert "barcode" in low or "did not" in low or "couldn't" in low or "could not" in low
    assert "gluten" in low


def test_echo_recipe_kind():
    text = compose_understanding_echo(
        eval_names=["basil", "parmesan"],
        unparsed=[],
        block_kind="recipe",
        restriction_ids=["dairy_free"],
    )
    assert "recipe" in text.lower()


def test_echo_empty_is_honest():
    text = compose_understanding_echo(
        eval_names=[],
        unparsed=["Nutella"],
        block_kind="product_name",
        restriction_ids=[],
    )
    low = text.lower()
    assert "nutella" in low
    assert "ingredient" in low
