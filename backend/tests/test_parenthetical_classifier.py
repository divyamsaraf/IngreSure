"""A35–A36: parenthetical kinds, function headers, origin-in-brackets."""
from core.parsing.ingredient_parser import preprocess_ingredients_to_strings
from core.parsing.parenthetical import classify_parenthetical


def test_function_header_number_list():
    kind, _ = classify_parenthetical("Emulsifier (322, 471)")
    assert kind == "function_header_numbers"


def test_name_plus_function_phrase():
    kind, _ = classify_parenthetical("soy lecithin (an emulsifier)")
    assert kind == "name_function"


def test_name_plus_origin_hazard():
    kind, _ = classify_parenthetical("lecithin (soya)")
    assert kind == "name_origin"


def test_quantity_parenthetical():
    kind, _ = classify_parenthetical("PEANUTS (49.5%)")
    assert kind == "quantity"


def test_a35_headers_are_not_atoms_numbers_kept():
    atoms = preprocess_ingredients_to_strings(
        "Emulsifier (322, 471), Thickener (412), Acidity regulator (330), "
        "Colour (102, 110), Preservative (202), Antioxidant (E300)"
    )
    blob = " ".join(a.lower() for a in atoms)
    bare = {a.lower().strip() for a in atoms}
    for header in (
        "emulsifier",
        "thickener",
        "acidity regulator",
        "colour",
        "preservative",
        "antioxidant",
    ):
        assert header not in bare, atoms
    for n in ("322", "471", "412", "330", "102", "110", "202", "300"):
        assert n in blob.replace(" ", "") or f"e{n}" in blob.replace(" ", ""), atoms


def test_india_ins_subvariant_not_bare_roman():
    atoms = preprocess_ingredients_to_strings(
        "Emulsifier (INS 322(ii)), acidity regulator (330(iii))"
    )
    bare = {a.lower().strip() for a in atoms}
    assert "ii" not in bare, atoms
    assert "i" not in bare, atoms
    assert "iii" not in bare, atoms
    blob = " ".join(a.lower() for a in atoms)
    assert "322" in blob
    assert "330" in blob


def test_real_india_raising_agent_not_bare_roman():
    atoms = preprocess_ingredients_to_strings(
        "Raising agent (500(ii)), Yeast, Flour treatment agents (516 and 1101(i))"
    )
    bare = {a.lower().strip() for a in atoms}
    assert "ii" not in bare, atoms
    assert "i" not in bare, atoms
    assert "raising agent" not in bare, atoms
    assert "flour treatment agents" not in bare, atoms
    blob = " ".join(a.lower() for a in atoms)
    assert "500" in blob
    assert "516" in blob
    assert "1101" in blob


def test_real_au_function_headers_not_atoms():
    atoms = preprocess_ingredients_to_strings(
        "Thickener (412), Emulsifiers (481, 472e), Preservative (282)"
    )
    bare = {a.lower().strip() for a in atoms}
    assert "thickener" not in bare, atoms
    assert "emulsifiers" not in bare, atoms
    assert "preservative" not in bare, atoms
    blob = "".join(a.lower() for a in atoms)
    assert "412" in blob
    assert "481" in blob
    assert "472" in blob
    assert "282" in blob


def test_function_header_named_payload_drops_header():
    kind, payload = classify_parenthetical("Emulsifier (Soya lecithin)")
    assert kind == "function_header_payload"
    atoms = preprocess_ingredients_to_strings("Emulsifier (Soya lecithin)")
    bare = {a.lower().strip() for a in atoms}
    assert "emulsifier" not in bare, atoms
    blob = " ".join(a.lower() for a in atoms)
    assert "lecithin" in blob or "soya" in blob


def test_sub_ingredient_list_not_name_origin():
    kind, _ = classify_parenthetical("chocolate (sugar, cocoa butter, milk)")
    assert kind == "sub_ingredient_list"
    atoms = preprocess_ingredients_to_strings(
        "chocolate (sugar, cocoa butter, milk), flour"
    )
    blob = " ".join(a.lower() for a in atoms)
    for tok in ("chocolate", "sugar", "cocoa", "milk", "flour"):
        assert tok in blob, atoms


def test_sourdough_wheat_flour_keeps_flour_not_unknown_starter():
    kind, _ = classify_parenthetical("Sourdough (Wheat Flour)")
    assert kind == "name_origin"
    atoms = preprocess_ingredients_to_strings("Sourdough (Wheat Flour)")
    blob = " ".join(a.lower() for a in atoms)
    bare = {a.lower().strip() for a in atoms}
    assert "wheat" in blob
    assert "sourdough" not in bare


def test_a36_keeps_name_and_soya_origin():
    atoms = preprocess_ingredients_to_strings(
        "soy lecithin (an emulsifier), lecithin (soya), flavour (nature identical)"
    )
    blob = " ".join(a.lower() for a in atoms)
    bare = {a.lower().strip() for a in atoms}
    assert "emulsifier" not in bare, atoms
    assert "an emulsifier" not in bare, atoms
    assert "nature identical" not in bare, atoms
    assert "lecithin" in blob or "soy" in blob
    assert "soya" in blob or "soy" in blob
    assert "flavour" in blob or "flavor" in blob
