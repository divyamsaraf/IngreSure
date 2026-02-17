"""
Combined fetcher: try USDA FDC then Open Food Facts; optional in-memory cache.
"""
import hashlib
import logging
from typing import Optional

from core.ontology.ingredient_schema import Ingredient
from core.external_apis.base import EnrichmentResult, ConfidenceLevel
from core.external_apis.usda_fdc import fetch_usda_fdc
from core.external_apis.open_food_facts import fetch_open_food_facts
from core.config import get_usda_fdc_api_key, get_open_food_facts_enabled

logger = logging.getLogger(__name__)

# Simple in-memory cache: normalized_key -> (EnrichmentResult, timestamp). Optional TTL later.
_api_cache: dict[str, tuple[EnrichmentResult, float]] = {}
_CACHE_MAX_ENTRIES = 500


def _cache_key(normalized_query: str) -> str:
    return hashlib.sha256(normalized_query.encode()).hexdigest()[:32]


def fetch_ingredient_from_apis(
    normalized_ingredient_key: str,
    use_cache: bool = True,
    timeout: int = 10,
) -> EnrichmentResult:
    """
    Try USDA FDC (if key set) then Open Food Facts. Return first non-low result or best available.
    Logs API fetch success/failure and confidence.
    """
    key = _cache_key(normalized_ingredient_key)
    if use_cache and key in _api_cache:
        cached, _ = _api_cache[key]
        logger.debug("ENRICHMENT cache hit key=%s", normalized_ingredient_key[:50])
        return cached

    best: Optional[EnrichmentResult] = None
    query = normalized_ingredient_key.replace("_", " ").strip()

    # Read API config at call time (not import time) so .env changes are picked up
    usda_key = get_usda_fdc_api_key()
    off_enabled = get_open_food_facts_enabled()

    if usda_key:
        res = fetch_usda_fdc(query, usda_key, timeout=timeout)
        logger.info(
            "ENRICHMENT API fetch usda_fdc query=%s success=%s confidence=%s",
            query[:60], res.ingredient is not None, res.confidence,
        )
        if res.ingredient is not None and res.confidence != "low":
            best = res
        elif res.ingredient is not None and best is None:
            best = res
    else:
        logger.warning("ENRICHMENT skip USDA FDC (no API key set in USDA_FDC_API_KEY)")

    if off_enabled and (best is None or best.confidence == "low"):
        res = fetch_open_food_facts(query, timeout=timeout)
        logger.info(
            "ENRICHMENT API fetch open_food_facts query=%s success=%s confidence=%s",
            query[:60], res.ingredient is not None, res.confidence,
        )
        if res.ingredient is not None:
            if best is None or (res.confidence == "high" and best.confidence != "high"):
                best = res
            elif best.confidence == "medium" and res.confidence == "high":
                best = res

    if best is None:
        best = EnrichmentResult(None, "low", "none", "no_result")
    if best.ingredient is None:
        logger.info(
            "EXTERNAL_LOOKUP failed normalized_key=%s source=%s reason=%s",
            normalized_ingredient_key[:80], best.source, best.raw_response_summary or "no_result",
        )
    else:
        logger.info(
            "EXTERNAL_LOOKUP resolved normalized_key=%s canonical_name=%s source=%s confidence=%s",
            normalized_ingredient_key[:80], (best.ingredient.canonical_name or "")[:80], best.source, best.confidence,
        )

    if use_cache and len(_api_cache) < _CACHE_MAX_ENTRIES:
        import time
        _api_cache[key] = (best, time.time())

    return best


def enrich_unknown_ingredient(
    raw_input: str,
    normalized_key: str,
    use_cache: bool = True,
) -> EnrichmentResult:
    """
    Entry point for enrichment: fetch from APIs and return result.
    Caller can add to dynamic ontology if confidence is high, or log for human review if medium.
    """
    return fetch_ingredient_from_apis(normalized_key, use_cache=use_cache)


def clear_enrichment_cache() -> None:
    """Clear in-memory API cache (e.g. for tests)."""
    global _api_cache
    _api_cache = {}
