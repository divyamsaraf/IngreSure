"""Tests for label separator normalization (class F/I/K)."""
from core.parsing.label_normalize import normalize_label_separators


def test_and_separator_splits_simple_lists():
    raw = "Ingredients: eggs and milk and flour"
    assert normalize_label_separators(raw) == "Ingredients: eggs, milk, flour"


def test_and_separator_preserves_vitamins_and_minerals_header():
    raw = "Ingredients: water. Vitamins and Minerals: iron, vitamin B12"
    normalized = normalize_label_separators(raw)
    assert "Vitamins and Minerals" in normalized
    assert "Vitamins, Minerals" not in normalized


def test_bullets_become_commas():
    raw = "Ingredients: water • salt • sugar"
    assert "•" not in normalize_label_separators(raw)
    assert "water, salt, sugar" in normalize_label_separators(raw)
