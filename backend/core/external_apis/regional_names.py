"""
Regional/local ingredient names → English/canonical names for USDA, Open Food Facts, etc.
- Static: data/regional_ingredient_names.json (curated).
- Learned: data/learned_regional_mappings.json (auto-expanded from user searches and API results).
Used so queries like "bajra" try "pearl millet" with USDA/OFF. Callers can also resolve online
via Wikidata (resolve_to_english_label) and persist with set_learned_english().
"""
import json
import logging
from pathlib import Path
from typing import List

from core.config import get_regional_ingredient_names_path, get_learned_regional_mappings_path

logger = logging.getLogger(__name__)

# Built-in fallback so regional names resolve even when data/ file is missing (e.g. Docker path)
_BUILTIN_REGIONAL: dict[str, str] = {
    "bajra": "pearl millet", "bajri": "pearl millet",
    "jowar": "sorghum", "jowari": "sorghum",
    "ragi": "finger millet", "nachni": "finger millet",
    "chana": "chickpea", "channa": "chickpea", "chole": "chickpea",
    "besan": "chickpea flour",
    "rajma": "kidney beans", "moong": "mung bean", "masoor": "red lentil",
    "toor": "pigeon pea", "tuvar": "pigeon pea", "arhar": "pigeon pea",
    "urad": "black gram", "chawal": "rice", "gehu": "wheat", "gehoon": "wheat",
    "atta": "wheat flour", "maida": "all purpose flour",
    "haldi": "turmeric", "jeera": "cumin", "dhania": "coriander", "methi": "fenugreek",
    "poha": "flattened rice", "sabudana": "sago", "paneer": "paneer", "ghee": "ghee",
}

# regional_key (normalized) -> canonical English name (built-in + static + learned)
_regional_to_canonical: dict[str, str] = {}
_loaded_static = False
_loaded_learned = False
_learned: dict[str, str] = {}


def _normalize(s: str) -> str:
    return s.lower().strip().replace(" ", "_")


def _load_static() -> None:
    global _regional_to_canonical, _loaded_static
    if _loaded_static:
        return
    _loaded_static = True
    # Built-in first so regional names work even when data/ file is missing (e.g. Docker)
    for k, v in _BUILTIN_REGIONAL.items():
        _regional_to_canonical[k] = v
    path = get_regional_ingredient_names_path()
    if not path.exists():
        logger.debug("Regional ingredient names file not found: %s (using built-in)", path)
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        mappings = data.get("mappings") or []
        for entry in mappings:
            canonical = (entry.get("canonical") or "").strip()
            if not canonical:
                continue
            for name in entry.get("regional") or []:
                key = _normalize((name or "").strip())
                if key:
                    _regional_to_canonical[key] = canonical
        logger.info("Loaded %d static regional ingredient name mappings", len(_regional_to_canonical))
    except Exception as e:
        logger.warning("Failed to load regional ingredient names from %s: %s", path, e)


def _load_learned() -> None:
    global _learned, _loaded_learned
    if _loaded_learned:
        return
    _loaded_learned = True
    path = get_learned_regional_mappings_path()
    if not path.exists():
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for k, v in (data.get("mappings") or {}).items():
            if k and v:
                _learned[_normalize(k)] = str(v).strip()
        if _learned:
            logger.info("Loaded %d learned regional ingredient mappings", len(_learned))
    except Exception as e:
        logger.warning("Failed to load learned regional mappings from %s: %s", path, e)


def _load_mappings() -> None:
    _load_static()
    _load_learned()
    for k, v in _learned.items():
        if k and k not in _regional_to_canonical:
            _regional_to_canonical[k] = v


def get_learned_english(query: str) -> str | None:
    """Return learned English/canonical name for this query if any. Normalizes query for lookup."""
    _load_learned()
    if not query or not query.strip():
        return None
    return _learned.get(_normalize(query))


def set_learned_english(query: str, english_name: str) -> None:
    """
    Persist a regional → English mapping so future lookups use it without calling Wikidata.
    Updates in-memory cache and appends to data/learned_regional_mappings.json.
    """
    if not query or not english_name or not (query.strip() and english_name.strip()):
        return
    norm = _normalize(query)
    en = english_name.strip()
    if _normalize(en) == norm:
        return
    global _regional_to_canonical, _learned
    _learned[norm] = en
    _regional_to_canonical[norm] = en
    path = get_learned_regional_mappings_path()
    try:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"description": "Auto-learned regional → English from user searches and API results", "mappings": {}}
        data.setdefault("mappings", {})[norm] = en
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug("Learned regional mapping: %s -> %s", norm[:50], en[:50])
    except Exception as e:
        logger.warning("Failed to persist learned regional mapping to %s: %s", path, e)


def get_canonical_queries(query: str) -> List[str]:
    """
    Return list of search strings to try for USDA/OFF: canonical English first if mapped (static or learned), then original.
    Normalizes query (lower, spaces → underscores) for lookup; returns display-style strings for API calls.
    """
    _load_mappings()
    if not query or not query.strip():
        return [query] if query else []
    normalized = _normalize(query)
    canonical = _regional_to_canonical.get(normalized) if normalized else None
    display_query = query.strip().replace("_", " ")
    if canonical and _normalize(canonical) != normalized:
        if normalized in _BUILTIN_REGIONAL:
            logger.info("REGIONAL_QUERY using built-in mapping: %s -> %s", normalized, canonical)
        return [canonical, display_query]
    return [display_query]
