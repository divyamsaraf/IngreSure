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

# --- Environment ---
# When True, 500 responses hide exception detail (generic "Internal server error"); full error is always logged.
PRODUCTION = os.environ.get("ENVIRONMENT", "").lower() == "production"

# --- Feature flags ---
# Knowledge DB (Phase 3+): keep off by default until fully wired
USE_KNOWLEDGE_DB = os.environ.get("USE_KNOWLEDGE_DB", "").lower() in ("1", "true", "yes")

# Redis cache (Phase 3+): optional distributed cache layer
REDIS_URL = os.environ.get("REDIS_URL", "").strip()

# --- Data paths ---
def get_ontology_path() -> Path:
    return _REPO_ROOT / "data" / "ontology.json"

def get_restrictions_path() -> Path:
    return _REPO_ROOT / "data" / "restrictions.json"

def get_dynamic_ontology_path() -> Path:
    return _REPO_ROOT / "data" / "dynamic_ontology.json"

def get_regional_ingredient_names_path() -> Path:
    return _REPO_ROOT / "data" / "regional_ingredient_names.json"

def get_learned_regional_mappings_path() -> Path:
    return _REPO_ROOT / "data" / "learned_regional_mappings.json"

def get_unknown_ingredients_log_path() -> Path:
    return _REPO_ROOT / "data" / "unknown_ingredients_log.json"

def get_profile_options_path() -> Path:
    """Single source of truth for diet/allergen/lifestyle options (served to frontend via GET /config)."""
    return _REPO_ROOT / "data" / "profile_options.json"

# --- API constants (single source; frontend fetches via GET /config) ---
MAX_CHAT_MESSAGE_LENGTH = int(os.environ.get("MAX_CHAT_MESSAGE_LENGTH", "8192"))

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

# --- Supabase (Docker-friendly URL) ---
def get_supabase_url() -> str:
    """
    Supabase URL from env. When RUNNING_IN_DOCKER=1, rewrites localhost/127.0.0.1
    to host.docker.internal so the container can reach Supabase on the host.
    """
    import re
    url = (os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or "").strip()
    if not url:
        return ""
    if os.environ.get("RUNNING_IN_DOCKER", "").lower() in ("1", "true", "yes"):
        if "127.0.0.1" in url or "localhost" in url.lower():
            url = re.sub(r"127\.0\.0\.1", "host.docker.internal", url, flags=re.IGNORECASE)
            url = re.sub(r"\blocalhost\b", "host.docker.internal", url, flags=re.IGNORECASE)
    return url

# --- Startup logging ---
def log_config() -> None:
    key = get_usda_fdc_api_key()
    off = get_open_food_facts_enabled()
    logger.info(
        "CONFIG: production=%s use_knowledge_db=%s ontology=%s restrictions=%s dynamic=%s "
        "usda_key=%s off_enabled=%s ollama_model=%s llm_intent_timeout=%ds llm_response_timeout=%ds",
        PRODUCTION, USE_KNOWLEDGE_DB,
        get_ontology_path().exists(), get_restrictions_path().exists(),
        get_dynamic_ontology_path().exists(),
        bool(key), off, get_ollama_model(),
        LLM_INTENT_TIMEOUT, LLM_RESPONSE_TIMEOUT,
    )
