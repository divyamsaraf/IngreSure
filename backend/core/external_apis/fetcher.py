"""
Combined fetcher: USDA FDC → Open Food Facts → PubChem → ChEBI; in-memory cache with TTL.
Layer 2 (scientific) sources used when food APIs miss (e.g. E-numbers, chemical names).
"""
import hashlib
import logging
import re
import time
from typing import Optional

import requests

from core.ontology.ingredient_schema import Ingredient
from core.external_apis.base import EnrichmentResult, ConfidenceLevel
from core.external_apis.usda_fdc import fetch_usda_fdc
from core.external_apis.open_food_facts import fetch_open_food_facts
from core.external_apis.pubchem import fetch_pubchem
from core.external_apis.chebi import fetch_chebi
from core.external_apis.wikidata_api import fetch_wikidata, resolve_to_english_label
from core.external_apis.regional_names import get_canonical_queries, set_learned_english
from core.config import get_usda_fdc_api_key, get_open_food_facts_enabled, get_ollama_url, get_ollama_model

logger = logging.getLogger(__name__)

# In-memory cache: hash -> (EnrichmentResult, timestamp)
_api_cache: dict[str, tuple[EnrichmentResult, float]] = {}
_CACHE_MAX_ENTRIES = 500
_CACHE_TTL_SECONDS = 3600  # 1 hour


def _cache_key(normalized_query: str) -> str:
    return hashlib.sha256(normalized_query.encode()).hexdigest()[:32]


def _resolve_to_english_llm(query: str, timeout: int = 5) -> Optional[str]:
    """Optional LLM fallback: ask Ollama for English name when Wikidata missed. Returns one line or None."""
    if not query or not query.strip() or timeout <= 0:
        return None
    try:
        prompt = (
            f"What is the common English or scientific name for this food ingredient? "
            f"Reply with only the name, one line, no explanation. Ingredient: {query.strip()[:100]}"
        )
        r = requests.post(
            get_ollama_url(),
            json={"model": get_ollama_model(), "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        r.raise_for_status()
        text = (r.json().get("response") or "").strip()
        if not text:
            return None
        first_line = text.split("\n")[0].strip()
        if not first_line or len(first_line) > 150:
            return None
        if re.search(r"\b(unknown|don't know|cannot|can't|n/a)\b", first_line, re.I):
            return None
        return first_line
    except Exception as e:
        logger.debug("LLM resolve_to_english failed query=%s: %s", query[:50], e)
        return None


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
    Resolve unknown ingredient via external APIs: USDA FDC → Open Food Facts → PubChem → ChEBI → Wikidata.
    Cache is used only for successful resolutions; cached "no result" is ignored so we always
    call APIs for unknowns and get best/correct results.
    """
    key = _cache_key(normalized_ingredient_key)

    # Use cache only for successful resolutions so unknowns always trigger external API search.
    # Never return cached "no result" — we want best/correct results by calling APIs when unknown.
    if use_cache and key in _api_cache:
        cached, ts = _api_cache[key]
        if time.time() - ts < _CACHE_TTL_SECONDS and cached.ingredient is not None:
            logger.debug("ENRICHMENT cache hit (success) key=%s", normalized_ingredient_key[:50])
            return cached
        if key in _api_cache:
            del _api_cache[key]

    best: Optional[EnrichmentResult] = None
    query = normalized_ingredient_key.replace("_", " ").strip()
    # Regional/language handling: try English names first for USDA/OFF (static + learned + online resolve)
    query_variants = get_canonical_queries(normalized_ingredient_key)
    if not query_variants:
        query_variants = [query]
    if len(query_variants) == 1 and query_variants[0].replace("_", " ").strip().lower() == query.lower():
        english = resolve_to_english_label(query, timeout=min(timeout, 8))
        if not english:
            english = _resolve_to_english_llm(query, timeout=5)
        if english and english.strip().lower() != query.lower():
            query_variants = [english.strip(), query]
            set_learned_english(normalized_ingredient_key, english.strip())
            logger.info("ENRICHMENT resolved regional name query=%s -> english=%s", query[:50], english[:50])

    usda_key = get_usda_fdc_api_key()
    off_enabled = get_open_food_facts_enabled()

    if usda_key:
        for q in query_variants:
            q_display = q.replace("_", " ").strip()
            res = fetch_usda_fdc(q_display, usda_key, timeout=timeout)
            logger.info(
                "ENRICHMENT usda_fdc query=%s success=%s confidence=%s",
                q_display[:60], res.ingredient is not None, res.confidence,
            )
            if res.ingredient is not None and res.confidence != "low":
                best = res
                break
            if res.ingredient is not None and best is None:
                best = res

    if off_enabled and (best is None or best.confidence == "low"):
        for q in query_variants:
            q_display = q.replace("_", " ").strip()
            res = fetch_open_food_facts(q_display, timeout=timeout)
            logger.info(
                "ENRICHMENT open_food_facts query=%s success=%s confidence=%s",
                q_display[:60], res.ingredient is not None, res.confidence,
            )
            if res.ingredient is not None:
                if best is None or (res.confidence == "high" and (best.ingredient is None or best.confidence != "high")):
                    best = res
                if res.confidence != "low":
                    break

    # Layer 2: scientific/chemical (PubChem, ChEBI) when food APIs miss
    if best is None or best.confidence == "low":
        res = fetch_pubchem(query, timeout=timeout)
        logger.info(
            "ENRICHMENT pubchem query=%s success=%s confidence=%s",
            query[:60], res.ingredient is not None, res.confidence,
        )
        if res.ingredient is not None:
            if best is None or best.ingredient is None or (res.confidence == "high" and best.confidence != "high"):
                best = res
    if best is None or best.confidence == "low":
        res = fetch_chebi(query, timeout=timeout)
        logger.info(
            "ENRICHMENT chebi query=%s success=%s confidence=%s",
            query[:60], res.ingredient is not None, res.confidence,
        )
        if res.ingredient is not None:
            if best is None or best.ingredient is None or (res.confidence == "high" and best.confidence != "high"):
                best = res

    # Layer 4: knowledge graph (Wikidata) — try English variant first so "pearl millet" hits
    if best is None or best.confidence == "low":
        for q in query_variants:
            q_display = q.replace("_", " ").strip()
            res = fetch_wikidata(q_display, timeout=timeout)
            logger.info(
                "ENRICHMENT wikidata query=%s success=%s confidence=%s",
                q_display[:60], res.ingredient is not None, res.confidence,
            )
            if res.ingredient is not None:
                if best is None or best.ingredient is None or (res.confidence == "high" and (best.ingredient is None or best.confidence != "high")):
                    best = res
                if best is not None and best.confidence != "low":
                    break

    if best is None:
        best = EnrichmentResult(None, "low", "none", "no_result")

    # Auto-expand: persist regional -> canonical so next time we don't need online resolve
    if best.ingredient and best.ingredient.canonical_name:
        canon = (best.ingredient.canonical_name or "").strip()
        if canon and canon.lower() != query.lower():
            set_learned_english(normalized_ingredient_key, canon)

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

    # Cache only successful results so next time we serve from cache; never cache "no result".
    # This way unknown ingredients always trigger external API search until we get a real resolution.
    if use_cache and best.ingredient is not None:
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
