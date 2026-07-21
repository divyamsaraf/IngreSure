"""L2 structured variant aliases (design §9.3.1).

Curated alias → canonical map loaded from
``data/commodity_seed_lists/variant_aliases.json``. Longest-phrase keys win.
No fuzzy / edit-distance matching.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from core.normalization.normalizer import normalize_ingredient_key

_REPO = Path(__file__).resolve().parents[4]
_ALIAS_PATH = _REPO / "data" / "commodity_seed_lists" / "variant_aliases.json"


@lru_cache(maxsize=1)
def _alias_table() -> dict[str, str]:
    if not _ALIAS_PATH.exists():
        return {}
    data = json.loads(_ALIAS_PATH.read_text(encoding="utf-8"))
    raw = data.get("aliases") or {}
    out: dict[str, str] = {}
    for src, dst in raw.items():
        if str(src).startswith("_"):
            continue
        sn = normalize_ingredient_key(str(src))
        dn = normalize_ingredient_key(str(dst))
        if sn and dn and sn != dn:
            out[sn] = dn
    return out


@lru_cache(maxsize=1)
def _aliases_by_length() -> list[tuple[str, str]]:
    """Longest source phrase first for prefix-safe exact lookup."""
    return sorted(_alias_table().items(), key=lambda kv: (-len(kv[0]), kv[0]))


def lookup_variant_alias(normalized_key: str) -> Optional[str]:
    """Return canonical key for an exact (normalized) variant alias, or None."""
    key = normalize_ingredient_key(normalized_key or "")
    if not key:
        return None
    table = _alias_table()
    hit = table.get(key)
    if hit:
        return hit
    # Longest-phrase: allow exact match only (already covered); keep API for
    # callers that iterate by length for future multi-token scans.
    for src, dst in _aliases_by_length():
        if key == src:
            return dst
    return None


def all_variant_aliases() -> dict[str, str]:
    return dict(_alias_table())


def reset_variant_alias_cache() -> None:
    """Test-only: reload JSON on next lookup."""
    _alias_table.cache_clear()
    _aliases_by_length.cache_clear()
