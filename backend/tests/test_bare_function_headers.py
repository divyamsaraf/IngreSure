"""Bracket-less AU/NZ function-class headers. Helper only — not wired to the parser."""
from __future__ import annotations

from core.parsing.bare_function_headers import (
    parse_bare_function_header,
    parse_bare_function_headers,
)


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
