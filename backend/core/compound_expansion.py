"""
Compound ingredient expansion for compliance evaluation.

Handles both explicit ('burger with chicken') and implicit ('garlic pasta',
'egg noodles') compound product names, extracting known restricted-ingredient
keywords for the compliance engine.
"""
import re
from typing import Dict, List, Set, Tuple

# Known restricted ingredient keywords — when found inside a multi-word
# product name, these are extracted for compliance evaluation.
_RESTRICTED_KEYWORDS_BIGRAM: Set[str] = {
    "sweet potato", "fish oil", "palm oil",
}

_RESTRICTED_KEYWORDS_SINGLE: Set[str] = {
    # Animal-derived
    "egg", "eggs", "chicken", "beef", "pork", "lamb", "fish",
    "tuna", "salmon", "shrimp", "prawn", "crab", "lobster",
    "bacon", "ham", "turkey", "duck", "veal", "mutton",
    "anchovy", "sardine", "squid", "octopus", "venison", "goat",
    # Dairy
    "milk", "cheese", "butter", "cream", "yogurt", "ghee",
    "paneer", "whey", "curd",
    # Root vegetables (Jain)
    "garlic", "onion", "potato", "carrot", "ginger",
    "beet", "beetroot", "radish", "turnip", "shallot", "leek", "yam",
    # Fungal (Jain)
    "mushroom", "truffle",
    # Other
    "gelatin", "honey", "lard", "alcohol", "wine", "beer",
    "peanut", "almond", "walnut", "cashew", "hazelnut", "pecan",
    "soy", "tofu", "wheat", "barley", "rye", "oat", "oats",
    "collagen", "rennet", "shellac", "carmine",
}

# Plant modifiers that neutralize the following dairy/meat word
# e.g. "coconut milk" is plant-based, NOT dairy
_PLANT_MODIFIERS: Set[str] = {
    "coconut", "almond", "soy", "oat", "oats", "rice", "cashew",
    "hemp", "pea", "cocoa", "shea", "sesame", "flax", "hazelnut",
    "peanut", "walnut", "pistachio", "macadamia", "pecan",
}


def find_sub_ingredients(name: str) -> List[str]:
    """Extract known restricted-ingredient keywords from a compound name.

    'garlic pasta'   -> ['garlic']
    'egg noodles'    -> ['egg']
    'coconut milk'   -> []   (plant modifier neutralizes 'milk')
    'butter chicken' -> ['butter', 'chicken']
    """
    words = name.lower().split()
    if len(words) <= 1:
        return []
    found: List[str] = []
    i = 0
    while i < len(words):
        if i + 1 < len(words):
            bigram = f"{words[i]} {words[i + 1]}"
            if bigram in _RESTRICTED_KEYWORDS_BIGRAM:
                found.append(bigram)
                i += 2
                continue
        if words[i] in _RESTRICTED_KEYWORDS_SINGLE:
            if i > 0 and words[i - 1] in _PLANT_MODIFIERS:
                i += 1
                continue
            found.append(words[i])
        i += 1
    return found


def expand_compounds(ingredients: List[str]) -> Tuple[List[str], Dict[str, str]]:
    """Expand compound items for compliance evaluation.

    Handles both explicit ('burger with chicken') and implicit
    ('garlic pasta', 'egg noodles') compound product names.

    Returns:
        expanded: ingredient names for the compliance engine
        display_map: {eval_name_lower: original_compound_display_name}
    """
    expanded: List[str] = []
    display_map: Dict[str, str] = {}
    seen: Set[str] = set()

    for ing in ingredients:
        # 1. Explicit "X with Y" pattern
        m = re.match(r"^(.+?)\s+with\s+(.+)$", ing, re.IGNORECASE)
        if m:
            sub = m.group(2).strip()
            key = sub.lower()
            if key not in seen:
                seen.add(key)
                expanded.append(sub)
                display_map[key] = ing
            continue

        # 2. Single-word ingredient -> pass through directly
        if " " not in ing.strip():
            key = ing.lower().strip()
            if key not in seen:
                seen.add(key)
                expanded.append(ing)
            continue

        # 3. Multi-word: extract known ingredient keywords
        subs = find_sub_ingredients(ing)
        if subs:
            covered: Set[str] = set()
            for s in subs:
                covered.update(s.split())
            all_words = set(ing.lower().split())
            is_compound_product = bool(all_words - covered)

            for sub in subs:
                key = sub.lower()
                if key not in seen:
                    seen.add(key)
                    expanded.append(sub)
                    if is_compound_product:
                        display_map[key] = ing
        else:
            key = ing.lower().strip()
            if key not in seen:
                seen.add(key)
                expanded.append(ing)

    return expanded, display_map
