"""
Deterministic normalization only. No LLM, no substring guessing.
Used to produce a key for ontology lookup; unknown keys are not resolved here.
Unicode NFKC normalization for regional scripts (e.g. Devanagari, Tamil) and compatibility.
"""
import re
import logging
import unicodedata
from typing import List, Optional

logger = logging.getLogger(__name__)

# High-confidence OCR token fixes (digit/letter confusions on common staples).
OCR_TYPOS: dict[str, str] = {
    "mi1k": "milk",
    "m1lk": "milk",
    "fl0ur": "flour",
    "f1our": "flour",
    "s0y": "soy",
    "su g4r": "sugar",
    "sug4r": "sugar",
    "whe4t": "wheat",
    "wh3at": "wheat",
    "ye4st": "yeast",
    "ye ast": "yeast",
    "sa lt": "salt",
    "wa ter": "water",
    "eg g": "egg",
    "0il": "oil",
    "ol1ve": "olive",
}

# Known spelling variants for ontology lookup (normalized key -> canonical key)
KNOWN_VARIANTS: dict[str, str] = {
    # Isinglass variants
    "inglass": "isinglass",
    "isinglass": "isinglass",
    "fish gelatin": "fish_gelatin",
    "fish gelatine": "fish_gelatin",
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
    "hazelnuts": "hazelnut",
    "pecans": "pecan",
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
# OCR typos merge into KNOWN_VARIANTS at lookup time (not duplicated in dict literal).

_E_NUMBER_RE = re.compile(r"^e(\d{3,4})([a-z]?)$", re.IGNORECASE)
# EU food additive codes are E100–E1599 (optional letter suffix a–f).
_E_NUMBER_MIN = 100
_E_NUMBER_MAX = 1599


def parse_e_number(text: str) -> Optional[tuple[int, str]]:
    """Parse E-number into (numeric code, suffix letter). None if not E-number shaped."""
    if not text or not isinstance(text, str):
        return None
    compact = re.sub(r"\s+", "", text.strip())
    m = _E_NUMBER_RE.match(compact)
    if not m:
        return None
    return int(m.group(1)), (m.group(2) or "").lower()


def is_e_number_code(text: str) -> bool:
    """True when text is an E-number additive code (e.g. E120, e441)."""
    return parse_e_number(text) is not None


def is_plausible_e_number_code(text: str) -> bool:
    """True for EU-range E-numbers (E100–E1599). Rejects invalid codes like E1222."""
    parsed = parse_e_number(text)
    if not parsed:
        return False
    num, _suffix = parsed
    return _E_NUMBER_MIN <= num <= _E_NUMBER_MAX


def substance_key(text: str) -> str:
    """
    Canonical substance identity for compliance, audit grouping, and dedup.
    E-numbers, aliases, and spelling variants map to one key (e.g. e120 -> carmine).
    """
    return normalize_ingredient_key(text)


def _apply_known_variants(t: str) -> str:
    if t in OCR_TYPOS:
        canonical = OCR_TYPOS[t]
        if canonical != t:
            logger.debug("NORMALIZE ocr typo applied raw=%s -> canonical=%s", t, canonical)
        return canonical
    if t in KNOWN_VARIANTS:
        canonical = KNOWN_VARIANTS[t]
        if canonical != t:
            logger.debug("NORMALIZE variant applied raw=%s -> canonical=%s", t, canonical)
        return canonical
    return t


def _apply_regional_canonical(t: str) -> str:
    from core.external_apis.regional_names import resolve_static_regional_canonical

    canonical = resolve_static_regional_canonical(t)
    if canonical:
        logger.debug("NORMALIZE regional applied raw=%s -> canonical=%s", t, canonical)
        return canonical.lower().strip()
    return t


def normalize_ingredient_key(text: str) -> str:
    """
    Normalize a raw ingredient string for lookup.
    - Unicode NFKC normalization (regional scripts, compatibility).
    - Lowercase, strip, remove excess punctuation and whitespace.
    - Apply known variants (e.g. inglass -> isinglass).
    - No substring or fuzzy matching.
    """
    if not text or not isinstance(text, str):
        return ""
    t = unicodedata.normalize("NFKC", text).lower().strip()
    t = t.replace("*", "").replace(".", "")
    t = re.sub(r"[,;:\-\u2013\u2014]+", " ", t)
    t = re.sub(r"\s+", " ", t)
    t = t.strip()
    t = _apply_known_variants(t)
    regional = _apply_regional_canonical(t)
    return regional if regional != t else t


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
