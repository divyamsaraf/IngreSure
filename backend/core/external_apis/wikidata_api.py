"""
Wikidata API for synonym and regional name resolution (Layer 4).
Search: wbsearchentities; returns canonical label, description, aliases.
Use for regional/scientific synonyms and origin inference.
"""
import logging
import re
import urllib.parse
from typing import List, Optional

import requests

from core.ontology.ingredient_schema import Ingredient
from core.external_apis.base import EnrichmentResult, ConfidenceLevel

logger = logging.getLogger(__name__)

WIKIDATA_SEARCH_URL = "https://www.wikidata.org/w/api.php"
# Required by Wikimedia: https://meta.wikimedia.org/wiki/User-Agent_policy
WIKIDATA_HEADERS = {
    "User-Agent": "IngreSure/1.0 (https://github.com/ingresure; ingredient compliance checker)",
}


def _normalize_id(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower().strip())
    return s.strip("_") or "unknown"


def _infer_origin_from_description(description: str, label: str) -> dict:
    """Infer origin from Wikidata description/label."""
    t = (description or "").lower() + " " + (label or "").lower()
    if any(w in t for w in ["animal", "meat", "fish", "dairy", "egg", "insect", "shellfish"]):
        return {"animal_origin": True, "plant_origin": False, "synthetic": False}
    if any(w in t for w in ["plant", "vegetable", "fruit", "grain", "legume", "nut", "seed"]):
        return {"animal_origin": False, "plant_origin": True, "synthetic": False}
    if any(w in t for w in ["synthetic", "chemical", "compound", "additive"]):
        return {"animal_origin": False, "plant_origin": False, "synthetic": True}
    return {"animal_origin": False, "plant_origin": False, "synthetic": False}


