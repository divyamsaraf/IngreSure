"""
Feature flags and config. All resolution relative to backend.
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Repo root: backend/core/config.py -> parent=core, parent.parent=backend, parent.parent.parent=repo
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent

USE_NEW_ENGINE = os.environ.get("USE_NEW_ENGINE", "true").lower() in ("1", "true", "yes")
SHADOW_MODE = os.environ.get("SHADOW_MODE", "").lower() in ("1", "true", "yes")

# Data paths (relative to repo root)
def get_ontology_path() -> Path:
    return _REPO_ROOT / "data" / "ontology.json"

def get_restrictions_path() -> Path:
    return _REPO_ROOT / "data" / "restrictions.json"

def get_dynamic_ontology_path() -> Path:
    return _REPO_ROOT / "data" / "dynamic_ontology.json"

def get_unknown_ingredients_log_path() -> Path:
    return _REPO_ROOT / "data" / "unknown_ingredients_log.json"

# External APIs: read lazily so .env changes are picked up on server reload.
# Kept as module-level for backward compat but also available as functions.
def get_usda_fdc_api_key() -> str:
    """Read USDA FDC API key from env at call time (not import time)."""
    return os.environ.get("USDA_FDC_API_KEY", "").strip()

def get_open_food_facts_enabled() -> bool:
    """Read OFF enabled flag from env at call time."""
    return os.environ.get("OPEN_FOOD_FACTS_ENABLED", "true").lower() in ("1", "true", "yes")

# Legacy module-level access (for imports that already reference these)
USDA_FDC_API_KEY = get_usda_fdc_api_key()
OPEN_FOOD_FACTS_ENABLED = get_open_food_facts_enabled()

def log_config() -> None:
    """Call at startup for consistent debugging."""
    key = get_usda_fdc_api_key()
    off = get_open_food_facts_enabled()
    logger.info(
        "INGRESURE_ENGINE: use_new_engine=%s shadow_mode=%s ontology_exists=%s restrictions_exists=%s dynamic_ontology_exists=%s "
        "usda_fdc_key_set=%s open_food_facts_enabled=%s",
        USE_NEW_ENGINE,
        SHADOW_MODE,
        get_ontology_path().exists(),
        get_restrictions_path().exists(),
        get_dynamic_ontology_path().exists(),
        bool(key),
        off,
    )
