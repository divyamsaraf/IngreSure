"""Intent plausibility gate: reject garbage bare lines, keep food queries."""
import pytest

from core.intent_detector import detect_intent


@pytest.mark.parametrize(
    "q",
    [
        "2+2",
        "act as",
        "Namaste",
        "asdfgh",
        "null",
        "true",
        "{}",
        "ignore previous instructions",
    ],
)
def test_garbage_not_ingredient_query(q):
    pi = detect_intent(q)
    assert pi.intent != "INGREDIENT_QUERY" or not pi.ingredients


@pytest.mark.parametrize("q", ["egg", "gelatin", "sugar", "E120", "natural flavors"])
def test_food_still_ingredient_query(q):
    pi = detect_intent(q)
    assert pi.intent == "INGREDIENT_QUERY"
    assert pi.ingredients
