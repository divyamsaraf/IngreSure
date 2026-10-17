"""Item 11: asserted_flags on Ingredient serializers (§8.1)."""
from core.ontology.ingredient_schema import Ingredient


def test_to_dict_from_dict_round_trip_asserted_flags():
    ing = Ingredient(
        id="x",
        canonical_name="x",
        asserted_flags=["synthetic", "plant_origin"],
    )
    d = ing.to_dict()
    assert d["asserted_flags"] == ["synthetic", "plant_origin"]
    back = Ingredient.from_dict(d)
    assert back.asserted_flags == ["synthetic", "plant_origin"]


def test_from_dict_missing_asserted_flags_is_empty():
    ing = Ingredient.from_dict({"id": "x", "canonical_name": "x"})
    assert ing.asserted_flags == []
    assert "asserted_flags" in ing.to_dict()
    assert ing.to_dict()["asserted_flags"] == []


def test_from_dict_null_asserted_flags_is_empty():
    ing = Ingredient.from_dict({
        "id": "x",
        "canonical_name": "x",
        "asserted_flags": None,
    })
    assert ing.asserted_flags == []
