"""
Combined fetcher: try USDA FDC then Open Food Facts; in-memory cache with TTL.
"""
import hashlib
import logging
import time
from typing import Optional

from core.ontology.ingredient_schema import Ingredient
from core.external_apis.base import EnrichmentResult, ConfidenceLevel
from core.external_apis.usda_fdc import fetch_usda_fdc
from core.external_apis.open_food_facts import fetch_open_food_facts
from core.config import get_usda_fdc_api_key, get_open_food_facts_enabled

logger = logging.getLogger(__name__)

# In-memory cache: hash -> (EnrichmentResult, timestamp)
_api_cache: dict[str, tuple[EnrichmentResult, float]] = {}
_CACHE_MAX_ENTRIES = 500
_CACHE_TTL_SECONDS = 3600  # 1 hour


def _cache_key(normalized_query: str) -> str:
    return hashlib.sha256(normalized_query.encode()).hexdigest()[:32]


def _evict_expired() -> None:
    """Remove expired entries when cache is full."""
    if len(_api_cache) < _CACHE_MAX_ENTRIES:
        return
    now = time.time()
    expired = [k for k, (_, ts) in _api_cache.items() if now - ts > _CACHE_TTL_SECONDS]
    for k in expired:
        del _api_cache[k]


def fetch_ingredient_from_apis(
    normalized_ingredient_key: str,
    use_cache: bool = True,
    timeout: int = 10,
) -> EnrichmentResult:
    """
    Try USDA FDC (if key set) then Open Food Facts.
    Return first non-low result or best available.
    """
    key = _cache_key(normalized_ingredient_key)

    # Check cache (with TTL)
    if use_cache and key in _api_cache:
        cached, ts = _api_cache[key]
        if time.time() - ts < _CACHE_TTL_SECONDS:
            logger.debug("ENRICHMENT cache hit key=%s", normalized_ingredient_key[:50])
            return cached
        else:
            del _api_cache[key]

    best: Optional[EnrichmentResult] = None
    query = normalized_ingredient_key.replace("_", " ").strip()

    usda_key = get_usda_fdc_api_key()
    off_enabled = get_open_food_facts_enabled()

    if usda_key:
        res = fetch_usda_fdc(query, usda_key, timeout=timeout)
        logger.info(
            "ENRICHMENT usda_fdc query=%s success=%s confidence=%s",
            query[:60], res.ingredient is not None, res.confidence,
        )
        if res.ingredient is not None and res.confidence != "low":
            best = res
        elif res.ingredient is not None and best is None:
            best = res

    if off_enabled and (best is None or best.confidence == "low"):
        res = fetch_open_food_facts(query, timeout=timeout)
        logger.info(
            "ENRICHMENT open_food_facts query=%s success=%s confidence=%s",
            query[:60], res.ingredient is not None, res.confidence,
        )
        if res.ingredient is not None:
            if best is None or (res.confidence == "high" and best.confidence != "high"):
                best = res

    if best is None:
        best = EnrichmentResult(None, "low", "none", "no_result")

    if best.ingredient is None:
        logger.info(
            "EXTERNAL_LOOKUP failed key=%s source=%s",
            normalized_ingredient_key[:80], best.source,
        )
    else:
        logger.info(
            "EXTERNAL_LOOKUP resolved key=%s name=%s source=%s confidence=%s",
            normalized_ingredient_key[:80],
            (best.ingredient.canonical_name or "")[:80],
            best.source, best.confidence,
        )

    # Store in cache with eviction
    if use_cache:
        _evict_expired()
        if len(_api_cache) < _CACHE_MAX_ENTRIES:
            _api_cache[key] = (best, time.time())

    return best


def enrich_unknown_ingredient(
    raw_input: str,
    normalized_key: str,
    use_cache: bool = True,
) -> EnrichmentResult:
    """Entry point for enrichment: fetch from APIs and return result."""
    return fetch_ingredient_from_apis(normalized_key, use_cache=use_cache)


def clear_enrichment_cache() -> None:
    """Clear in-memory API cache (e.g. for tests)."""
    global _api_cache
    _api_cache = {}
