"""
Flatten ingredient strings for evaluation: split parentheses, commas, map processed foods to base ingredients.
"""
import re
import logging
from typing import List

from core.normalization.normalizer import normalize_ingredient_key
from core.parsing.ingredient_parser import (
    _label_clauses,
    _segment_canonical,
    _TOP_LEVEL_SEP,
    strip_label_boilerplate,
)
from core.parsing.nesting_split import split_by_nesting

logger = logging.getLogger(__name__)

# Processed food -> base ingredients (deterministic; no hallucination)
# Keys normalized (lower, no extra spaces). Values are base ingredients for ontology lookup.
PROCESSED_FOOD_TO_BASE: dict[str, List[str]] = {
    "potato chips": ["potato", "vegetable oil", "salt"],
    "potato chip": ["potato", "vegetable oil", "salt"],
    "french fries": ["potato", "vegetable oil", "salt"],
    "french fry": ["potato", "vegetable oil", "salt"],
    "tortilla chips": ["corn", "vegetable oil", "salt"],
    "tortilla chip": ["corn", "vegetable oil", "salt"],
    "corn chips": ["corn", "vegetable oil", "salt"],
    "corn chip": ["corn", "vegetable oil", "salt"],
    "pretzels": ["wheat flour", "salt", "yeast"],
    "pretzel": ["wheat flour", "salt", "yeast"],
    "crackers": ["wheat flour", "vegetable oil", "salt"],
    "cracker": ["wheat flour", "vegetable oil", "salt"],
    "bread": ["wheat flour", "water", "salt", "yeast"],
    "white bread": ["wheat flour", "water", "salt", "yeast"],
    "pasta": ["wheat flour", "water", "egg"],
    "spaghetti": ["wheat flour", "water", "egg"],
    "macaroni": ["wheat flour", "water", "egg"],
    "noodles": ["wheat flour", "water", "egg"],
    "rice noodles": ["rice flour", "water"],
    "couscous": ["wheat flour", "water"],
    "hummus": ["chickpea", "sesame", "olive oil", "lemon", "garlic"],
    "ketchup": ["tomato", "sugar", "vinegar", "salt"],
    "mustard": ["mustard seed", "vinegar", "salt"],
    "mayonnaise": ["egg", "vegetable oil", "vinegar"],
    "salsa": ["tomato", "onion", "pepper", "lime", "salt"],
    "soy sauce": ["soybean", "wheat", "salt", "water"],
    "teriyaki sauce": ["soy sauce", "sugar", "ginger", "garlic"],
    "bbq sauce": ["tomato", "vinegar", "sugar", "molasses"],
    "hot sauce": ["pepper", "vinegar", "salt"],
    "peanut butter": ["peanut", "salt", "vegetable oil"],
    "almond butter": ["almond", "salt", "vegetable oil"],
    "jam": ["fruit", "sugar", "pectin"],
    "jelly": ["fruit juice", "sugar", "pectin"],
    "marmalade": ["citrus", "sugar", "pectin"],
    "chocolate": ["cocoa", "sugar", "cocoa butter", "milk"],
    "dark chocolate": ["cocoa", "sugar", "cocoa butter"],
    "milk chocolate": ["cocoa", "sugar", "cocoa butter", "milk"],
    "ice cream": ["milk", "cream", "sugar", "egg"],
    "yogurt": ["milk", "bacterial culture"],
    "cheese": ["milk", "salt", "rennet"],
    "butter": ["milk", "salt"],
    "tofu": ["soybean", "water"],
    "tempeh": ["soybean", "water"],
    "seitan": ["wheat gluten", "water"],
    "plant-based meat": ["soy", "wheat", "vegetable oil", "flavoring"],
    "veggie burger": ["vegetable", "legume", "grain", "binding"],
    "vegan cheese": ["coconut oil", "starch", "flavoring"],
    "oat milk": ["oat", "water"],
    "almond milk": ["almond", "water"],
    "soy milk": ["soybean", "water"],
    "rice milk": ["rice", "water"],
    "coconut milk": ["coconut", "water"],
}

# Category expansion: "X (A, B, C)" -> ["A suffix", "B suffix", "C suffix"] when X is a known category.
# Normalized category key -> suffix to append to each parenthetical item (e.g. " oil" -> "sunflower oil").
CATEGORY_EXPAND: dict[str, str] = {
    "vegetable oil": " oil",
    "oil": " oil",
    "nut": " nut",
    "nuts": " nut",
    "starch": " starch",
    "starches": " starch",
    "flour": " flour",
    "flours": " flour",
    "gum": " gum",
    "gums": " gum",
    "protein": " protein",
    "proteins": " protein",
    "emulsifier": " emulsifier",
    "emulsifiers": " emulsifier",
    "stabilizer": " stabilizer",
    "stabilizers": " stabilizer",
}


def _expand_category_parenthetical(parts: List[str]) -> List[str]:
    """
    If parts is [category, item1, item2, ...] and category is in CATEGORY_EXPAND,
    return [item1 + suffix, item2 + suffix, ...]. Otherwise return parts as-is.
    """
    if not parts or len(parts) < 2:
        return parts
    first_norm = normalize_ingredient_key(parts[0])
    suffix = CATEGORY_EXPAND.get(first_norm)
    if suffix is None:
        return parts
    out: List[str] = []
    for p in parts[1:]:
        p = p.strip()
        if not p:
            continue
        # e.g. "sunflower" + " oil" -> "sunflower oil"
        combined = (p + suffix).strip()
        if combined:
            out.append(combined)
    return out if out else parts


def flatten_ingredients(raw_str: str) -> List[str]:
    """
    Flatten a raw ingredient string into a list of normalized base ingredients.

    1. Normalize and check processed-food map (e.g. "potato chips" -> ["potato", "vegetable oil", "salt"]).
    2. Otherwise split by commas (respecting parentheses) and by parentheses; flatten.
    3. Normalize each part and return deduplicated list (order preserved).

    Handles:
    - "Enriched Bleached Wheat Flour (Bleached Wheat Flour, Niacin, Folic Acid)"
      -> ["enriched bleached wheat flour", "bleached wheat flour", "niacin", "folic acid"]
    - "potato chips" -> ["potato", "vegetable oil", "salt"]
    """
    if not raw_str or not isinstance(raw_str, str):
        return []
    raw_str = strip_label_boilerplate(raw_str)
    if not raw_str:
        return []

    # Check processed food first (whole string normalized)
    key = normalize_ingredient_key(raw_str)
    if key in PROCESSED_FOOD_TO_BASE:
        return list(PROCESSED_FOOD_TO_BASE[key])

    flat: List[str] = []
    for clause in _label_clauses(raw_str):
        for seg in _TOP_LEVEL_SEP.split(clause):
            seg = seg.strip()
            if not seg:
                continue
            collapsed = _segment_canonical(seg)
            if collapsed != seg:
                parts = [collapsed]
            else:
                parts = split_by_nesting(seg)
            parts = _expand_category_parenthetical(parts)
            for p in parts:
                p = p.strip()
                if not p:
                    continue
                pk = normalize_ingredient_key(p)
                if pk in PROCESSED_FOOD_TO_BASE:
                    flat.extend(PROCESSED_FOOD_TO_BASE[pk])
                elif pk:
                    flat.append(pk)

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: List[str] = []
    for item in flat:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
