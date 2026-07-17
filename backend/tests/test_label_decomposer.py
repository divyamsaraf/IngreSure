"""Tests for unified label decomposition (classes A–G)."""
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "labels" / "corpus.json"

BREAD_LABEL = next(
    c["raw"] for c in json.loads(FIXTURES.read_text()) if c["id"] == "sourdough_bread"
)


def _load_fixtures():
    return json.loads(FIXTURES.read_text())


def test_split_by_nesting_brackets():
    from core.parsing.nesting_split import split_by_nesting

    out = split_by_nesting("Enriched Wheat Flour [Flour, Malted Barley Flour]")
    assert "Enriched Wheat Flour" in out
    assert "Flour" in out
    assert "Malted Barley Flour" in out


@pytest.mark.parametrize("case", _load_fixtures(), ids=lambda c: c["id"])
def test_decompose_label_fixtures(case):
    from core.parsing.label_decomposer import decompose_label

    items = decompose_label(case["raw"])
    names = [i.name for i in items]
    by_trace = {i.name: i.trace for i in items}

    for token in case.get("must_include", []):
        assert any(token in n for n in names), f"{case['id']}: missing {token} in {names}"

    if case.get("must_not_include_brackets"):
        assert not any("[" in n or "]" in n for n in names), names

    if case.get("must_not_include_prefix"):
        assert not any(n.startswith("ingredients") for n in names), names

    for atom in case.get("trace_atoms", []):
        match = next((n for n in names if atom in n), None)
        assert match is not None, f"{case['id']}: trace atom {atom} not found"
        assert by_trace.get(match) is True, f"{case['id']}: {match} should be trace"

    for atom in case.get("non_trace_atoms", []):
        match = next((n for n in names if atom in n), None)
        assert match is not None
        assert by_trace.get(match) is False, f"{case['id']}: {match} should not be trace"

    by_may_contain = {i.name: i.may_contain for i in items}
    for atom in case.get("may_contain_atoms", []):
        match = next((n for n in names if atom in n), None)
        assert match is not None, f"{case['id']}: may_contain atom {atom} not found"
        assert by_may_contain.get(match) is True, f"{case['id']}: {match} should be may_contain"

    for atom in case.get("non_may_contain_atoms", []):
        match = next((n for n in names if atom in n), None)
        assert match is not None
        assert by_may_contain.get(match) is False, f"{case['id']}: {match} should not be may_contain"


def test_preprocess_strips_composition_prefix():
    from core.parsing.ingredient_parser import preprocess_ingredients

    items = preprocess_ingredients("Composition: water, salt")
    names = [x["name"] for x in items]
    assert "water" in names
    assert "salt" in names
