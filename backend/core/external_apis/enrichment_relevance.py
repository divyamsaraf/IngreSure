"""Relevance guards for external enrichment (species mismatch, junk queries).

Pattern class L (extends universal label pipeline A–K):
  L1 — exclusive meat species mismatch (chicken ≠ lamb, beef ≠ pork, …)
  L2 — plant-named query vs animal/dairy API hit (coconut milk ≠ cow milk)
  L3 — shared process terms (mechanically separated) must not override species
  L4 — no species in query → species guard inactive (flavorings, chemicals)
  L5 — scoring ranks candidates; negative score = reject
"""
from __future__ import annotations

import re

# Exclusive meat species groups — if query and result each hit a group, they must overlap.
_SPECIES_TERMS: dict[str, tuple[str, ...]] = {
    "poultry": ("chicken", "poultry", "hen", "broiler"),
    "turkey": ("turkey",),
    "duck": ("duck", "duckling"),
    "beef": ("beef", "veal", "bovine", "cattle"),
    "pork": ("pork", "bacon", "ham", "swine", "pig", "porcine"),
    "lamb": ("lamb", "mutton", "sheep", "goat"),
    "fish": ("fish", "salmon", "tuna", "cod", "sardine", "anchovy", "haddock"),
    "shellfish": ("shrimp", "crab", "lobster", "shellfish", "prawn", "clam", "mussel", "oyster", "scallop"),
}

# Plant-based names that contain misleading animal keywords (class L2).
_PLANT_OVERRIDE_PATTERNS = (
    "peanut butter", "almond butter", "cashew butter", "sunflower butter",
    "cocoa butter", "shea butter", "apple butter",
    "almond milk", "oat milk", "soy milk", "rice milk", "coconut milk",
    "cashew milk", "hemp milk", "flax milk",
    "coconut cream", "coconut yogurt", "coconut cheese",
    "vegan cheese", "vegan butter", "vegan cream", "vegan egg",
    "tofu", "tempeh", "seitan", "jackfruit", "nutritional yeast",
    "plant-based", "plant based", "meatless", "dairy-free", "dairy free",
    "eggplant", "egg plant", "egusi",
    "butternut", "buttercup squash", "butterbean", "butter bean",
    "butterscotch", "cream of tartar", "creamed corn", "cream soda",
)

_ANIMAL_DAIRY_KEYWORDS = (
    "milk", "whey", "casein", "cheese", "cream", "butter", "dairy",
    "lactose", "ghee", "yogurt", "meat", "beef", "pork", "chicken",
    "lamb", "veal", "bacon", "ham", "gelatin", "lard",
)


def _word_in(text: str, word: str) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}(?:e?s)?\b", text, re.IGNORECASE))


def _is_plant_override(text: str) -> bool:
    t = (text or "").lower()
    return any(p in t for p in _PLANT_OVERRIDE_PATTERNS)


def species_groups_in_text(text: str) -> frozenset[str]:
    """Return meat-species groups mentioned in label/API text."""
    if not text:
        return frozenset()
    groups: set[str] = set()
    for group, terms in _SPECIES_TERMS.items():
        if any(_word_in(text, term) for term in terms):
            groups.add(group)
    return frozenset(groups)


def enrichment_species_mismatch(query: str, candidate: str) -> bool:
    """True when query and candidate name different exclusive meat species."""
    q_groups = species_groups_in_text(query)
    c_groups = species_groups_in_text(candidate)
    if not q_groups or not c_groups:
        return False
    return q_groups.isdisjoint(c_groups)


def enrichment_plant_animal_mismatch(query: str, candidate: str) -> bool:
    """True when a plant-named query (coconut milk) maps to animal/dairy canonical."""
    if not _is_plant_override(query):
        return False
    if _is_plant_override(candidate):
        return False
    if species_groups_in_text(candidate):
        return True
    c = (candidate or "").lower()
    return any(_word_in(c, kw) for kw in _ANIMAL_DAIRY_KEYWORDS)


def is_enrichment_relevant(query: str, candidate: str) -> bool:
    """Central gate: reject enrichment results that mismatch query semantics."""
    if enrichment_species_mismatch(query, candidate):
        return False
    if enrichment_plant_animal_mismatch(query, candidate):
        return False
    return True


def score_enrichment_candidate(query: str, description: str) -> int:
    """Higher is better. Negative when relevance guards fail."""
    if not is_enrichment_relevant(query, description):
        return -100
    q = (query or "").lower()
    d = (description or "").lower()
    if not q or not d:
        return 0
    score = 0
    if q in d or d in q:
        score += 50
    q_tokens = [t for t in re.split(r"[^a-z0-9]+", q) if len(t) > 2]
    for token in q_tokens:
        if _word_in(d, token):
            score += 10
    return score


# Back-compat alias used by USDA connector
score_usda_candidate = score_enrichment_candidate