def fetch_wikidata(ingredient_query: str, timeout: int = 10) -> EnrichmentResult:
    """
    Search Wikidata by label/alias. Returns EnrichmentResult with canonical label
    and aliases (suitable for regional/scientific alias_type when persisting).
    """
    if not ingredient_query or not ingredient_query.strip():
        return EnrichmentResult(None, "low", "wikidata", "empty_query")
    name = ingredient_query.strip()[:200]
    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": "en",
        "format": "json",
        "limit": 5,
    }
    try:
        resp = requests.get(WIKIDATA_SEARCH_URL, params=params, headers=WIKIDATA_HEADERS, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.debug("Wikidata fetch failed query=%s: %s", name[:60], e)
        return EnrichmentResult(None, "low", "wikidata", f"error:{type(e).__name__}")

    search = data.get("search") or []
    if not search:
        return EnrichmentResult(None, "low", "wikidata", "no_search_results")
    first = search[0]
    entity_id = first.get("id") or ""
    label = (first.get("label") or first.get("description") or name).strip()
    description = (first.get("description") or "").strip()
    # Aliases: Wikidata may return aliases in a separate call; for now use label + query
    aliases = [name] if name != label else []
    infer = _infer_origin_from_description(description, label)
    ing_id = f"wikidata_{entity_id or _normalize_id(label)}"[:64]
    ing = Ingredient(
        id=ing_id,
        canonical_name=label,
        aliases=aliases,
        derived_from=[],
        contains=[],
        may_contain=[],
        animal_origin=infer.get("animal_origin", False),
        plant_origin=infer.get("plant_origin", False),
        synthetic=infer.get("synthetic", False),
        fungal=False,
        insect_derived=False,
        animal_species=None,
        egg_source=False,
        dairy_source=False,
        gluten_source=False,
        nut_source=None,
        soy_source=False,
        sesame_source=False,
        alcohol_content=None,
        root_vegetable=False,
        onion_source=False,
        garlic_source=False,
        fermented=False,
        uncertainty_flags=["wikidata_inferred"],
        regions=[],
    )
    confidence: ConfidenceLevel = "high" if label.lower() == name.lower() else "medium"
    return EnrichmentResult(ing, confidence, "wikidata", f"id={entity_id} desc={description[:60]}")


# Languages to try for regional name → English resolution (order: en first, then common regional)
_RESOLVE_LANGUAGES: List[str] = [
    "en", "hi", "es", "fr", "zh", "de", "ar", "pt", "ja", "ko", "it", "ru", "th", "vi", "id", "tr",
]


def resolve_to_english_label(ingredient_query: str, timeout: int = 8) -> Optional[str]:
    """
    Resolve a regional/local ingredient name to its English label using Wikidata.
    Tries wbsearchentities with multiple languages; then wbgetentities for English label.
    Returns the English label string, or None if not found. Used to feed USDA/OFF with
    English terms when the user query is in another language.
    """
    if not ingredient_query or not ingredient_query.strip():
        return None
    name = ingredient_query.strip()[:200]
    entity_id: Optional[str] = None
    for lang in _RESOLVE_LANGUAGES:
        try:
            params = {
                "action": "wbsearchentities",
                "search": name,
                "language": lang,
                "format": "json",
                "limit": 1,
            }
            resp = requests.get(WIKIDATA_SEARCH_URL, params=params, headers=WIKIDATA_HEADERS, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.debug("Wikidata resolve_to_english search failed lang=%s query=%s: %s", lang, name[:50], e)
            continue
        search = data.get("search") or []
        if search:
            entity_id = (search[0].get("id") or "").strip()
            if entity_id:
                break
    if not entity_id:
        return None
    qid = entity_id if entity_id.upper().startswith("Q") else "Q" + entity_id
    try:
        params = {
            "action": "wbgetentities",
            "ids": qid,
            "format": "json",
            "props": "labels",
        }
        resp = requests.get(WIKIDATA_SEARCH_URL, params=params, headers=WIKIDATA_HEADERS, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.debug("Wikidata resolve_to_english getentities failed id=%s: %s", qid, e)
        return None
    entities = data.get("entities") or {}
    entity = entities.get(qid, {})
    if entity.get("missing") == "":
        return None
    labels = entity.get("labels") or {}
    en_label = (labels.get("en", {}) or {}).get("value")
    if en_label:
        return en_label.strip()
    if labels:
        first = list(labels.values())[0]
        if isinstance(first, dict) and first.get("value"):
            return first["value"].strip()
    return None


def fetch_wikidata_by_id(entity_id: str, timeout: int = 10) -> EnrichmentResult:
    """Fetch entity by Q-id. Uses wbgetentities."""
    if not entity_id:
        return EnrichmentResult(None, "low", "wikidata", "empty_id")
    qid = str(entity_id).strip().upper()
    if not qid.startswith("Q"):
        qid = "Q" + qid
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "format": "json",
        "props": "labels|descriptions|aliases",
    }
    try:
        resp = requests.get(WIKIDATA_SEARCH_URL, params=params, headers=WIKIDATA_HEADERS, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return EnrichmentResult(None, "low", "wikidata", f"error:{type(e).__name__}")
    entities = data.get("entities") or {}
    entity = entities.get(qid, {})
    if entity.get("missing") == "":
        return EnrichmentResult(None, "low", "wikidata", "entity_missing")
    labels = entity.get("labels") or {}
    label = (labels.get("en", {}).get("value") or list(labels.values())[0].get("value") if labels else "").strip()
    descs = entity.get("descriptions") or {}
    description = (descs.get("en", {}).get("value") or (list(descs.values())[0].get("value") if descs else "")).strip()
    aliases_list = entity.get("aliases") or {}
    en_aliases = aliases_list.get("en") or []
    aliases = [a.get("value") for a in en_aliases if isinstance(a, dict) and a.get("value")][:15]
    if not label:
        label = qid
    infer = _infer_origin_from_description(description, label)
    ing = Ingredient(
        id=f"wikidata_{qid}"[:64],
        canonical_name=label,
        aliases=aliases,
        derived_from=[],
        contains=[],
        may_contain=[],
        animal_origin=infer.get("animal_origin", False),
        plant_origin=infer.get("plant_origin", False),
        synthetic=infer.get("synthetic", False),
        fungal=False,
        insect_derived=False,
        animal_species=None,
        egg_source=False,
        dairy_source=False,
        gluten_source=False,
        nut_source=None,
        soy_source=False,
        sesame_source=False,
        alcohol_content=None,
        root_vegetable=False,
        onion_source=False,
        garlic_source=False,
        fermented=False,
        uncertainty_flags=["wikidata_inferred"],
        regions=[],
    )
    return EnrichmentResult(ing, "high", "wikidata", f"id={qid}")
