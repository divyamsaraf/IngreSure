"""
Feature flags, paths, and centralized configuration.
All resolution relative to the backend directory.
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Repo root: backend/core/config.py -> parent=core, parent.parent=backend, parent.parent.parent=repo
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent

# --- Feature flags ---
USE_NEW_ENGINE = os.environ.get("USE_NEW_ENGINE", "true").lower() in ("1", "true", "yes")
SHADOW_MODE = os.environ.get("SHADOW_MODE", "").lower() in ("1", "true", "yes")

# --- Data paths ---
def get_ontology_path() -> Path:
    return _REPO_ROOT / "data" / "ontology.json"

def get_restrictions_path() -> Path:
    return _REPO_ROOT / "data" / "restrictions.json"

def get_dynamic_ontology_path() -> Path:
    return _REPO_ROOT / "data" / "dynamic_ontology.json"

def get_unknown_ingredients_log_path() -> Path:
    return _REPO_ROOT / "data" / "unknown_ingredients_log.json"

# --- External APIs (lazy read from env) ---
def get_usda_fdc_api_key() -> str:
    return os.environ.get("USDA_FDC_API_KEY", "").strip()

def get_open_food_facts_enabled() -> bool:
    return os.environ.get("OPEN_FOOD_FACTS_ENABLED", "true").lower() in ("1", "true", "yes")

# --- LLM / Ollama ---
def get_ollama_url() -> str:
    return os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/generate")

def get_ollama_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "llama3.2:3b")

# LLM timeout defaults (seconds)
LLM_INTENT_TIMEOUT = int(os.environ.get("LLM_INTENT_TIMEOUT", "30"))
LLM_RESPONSE_TIMEOUT = int(os.environ.get("LLM_RESPONSE_TIMEOUT", "30"))

# --- Startup logging ---
def log_config() -> None:
    key = get_usda_fdc_api_key()
    off = get_open_food_facts_enabled()
    logger.info(
        "CONFIG: use_new_engine=%s shadow_mode=%s ontology=%s restrictions=%s dynamic=%s "
        "usda_key=%s off_enabled=%s ollama_model=%s llm_intent_timeout=%ds llm_response_timeout=%ds",
        USE_NEW_ENGINE, SHADOW_MODE,
        get_ontology_path().exists(), get_restrictions_path().exists(),
        get_dynamic_ontology_path().exists(),
        bool(key), off, get_ollama_model(),
        LLM_INTENT_TIMEOUT, LLM_RESPONSE_TIMEOUT,
    )
