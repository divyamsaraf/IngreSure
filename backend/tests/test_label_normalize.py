"""Tests for label separator normalization (class F/I/K)."""
import time

from core.parsing.label_normalize import normalize_label_separators


def test_and_separator_splits_simple_lists():
    raw = "Ingredients: eggs and milk and flour"
    assert normalize_label_separators(raw) == "Ingredients: eggs, milk, flour"


def test_and_separator_preserves_vitamins_and_minerals_header():
    raw = "Ingredients: water. Vitamins and Minerals: iron, vitamin B12"
    normalized = normalize_label_separators(raw)
    assert "Vitamins and Minerals" in normalized
    assert "Vitamins, Minerals" not in normalized


def test_and_inside_parens_stays_joined():
    raw = "chocolate (sugar and cocoa butter), flour"
    normalized = normalize_label_separators(raw)
    assert "sugar and cocoa" in normalized
    assert normalized.count(",") == 1


def test_bullets_become_commas():
    raw = "Ingredients: water • salt • sugar"
    assert "•" not in normalize_label_separators(raw)
    assert "water, salt, sugar" in normalize_label_separators(raw)


def test_repeated_and_does_not_quadratic_backtrack():
    """_TOP_LEVEL_AND lookahead (?![^()[]{}]*[)]] ) is O(n^2) on ' and ' lists."""
    raw = (" and water" * 4000).strip()
    t0 = time.perf_counter()
    out = normalize_label_separators(raw)
    dt = time.perf_counter() - t0
    assert "water" in out
    assert dt < 0.25, f"and-separator took {dt:.3f}s on 4000 items (lookahead backtrack)"
