"""
Compound ingredient expansion for compliance evaluation.

Typed neutralize (plant_mod / dairy_head / culinary_keep / process_keep) lives in
``coverage_os.neutralize.apply_policies``. This module:
  - splits explicit "X with Y"
  - trusts PolicyResult when a policy fires
  - on passthrough, extracts via ``_RESTRICTED_KEYWORDS_*`` / find_sub_ingredients
"""
from __future__ import annotations

import re
from typing import Dict, List, Mapping, Optional, Set, Tuple

from core.knowledge.ike2.coverage_os.neutralize import apply_policies, build_role_index

# Known restricted ingredient keywords — when found inside a multi-word
# product name on neutralize passthrough, these are extracted for compliance.
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

_ROLE_INDEX_CACHE: Optional[dict[str, str]] = None


def clear_role_index_cache() -> None:
    global _ROLE_INDEX_CACHE
    _ROLE_INDEX_CACHE = None


def get_role_index() -> dict[str, str]:
    """Public role index for expansion + facet consumers."""
    return _load_role_index()


def _load_role_index() -> dict[str, str]:
    global _ROLE_INDEX_CACHE
    if _ROLE_INDEX_CACHE is not None:
        return _ROLE_INDEX_CACHE
    try:
        from core.knowledge.ike2.etl.load_ontology import load_ontology_records
        _ROLE_INDEX_CACHE = build_role_index(list(load_ontology_records()))
    except Exception:
        _ROLE_INDEX_CACHE = {}
    return _ROLE_INDEX_CACHE


def find_sub_ingredients(name: str) -> List[str]:
    """Extract known restricted-ingredient keywords (passthrough path only).

    Plant-mod / culinary-keep / process-keep are owned by apply_policies;
    this helper must not reimplement those neutralize lists.
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
            found.append(words[i])
        i += 1
    return found


def expand_compounds(
    ingredients: List[str],
    *,
    role_index: Mapping[str, str] | None = None,
) -> Tuple[List[str], Dict[str, str], Dict[str, str]]:
    """Expand compound items for compliance evaluation.

    Returns:
        expanded: ingredient names for the compliance engine
        display_map: {eval_name_lower: original_compound_display_name}
        derived_from_map: {derived_atom_lower: parent_phrase_lower}
    """
    expanded: List[str] = []
    display_map: Dict[str, str] = {}
    derived_from_map: Dict[str, str] = {}
    seen: Set[str] = set()
    roles = dict(role_index) if role_index is not None else _load_role_index()

    def _emit(atom: str, display: str) -> None:
        key = atom.lower().strip()
        if not key or key in seen:
            return
        seen.add(key)
        expanded.append(atom)
        if display and display.lower().strip() != key:
            display_map[key] = display

    for ing in ingredients:
        # 1. Explicit "X with Y" pattern
        m = re.match(r"^(.+?)\s+with\s+(.+)$", ing, re.IGNORECASE)
        if m:
            sub = m.group(2).strip()
            _emit(sub, ing)
            continue

        # 2. Single-word ingredient -> pass through directly
        if " " not in ing.strip():
            _emit(ing, "")
            continue

        # 3. Typed neutralize (shared policy engine)
        result = apply_policies(ing, role_index=roles)
        if result.policy_fired:
            for atom in result.atoms:
                _emit(atom, ing)
            for child, parent in result.derived_from.items():
                derived_from_map[child.lower()] = parent.lower()
            continue

        # 4. Passthrough: existing restricted-keyword extract (not neutralize)
        subs = find_sub_ingredients(ing)
        if subs:
            for sub in subs:
                _emit(sub, ing)
        else:
            _emit(ing, "")

    return expanded, display_map, derived_from_map
