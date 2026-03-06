"""
ChEBI API connector for chemical entities (additives, compounds, E-numbers).
No API key. Base: https://www.ebi.ac.uk/chebi/backend/api/public/
Search: GET es_search/?query=... or GET compounds/?query=...
"""
import logging
import re
import urllib.parse
from typing import Optional

import requests

from core.ontology.ingredient_schema import Ingredient
from core.external_apis.base import EnrichmentResult, ConfidenceLevel

logger = logging.getLogger(__name__)

CHEBI_BASE = "https://www.ebi.ac.uk/chebi/backend/api/public"
CHEBI_SEARCH_URL = f"{CHEBI_BASE}/es_search/"
CHEBI_COMPOUND_URL = f"{CHEBI_BASE}/compound"


def _normalize_id(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower().strip())
    return s.strip("_") or "unknown"


def _infer_origin_from_entity(entity: dict) -> dict:
    """Infer dietary flags from ChEBI entity (ontology, comments)."""
    combined = ""
    for key in ("chebiAsciiName", "ascii_name", "name", "definition", "ontology", "comments"):
        v = entity.get(key)
        if isinstance(v, str):
            combined += " " + v.lower()
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and "data" in item:
                    combined += " " + str(item.get("data", "")).lower()
    if any(w in combined for w in ["animal", "mammal", "fish", "insect", "carmine", "gelatin", "cysteine", "l-cysteine"]):
        return {"animal_origin": True, "plant_origin": False, "synthetic": False}
    if any(w in combined for w in ["plant", "botanical"]):
        return {"animal_origin": False, "plant_origin": True, "synthetic": False}
    return {"animal_origin": False, "plant_origin": False, "synthetic": True}


def fetch_chebi(ingredient_query: str, timeout: int = 10) -> EnrichmentResult:
    """
    Search ChEBI by name. Returns EnrichmentResult.
    """
    if not ingredient_query or not ingredient_query.strip():
        return EnrichmentResult(None, "low", "chebi", "empty_query")
    name = ingredient_query.strip()[:200]
    params = {"query": name, "maxResults": 5}
    try:
        resp = requests.get(CHEBI_SEARCH_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.debug("ChEBI fetch failed query=%s: %s", name[:60], e)
        return EnrichmentResult(None, "low", "chebi", f"error:{type(e).__name__}")

    # ChEBI es_search: newer API returns {"results": [{"_id": "...", "_source": {...}}]}; legacy had hits/entities
    raw_list = data.get("results") or data.get("hits") or data.get("entities") if isinstance(data, dict) else (data if isinstance(data, list) else [])
    if not raw_list:
        return EnrichmentResult(None, "low", "chebi", "no_hits")
    hit = raw_list[0] if isinstance(raw_list[0], dict) else {}
    source = hit.get("_source") or hit
    chebi_id = source.get("chebi_accession") or hit.get("_id") or source.get("chebiId") or hit.get("id") or source.get("chebi_id")
    title = (source.get("ascii_name") or source.get("name") or source.get("chebiAsciiName") or name).strip()
    # Compound API expects numeric id or CHEBI:nnn
    compound_id = str(chebi_id).replace("CHEBI:", "").strip() or chebi_id
    if compound_id:
        try:
            full_resp = requests.get(f"{CHEBI_COMPOUND_URL}/{compound_id}/", timeout=timeout)
            if full_resp.ok:
                full = full_resp.json()
                title = (full.get("chebiAsciiName") or full.get("name") or title).strip()
                infer = _infer_origin_from_entity(full)
            else:
                infer = _infer_origin_from_entity(source)
        except Exception:
            infer = _infer_origin_from_entity(source)
    else:
        infer = _infer_origin_from_entity(source)
    ing_id = f"chebi_{_normalize_id(title)}"[:64]
    synonyms = source.get("synonyms") or source.get("Synonyms") or hit.get("synonyms") or []
    if isinstance(synonyms, str):
        synonyms = [synonyms]
    synonyms = [s for s in synonyms[:10] if isinstance(s, str)]
    ing = Ingredient(
        id=ing_id,
        canonical_name=title,
        aliases=synonyms if synonyms else [name],
        derived_from=[],
        contains=[],
        may_contain=[],
        animal_origin=infer.get("animal_origin", False),
        plant_origin=infer.get("plant_origin", False),
        synthetic=infer.get("synthetic", True),
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
        uncertainty_flags=["chebi_inferred"],
        regions=[],
    )
    confidence: ConfidenceLevel = "high" if title.lower() == name.lower() else "medium"
    return EnrichmentResult(ing, confidence, "chebi", f"chebiId={chebi_id} name={title[:80]}")


def fetch_chebi_by_id(chebi_id: str, timeout: int = 10) -> EnrichmentResult:
    """Fetch ChEBI entity by ID (e.g. CHEBI:15361)."""
    if not chebi_id:
        return EnrichmentResult(None, "low", "chebi", "empty_id")
    tid = str(chebi_id).strip().upper().replace("CHEBI:", "")
    url = f"{CHEBI_COMPOUND_URL}/{tid}/"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        entity = resp.json()
    except requests.RequestException as e:
        return EnrichmentResult(None, "low", "chebi", f"error:{type(e).__name__}")
    title = (entity.get("chebiAsciiName") or entity.get("name") or f"CHEBI:{tid}").strip()
    infer = _infer_origin_from_entity(entity)
    ing = Ingredient(
        id=f"chebi_{tid}"[:64],
        canonical_name=title,
        aliases=[],
        derived_from=[],
        contains=[],
        may_contain=[],
        animal_origin=infer.get("animal_origin", False),
        plant_origin=infer.get("plant_origin", False),
        synthetic=infer.get("synthetic", True),
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
        uncertainty_flags=["chebi_inferred"],
        regions=[],
    )
    return EnrichmentResult(ing, "high", "chebi", f"chebiId={tid}")
