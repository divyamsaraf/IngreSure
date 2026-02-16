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

USE_NEW_ENGINE = os.environ.get("USE_NEW_ENGINE", "").lower() in ("1", "true", "yes")
SHADOW_MODE = os.environ.get("SHADOW_MODE", "").lower() in ("1", "true", "yes")

# Data paths (relative to repo root)
def get_ontology_path() -> Path:
    return _REPO_ROOT / "data" / "ontology.json"

def get_restrictions_path() -> Path:
    return _REPO_ROOT / "data" / "restrictions.json"

def log_config() -> None:
    """Call at startup for consistent debugging."""
    logger.info(
        "INGRESURE_ENGINE: use_new_engine=%s shadow_mode=%s ontology_exists=%s restrictions_exists=%s",
        USE_NEW_ENGINE,
        SHADOW_MODE,
        get_ontology_path().exists(),
        get_restrictions_path().exists(),
    )
