"""Bracket-less AU/NZ function-class headers, wired through the parser."""
from __future__ import annotations

from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.parsing.bare_function_headers import (
    parse_bare_function_header,
    parse_bare_function_headers,
)
from core.parsing.ingredient_parser import preprocess_ingredients_to_strings


def test_emulsifier_number():
    hit = parse_bare_function_header("Emulsifier 322")
    assert hit is not None
    assert hit.function_class == "emulsifier"
    assert hit.code == "322"
    assert hit.substance is None


def test_acidity_regulator_number():
    hit = parse_bare_function_header("Acidity Regulator 330")
    assert hit is not None
    assert hit.function_class == "acidity_regulator"
    assert hit.code == "330"


def test_emulsifier_named_substance():
    hit = parse_bare_function_header("Emulsifier: soy lecithin")
    assert hit is not None
    assert hit.function_class == "emulsifier"
    assert hit.code is None
    assert hit.substance == "soy lecithin"


def test_real_shaped_au_nz_strings():
    cases = (
        ("Emulsifiers 322, 471", [("emulsifier", "322"), ("emulsifier", "471")]),
        ("Colour 160a", [("colour", "160a")]),
        ("Preservative 202", [("preservative", "202")]),
        ("Raising Agent 500", [("raising_agent", "500")]),
        ("Thickener 415", [("thickener", "415")]),
        ("Antioxidant 306", [("antioxidant", "306")]),
        ("Stabiliser 412", [("stabiliser", "412")]),
        ("Flavour Enhancer 621", [("flavour_enhancer", "621")]),
    )
    for raw, expected in cases:
        hits = parse_bare_function_headers(raw)
        got = [(h.function_class, h.code) for h in hits]
        assert got == expected, (raw, got)


def test_mixed_number_and_named_clause():
    hits = parse_bare_function_headers(
        "Acidity regulator 330, emulsifier: soy lecithin, antioxidant 300"
    )
    assert [(h.function_class, h.code, h.substance) for h in hits] == [
        ("acidity_regulator", "330", None),
        ("emulsifier", None, "soy lecithin"),
        ("antioxidant", "300", None),
    ]


def test_plain_ingredient_is_not_a_header():
    assert parse_bare_function_header("soy lecithin") is None
    assert parse_bare_function_headers("water, sugar, salt") == []


def _compact(atoms: list[str]) -> set[str]:
    return {a.lower().replace(" ", "") for a in atoms}


def test_parser_emulsifier_number():
    atoms = preprocess_ingredients_to_strings("Emulsifier 322")
    assert not any("emulsifier" in a.lower() for a in atoms), atoms
    assert "e322" in _compact(atoms), atoms


def test_parser_acidity_regulator_number():
    atoms = preprocess_ingredients_to_strings("Acidity Regulator 330")
    assert not any("acidity" in a.lower() for a in atoms), atoms
    assert "e330" in _compact(atoms), atoms


def test_parser_emulsifier_named_substance_keeps_soy():
    atoms = preprocess_ingredients_to_strings("Emulsifier: soy lecithin")
    assert not any("emulsifier" in a.lower() for a in atoms), atoms
    assert any("soy" in a.lower() and "lecithin" in a.lower() for a in atoms), atoms
    soy_atom = next(a for a in atoms if "lecithin" in a.lower())
    assert derive_identity_flags(soy_atom).get("soy_source") is True


def test_parser_emulsifiers_code_list():
    atoms = preprocess_ingredients_to_strings("Emulsifiers 322, 471")
    compact = _compact(atoms)
    assert not any("emulsifier" in a.lower() for a in atoms), atoms
    assert "e322" in compact, atoms
    assert "e471" in compact, atoms


def test_parser_colour_160a():
    atoms = preprocess_ingredients_to_strings("Colour 160a")
    assert not any("colour" in a.lower() or "color" in a.lower() for a in atoms), atoms
    assert "e160a" in _compact(atoms), atoms


def test_parser_mixed_clause_does_not_drop_soy():
    atoms = preprocess_ingredients_to_strings(
        "Acidity regulator 330, emulsifier: soy lecithin, antioxidant 300"
    )
    compact = _compact(atoms)
    assert not any(
        any(h in a.lower() for h in ("emulsifier", "acidity", "antioxidant"))
        for a in atoms
    ), atoms
    assert "e330" in compact, atoms
    assert "e300" in compact, atoms
    soy_atom = next(a for a in atoms if "lecithin" in a.lower())
    assert "soy" in soy_atom.lower()
    assert derive_identity_flags(soy_atom).get("soy_source") is True


def test_parser_plain_list_unchanged():
    atoms = preprocess_ingredients_to_strings("water, sugar, salt")
    assert atoms == ["water", "sugar", "salt"]
