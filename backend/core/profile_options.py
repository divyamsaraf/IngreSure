"""
Load profile options from data/profile_options.json (single source of truth for backend and frontend).
Canonical display string for Hindu veg diet is "Hindu Vegetarian".
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from core.config import get_profile_options_path

logger = logging.getLogger(__name__)

# Fallbacks if file missing (must match profile_options.json shape)
_DEFAULT_DIETARY_VALUES = [
    "No rules", "Vegan", "Vegetarian", "Pescatarian", "Jain", "Halal", "Kosher",
    "Hindu Vegetarian", "Hindu Non Vegetarian",
]
_DEFAULT_ALLERGENS = [
    "Milk", "Eggs", "Peanuts", "Tree Nuts", "Soy", "Wheat/Gluten",
    "Fish", "Shellfish", "Sesame", "Mustard", "Celery", "Other",
]
_DEFAULT_LIFESTYLE_VALUES = [
    "no alcohol", "no insect derived", "no palm oil", "no onion", "no garlic",
    "Gluten-Free", "Dairy-Free", "Egg-Free",
]

_cached: Dict[str, Any] | None = None


def _load() -> Dict[str, Any]:
    global _cached
    if _cached is not None:
        return _cached
    path = get_profile_options_path()
    if not path.exists():
        logger.warning("profile_options.json not found at %s; using defaults", path)
        _cached = {
            "dietary_preference_options": [{"value": v, "label": v} for v in _DEFAULT_DIETARY_VALUES],
            "allergen_options": _DEFAULT_ALLERGENS,
            "lifestyle_options": [{"value": v, "label": v} for v in _DEFAULT_LIFESTYLE_VALUES],
            "diet_icon": {},
        }
        return _cached
    try:
        with open(path, encoding="utf-8") as f:
            _cached = json.load(f)
        return _cached
    except Exception as e:
        logger.warning("Failed to load profile_options.json: %s; using defaults", e)
        _cached = {
            "dietary_preference_options": [{"value": v, "label": v} for v in _DEFAULT_DIETARY_VALUES],
            "allergen_options": _DEFAULT_ALLERGENS,
            "lifestyle_options": [{"value": v, "label": v} for v in _DEFAULT_LIFESTYLE_VALUES],
            "diet_icon": {},
        }
        return _cached


def get_dietary_preference_choices() -> List[str]:
    """Canonical list of dietary preference values (e.g. for validation)."""
    data = _load()
    opts = data.get("dietary_preference_options") or []
    return [o.get("value") or o.get("label") for o in opts if isinstance(o, dict)]


def get_allergen_choices() -> List[str]:
    """Canonical list of allergen display names."""
    data = _load()
    opts = data.get("allergen_options") or []
    return list(opts) if isinstance(opts, list) else _DEFAULT_ALLERGENS


def get_lifestyle_choices() -> List[str]:
    """Canonical list of lifestyle option values (stored in profile)."""
    data = _load()
    opts = data.get("lifestyle_options") or []
    if not isinstance(opts, list):
        return _DEFAULT_LIFESTYLE_VALUES
    return [o.get("value") or o.get("label") for o in opts if isinstance(o, dict)]


def get_profile_options_raw() -> Dict[str, Any]:
    """Full options dict (e.g. for API)."""
    return dict(_load())
