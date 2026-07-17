from core.knowledge.ike2.input_layer import to_atoms


def test_compound_parenthetical_expands_to_inner_source():
    assert "soy lecithin" in to_atoms("emulsifier (soy lecithin)")


def test_source_qualifier_reduces_to_base():
    atoms = to_atoms("sugar (from beet)")
    assert atoms == ["sugar"]


def test_splits_multiple_ingredients():
    atoms = to_atoms("water, salt, citric acid")
    assert atoms == ["water", "salt", "citric acid"]


def test_trace_section_marks_subsequent_ingredients():
    from core.knowledge.ike2.input_layer import parse_atoms

    atoms = parse_atoms("flour, less than 2% of: soy lecithin, salt")
    by_name = {a.name: a.trace for a in atoms}
    assert by_name.get("flour") is False
    assert by_name.get("soy lecithin") is True
    assert by_name.get("salt") is True


def test_trace_marker_in_same_segment():
    from core.knowledge.ike2.input_layer import parse_atoms

    atoms = parse_atoms("water, contains 2% or less: peanuts")
    by_name = {a.name: a.trace for a in atoms}
    assert by_name.get("water") is False
    assert by_name.get("peanut") is True


def test_may_contain_section_marks_allergen_statement():
    from core.knowledge.ike2.input_layer import parse_atoms

    atoms = parse_atoms("water, flour. May contain: peanuts")
    by_name = {a.name: a for a in atoms}
    assert by_name.get("water").may_contain is False
    assert by_name.get("flour").may_contain is False
    peanut = next(a for a in atoms if "peanut" in a.name)
    assert peanut.may_contain is True
    assert peanut.trace is False


def test_parse_atoms_bread_label_matches_bridge():
    from core.bridge import preprocess_ingredient_list
    from core.knowledge.ike2.input_layer import parse_atoms
    from tests.test_label_decomposer import BREAD_LABEL

    bridge_atoms, trace_keys, _ = preprocess_ingredient_list([BREAD_LABEL])
    ike2_atoms = {a.name for a in parse_atoms(BREAD_LABEL)}
    assert "wheat gluten" in ike2_atoms
    assert "enzymes" in ike2_atoms
    assert not any("[" in a for a in ike2_atoms)
    for atom in bridge_atoms:
        assert atom in ike2_atoms, f"bridge atom {atom} missing from IKE-2"
    for name, trace in ((a, a in trace_keys) for a in ike2_atoms):
        ike2_trace = next(x.trace for x in parse_atoms(BREAD_LABEL) if x.name == name)
        if name in trace_keys:
            assert ike2_trace is True, name
