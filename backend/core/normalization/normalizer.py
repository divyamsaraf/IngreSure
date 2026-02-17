"""
Deterministic normalization only. No LLM, no substring guessing.
Used to produce a key for ontology lookup; unknown keys are not resolved here.
"""
import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# Known spelling variants for ontology lookup (normalized key -> canonical key)
KNOWN_VARIANTS: dict[str, str] = {
    # Isinglass variants
    "inglass": "isinglass",
    "isinglass": "isinglass",
    "fish gelatin": "isinglass",
    "fish bladder": "isinglass",
    # Shellac variants
    "confectioners glaze": "shellac",
    "confectioner's glaze": "shellac",
    "resinous glaze": "shellac",
    "pharmaceutical glaze": "shellac",
    "e904": "shellac",
    # L-cysteine variants
    "l cysteine": "l-cysteine",
    "cysteine": "l-cysteine",
    "e920": "l-cysteine",
    # Lanolin variants
    "wool grease": "lanolin",
    "wool wax": "lanolin",
    "wool fat": "lanolin",
    # Anchovy variants
    "anchovie": "anchovy",
    "anchovies": "anchovy",
    "anchovy paste": "anchovy",
    "anchovy extract": "anchovy",
    # Common plurals → canonical singular (ontology uses singular)
    "eggs": "egg",
    "onions": "onion",
    "potatoes": "potato",
    "tomatoes": "tomato",
    "carrots": "carrot",
    "mushrooms": "mushroom",
    "almonds": "almond",
    "walnuts": "walnut",
    "cashews": "cashew",
    "peanuts": "peanut",
    "prawns": "prawn",
    "shrimps": "shrimp",
    "oats": "oat",
    "raisins": "raisin",
    "olives": "olive",
    "lemons": "lemon",
    "limes": "lime",
    "oranges": "orange",
    "bananas": "banana",
    "apples": "apple",
    "grapes": "grape",
    "berries": "berry",
    "cherries": "cherry",
    "strawberries": "strawberry",
    "blueberries": "blueberry",
    "raspberries": "raspberry",
    "cranberries": "cranberry",
    "sardines": "sardine",
    "mackerels": "mackerel",
    "clams": "clam",
    "mussels": "mussel",
    "oysters": "oyster",
    "scallops": "scallop",
    "lobsters": "lobster",
    "crabs": "crab",
    # Gelatin / gelatine normalization
    "gelatine": "gelatin",
    # Common E-number food additives
    "e120": "carmine",
    "e441": "gelatin",
    "e542": "bone phosphate",
    "e631": "disodium inosinate",
    "e901": "beeswax",
    "e966": "lactitol",
    # Rennet variants
    "animal rennet": "rennet",
}


def normalize_ingredient_key(text: str) -> str:
    """
    Normalize a raw ingredient string for lookup.
    - Lowercase, strip, remove excess punctuation and whitespace.
    - Apply known variants (e.g. inglass -> isinglass).
    - No substring or fuzzy matching.
    """
    if not text or not isinstance(text, str):
        return ""
    t = text.lower().strip()
    t = t.replace("*", "").replace(".", "")
    t = re.sub(r"[,;:\-\u2013\u2014]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    t = t.strip()
    if t in KNOWN_VARIANTS:
        canonical = KNOWN_VARIANTS[t]
        if canonical != t:
            logger.debug("NORMALIZE variant applied raw=%s -> canonical=%s", t, canonical)
        return canonical
    return t


def tokenize_ingredients(raw_text: str) -> List[str]:
    """
    Split raw text into candidate ingredient tokens (e.g. by comma, newline).
    Does not resolve or validate; just deterministic split and trim.
    """
    if not raw_text:
        return []
    # Split on comma, newline, semicolon; trim each
    parts = re.split(r"[\n,;]", raw_text)
    return [normalize_ingredient_key(p) for p in parts if normalize_ingredient_key(p)]
