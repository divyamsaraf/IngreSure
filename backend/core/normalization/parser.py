"""
Flatten ingredient strings for evaluation: split parentheses, commas, map processed foods to base ingredients.
"""
import re
import logging
from typing import List

from core.normalization.normalizer import normalize_ingredient_key

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


def _split_by_parentheses(text: str) -> List[str]:
    """
    Split by top-level parentheses; commas inside parentheses become separate items.
    'Enriched Flour (Wheat Flour, Niacin, Iron)' -> ['Enriched Flour', 'Wheat Flour', 'Niacin', 'Iron']
    """
    if not text or not text.strip():
        return []
    out: List[str] = []
    depth = 0
    start = 0
    i = 0
    while i < len(text):
        if text[i] == "(":
            if depth == 0 and i > start:
                chunk = text[start:i].strip()
                if chunk:
                    out.append(chunk)
            depth += 1
            if depth == 1:
                start = i + 1
            i += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                inner = text[start:i].strip()
                if inner:
                    for part in re.split(r"\s*,\s*", inner):
                        part = part.strip()
                        if part:
                            out.extend(_split_by_parentheses(part))
                start = i + 1
            i += 1
        else:
            i += 1
    if depth == 0 and start < len(text):
        chunk = text[start:].strip()
        if chunk:
            out.append(chunk)
    return out


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
    raw_str = raw_str.strip()
    if not raw_str:
        return []

    # Check processed food first (whole string normalized)
    key = normalize_ingredient_key(raw_str)
    if key in PROCESSED_FOOD_TO_BASE:
        return list(PROCESSED_FOOD_TO_BASE[key])

    # Split by comma outside parentheses only (commas inside parentheses handled in _split_by_parentheses)
    flat: List[str] = []
    segments = re.split(r",(?![^(]*\))", raw_str)
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        parts = _split_by_parentheses(seg)
        for p in parts:
            p = p.strip()
            if not p:
                continue
            pk = normalize_ingredient_key(p)
            if pk in PROCESSED_FOOD_TO_BASE:
                flat.extend(PROCESSED_FOOD_TO_BASE[pk])
            else:
                if pk:
                    flat.append(pk)

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: List[str] = []
    for item in flat:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
