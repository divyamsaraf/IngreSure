"""LLM verdict explanation guards — pattern-class, not per-query."""
from core.llm_response import _explanation_introduces_unflagged_terms


def test_rejects_gelatin_when_only_pork_flagged():
    text = (
        "This product contains gelatin derived from pork skin and bones, "
        "making it unsuitable for vegetarians."
    )
    assert _explanation_introduces_unflagged_terms(text, ["pork", "beef"]) is True


def test_allows_gelatin_when_gelatin_flagged():
    text = "Gelatin is animal-derived and not vegetarian-friendly."
    assert _explanation_introduces_unflagged_terms(text, ["gelatin"]) is False


def test_allows_pork_explanation_when_pork_flagged():
    text = "Pork is meat and not suitable for a vegetarian diet."
    assert _explanation_introduces_unflagged_terms(text, ["pork"]) is False


def test_rejects_lamb_explanation_when_chicken_flagged():
    text = (
        "Lamb variety meats and by-products mechanically separated raw are unsuitable "
        "for Vegetarian diets due to animal parts."
    )
    assert _explanation_introduces_unflagged_terms(
        text, ["mechanically separated chicken"]
    ) is True


def test_allows_chicken_explanation_when_chicken_flagged():
    text = "Mechanically separated chicken is poultry and not vegetarian."
    assert _explanation_introduces_unflagged_terms(
        text, ["mechanically separated chicken"]
    ) is False
