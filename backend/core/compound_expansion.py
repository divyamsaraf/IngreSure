"""
Compound ingredient expansion for compliance evaluation.

Typed neutralize (plant_mod / dairy_head / culinary_keep / process_keep) lives in
``coverage_os.neutralize.apply_policies``. This module:
  - splits explicit "X with Y"
  - trusts PolicyResult when a policy fires
  - on passthrough, extracts via ``_RESTRICTED_KEYWORDS_*`` / find_sub_ingredients
  - retains process-identity tokens (tempeh/miso/…) dropped by keyword extract
    and OR-propagates process flags via ``propagate_process_flags`` (Item 2.1)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

from core.knowledge.ike2.coverage_os.neutralize import apply_policies, build_role_index
from core.knowledge.ike2.flag_derive import (
    derive_identity_flags,
    is_free_from_claim,
    keyword_negated_in_phrase,
)
from core.knowledge.ike2.keep_whole import is_keep_whole, load_keep_whole_names
from core.knowledge.ike2.process_flags import PROCESS_FLAG_SET, propagate_process_flags

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


def named_restricted_atoms(*texts: str) -> List[str]:
    """Known restricted tokens named in product-shaped text (positives stand)."""
    found: List[str] = []
    seen: Set[str] = set()
    for text in texts:
        for atom in find_sub_ingredients(text or ""):
            key = atom.lower().strip()
            if key and key not in seen:
                seen.add(key)
                found.append(atom)
    return found


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


def parent_process_flags(phrase: str) -> dict[str, Any]:
    """Process flags implied by a parent compound phrase (for propagation)."""
    derived = derive_identity_flags(phrase, {})
    return {flag: True for flag in PROCESS_FLAG_SET if derived.get(flag)}


def member_flags_with_parent_process(
    parent_phrase: str,
    member_flags: Mapping[str, Any],
) -> dict[str, Any]:
    """OR parent process flags onto a member's flag dict (Item 2.1 helper wire)."""
    return propagate_process_flags(parent_process_flags(parent_phrase), member_flags)


def _process_identity_tokens() -> Set[str]:
    """Process-identity tokens from the keep-whole registry (Item 2 Prompt 4)."""
    try:
        return set(load_keep_whole_names())
    except Exception:
        return set()


def _process_identity_atoms(phrase: str) -> List[str]:
    """Tokens in ``phrase`` that carry process identity and must survive extract."""
    words = phrase.lower().split()
    identity = _process_identity_tokens()
    out: List[str] = []
    seen: Set[str] = set()
    for w in words:
        if w in seen:
            continue
        if w in identity:
            seen.add(w)
            out.append(w)
            continue
        flags = derive_identity_flags(w, {})
        if any(flags.get(f) for f in PROCESS_FLAG_SET):
            seen.add(w)
            out.append(w)
    return out


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

    def _retain_process_identity(phrase: str) -> None:
        """Keep tempeh/miso/… atoms that keyword extract would drop."""
        for atom in _process_identity_atoms(phrase):
            _emit(atom, phrase)
            derived_from_map[atom.lower()] = phrase.lower()

    for ing in ingredients:
        # 0. Keep-whole registry: never recipe-tear a registered process food.
        if is_keep_whole(ing):
            _emit(ing, "")
            continue

        # 1. Explicit "X with Y" pattern
        m = re.match(r"^(.+?)\s+with\s+(.+)$", ing, re.IGNORECASE)
        if m:
            sub = m.group(2).strip()
            _emit(sub, ing)
            _retain_process_identity(ing)
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
            # If neutralize tore to members, still keep process-identity tokens.
            if result.derived_from:
                _retain_process_identity(ing)
            continue

        # 4. Passthrough: restricted-keyword extract + process-identity retain
        # derived_from for keyword hits stays empty (Phase 2a baseline); only
        # retained process-identity atoms record parent linkage.
        # Free-from / contains-no claims must stay whole — extracting "egg" from
        # "egg free pasta" turns a marketed-safe claim into a false Avoid.
        if is_free_from_claim(ing):
            _emit(ing, "")
            continue
        subs = [
            s for s in find_sub_ingredients(ing) if not keyword_negated_in_phrase(ing, s)
        ]
        if subs:
            for sub in subs:
                _emit(sub, ing)
            _retain_process_identity(ing)
        else:
            _emit(ing, "")

    return expanded, display_map, derived_from_map
