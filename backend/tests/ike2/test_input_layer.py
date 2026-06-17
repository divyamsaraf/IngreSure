from core.knowledge.ike2.input_layer import to_atoms


def test_compound_parenthetical_expands_to_inner_source():
    assert "soy lecithin" in to_atoms("emulsifier (soy lecithin)")


def test_source_qualifier_reduces_to_base():
    atoms = to_atoms("sugar (from beet)")
    assert atoms == ["sugar"]


def test_splits_multiple_ingredients():
    atoms = to_atoms("water, salt, citric acid")
    assert atoms == ["water", "salt", "citric acid"]
