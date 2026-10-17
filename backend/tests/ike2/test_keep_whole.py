"""Item 2 Prompt 4: keep-whole / anti-recipe registry."""
from __future__ import annotations

import json
from pathlib import Path

from core.compound_expansion import expand_compounds
from core.knowledge.ike2.keep_whole import (
    clear_keep_whole_cache,
    is_keep_whole,
    load_keep_whole_names,
)
from core.normalization.parser import PROCESSED_FOOD_TO_BASE, flatten_ingredients


def test_tempeh_is_keep_whole_by_default():
    clear_keep_whole_cache()
    assert is_keep_whole("tempeh") is True
    assert is_keep_whole("TEMPEH") is True


def test_tofu_is_not_keep_whole():
    """Tofu may still recipe-expand; keep-whole is process-identity foods only."""
    clear_keep_whole_cache()
    assert is_keep_whole("tofu") is False


def test_flatten_tempeh_stays_whole_even_if_recipe_map_has_entry(monkeypatch):
    """Keep-whole beats PROCESSED_FOOD_TO_BASE (tempeh Rhizopus identity)."""
    monkeypatch.setitem(PROCESSED_FOOD_TO_BASE, "tempeh", ["soybean", "water"])
    assert flatten_ingredients("tempeh") == ["tempeh"]


def test_adding_keep_whole_entry_prevents_destructive_expansion(tmp_path, monkeypatch):
    path = tmp_path / "keep_whole.json"
    path.write_text(
        json.dumps({"keep_whole": ["mock fungus cake", "tempeh"]}),
        encoding="utf-8",
    )
    clear_keep_whole_cache()
    monkeypatch.setattr(
        "core.knowledge.ike2.keep_whole._DEFAULT_PATH",
        path,
    )
    monkeypatch.setitem(
        PROCESSED_FOOD_TO_BASE,
        "mock fungus cake",
        ["soybean", "water"],
    )
    assert is_keep_whole("mock fungus cake") is True
    assert flatten_ingredients("mock fungus cake") == ["mock fungus cake"]


def test_keep_whole_phrase_skips_keyword_tear_in_expand():
    """Bare registry phrase stays whole (no soy-only collapse)."""
    clear_keep_whole_cache()
    # Register multi-word keep-whole via cache override is harder; use tempeh alone.
    expanded, _, derived = expand_compounds(["tempeh"], role_index={})
    assert expanded == ["tempeh"]
    assert derived == {}


def test_load_keep_whole_includes_documented_peers():
    names = load_keep_whole_names()
    for peer in ("tempeh", "miso", "koji", "natto", "yeast", "mycoprotein"):
        assert peer in names, peer
