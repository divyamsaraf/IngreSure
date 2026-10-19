"""Orthographic spelling pairs for verdict-parity scanning (Item 37 Part C)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from core.normalization.normalizer import normalize_ingredient_key

_PAIRS = (
    ("sulf", "sulph"),
    ("aluminium", "aluminum"),
    ("colour", "color"),
    ("fibre", "fiber"),
)

_REVIEWED_PATH = Path(__file__).with_name("orthographic_safe_uncertain_baseline.json")

# Restrictions probed for firm SAFE vs NOT_SAFE disagreement.
ORTHO_RESTRICTIONS: tuple[str, ...] = (
    "sulfite_sensitive",
    "gluten_free",
    "dairy_free",
    "vegan",
    "vegetarian",
    "egg_free",
    "fish_allergy",
    "shellfish_allergy",
    "soy_allergy",
    "sesame_allergy",
    "mustard_allergy",
    "celery_allergy",
    "lupin_allergy",
    "peanut_allergy",
    "tree_nut_allergy",
)


def _flip(s: str, a: str, b: str) -> str | None:
    if a in s:
        return s.replace(a, b)
    if b in s:
        return s.replace(b, a)
    return None


def _alias_universe() -> set[str]:
    aliases: set[str] = set()
    repo = Path(__file__).resolve().parents[4]
    ont_path = repo / "data" / "ontology.json"
    if ont_path.exists():
        for r in json.loads(ont_path.read_text(encoding="utf-8")).get("ingredients") or []:
            aliases.add(normalize_ingredient_key(r.get("canonical_name") or ""))
            for a in r.get("aliases") or []:
                aliases.add(normalize_ingredient_key(a))
    cat_path = repo / "data" / "e_number_catalog.json"
    if cat_path.exists():
        raw = json.loads(cat_path.read_text(encoding="utf-8"))
        entries = raw if isinstance(raw, list) else raw.get("entries") or []
        for e in entries:
            if not isinstance(e, dict):
                continue
            aliases.add(normalize_ingredient_key(e.get("canonical_name") or ""))
            for a in e.get("aliases") or []:
                aliases.add(normalize_ingredient_key(a if isinstance(a, str) else ""))
            for a in e.get("e_number_aliases") or []:
                aliases.add(normalize_ingredient_key(a))
    aliases.discard("")
    return aliases


def generate_orthographic_pairs() -> list[tuple[str, str, str]]:
    """Return (left, right, kind) for every distinct spelling flip in the alias universe."""
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str, str]] = []
    for alias in _alias_universe():
        for a, b in _PAIRS:
            if a not in alias and b not in alias:
                continue
            other = _flip(alias, a, b)
            if not other or other == alias:
                continue
            key = tuple(sorted((alias, other)))
            if key in seen:
                continue
            seen.add(key)
            out.append((key[0], key[1], f"{a}/{b}"))
    return sorted(out)


@lru_cache(maxsize=1)
def reviewed_safe_uncertain() -> frozenset[tuple[str, str, str]]:
    """Grandfathered SAFE↔UNCERTAIN baseline (ratchet). Not a written per-pair review."""
    if not _REVIEWED_PATH.exists():
        return frozenset()
    raw = json.loads(_REVIEWED_PATH.read_text(encoding="utf-8"))
    out: set[tuple[str, str, str]] = set()
    for item in raw.get("pairs") or []:
        if len(item) != 3:
            continue
        a, b, rid = item
        left, right = sorted((str(a), str(b)))
        out.add((left, right, str(rid)))
    return frozenset(out)
