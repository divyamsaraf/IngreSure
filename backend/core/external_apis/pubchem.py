"""
PubChem PUG REST API connector for chemical ingredients, E-numbers, additives.
No API key. Rate limit: ~5 requests/second.
Search by name: https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/json
"""
import logging
import re
import urllib.parse
from typing import Optional

import requests

from core.ontology.ingredient_schema import Ingredient
from core.external_apis.base import EnrichmentResult, ConfidenceLevel

logger = logging.getLogger(__name__)

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name"


def _normalize_id(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower().strip())
    return s.strip("_") or "unknown"


def _infer_origin_from_synonyms_and_title(synonyms: list, title: str) -> dict:
    """Infer dietary flags from compound name/synonyms (e.g. cysteine -> can be animal-derived)."""
    t = (title or "").lower()
    syn_text = " ".join((s or "").lower() for s in (synonyms or [])[:20])
    combined = f"{t} {syn_text}"
    # Common animal-derived compounds
    if any(w in combined for w in ["cysteine", "l-cysteine", "e920", "hair", "keratin", "gelatin", "collagen"]):
        return {"animal_origin": True, "plant_origin": False, "synthetic": False}
    if any(w in combined for w in ["carmine", "e120", "cochineal"]):
        return {"animal_origin": True, "plant_origin": False, "insect_derived": True}
    # Default for organic/chemical: often synthetic or plant-derived
    return {"animal_origin": False, "plant_origin": False, "synthetic": True}


def fetch_pubchem(ingredient_query: str, timeout: int = 10) -> EnrichmentResult:
    """
    Search PubChem by compound name. Returns EnrichmentResult.
    Chemical compounds are typically synthetic unless we infer animal/plant from name.
    """
    if not ingredient_query or not ingredient_query.strip():
        return EnrichmentResult(None, "low", "pubchem", "empty_query")
    name = ingredient_query.strip()[:200]
    encoded = urllib.parse.quote(name, safe="")
    url = f"{PUBCHEM_BASE}/{encoded}/JSON"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.debug("PubChem fetch failed query=%s: %s", name[:60], e)
        return EnrichmentResult(None, "low", "pubchem", f"error:{type(e).__name__}")

    pc = data.get("PC_Compounds") or []
    if not pc:
        return EnrichmentResult(None, "low", "pubchem", "no_compounds")
    comp = pc[0]
    props = comp.get("props") or []
    title = ""
    synonyms: list = []
    for p in props:
        if p.get("urn", {}).get("label") == "IUPAC Name" or p.get("urn", {}).get("label") == "Title":
            val = p.get("value", {})
            if isinstance(val, dict) and "sval" in val:
                title = (val.get("sval") or "").strip()
            elif isinstance(val, str):
                title = val.strip()
        if p.get("urn", {}).get("label") == "Synonym":
            val = p.get("value", {})
            if isinstance(val, dict) and "sval" in val:
                synonyms = [val["sval"]] if isinstance(val["sval"], str) else list(val.get("sval") or [])
            elif isinstance(val, list):
                synonyms = val[:15]
    if not title:
        title = name
    infer = _infer_origin_from_synonyms_and_title(synonyms, title)
    ing_id = f"pubchem_{_normalize_id(title)}"[:64]
    ing = Ingredient(
        id=ing_id,
        canonical_name=title,
        aliases=synonyms[:10] if synonyms else [name],
        derived_from=[],
        contains=[],
        may_contain=[],
        animal_origin=infer.get("animal_origin", False),
        plant_origin=infer.get("plant_origin", False),
        synthetic=infer.get("synthetic", True),
        fungal=False,
        insect_derived=infer.get("insect_derived", False),
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
        uncertainty_flags=["pubchem_inferred"],
        regions=[],
    )
    confidence: ConfidenceLevel = "high" if title and title.lower() == name.lower() else "medium"
    return EnrichmentResult(ing, confidence, "pubchem", f"title={title[:80]}")


def fetch_pubchem_by_cid(cid: int, timeout: int = 10) -> EnrichmentResult:
    """Fetch compound by PubChem CID. Returns EnrichmentResult."""
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/JSON"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return EnrichmentResult(None, "low", "pubchem", f"error:{type(e).__name__}")
    pc = data.get("PC_Compounds") or []
    if not pc:
        return EnrichmentResult(None, "low", "pubchem", "no_compounds")
    comp = pc[0]
    props = comp.get("props") or []
    title = f"PubChem_{cid}"
    for p in props:
        if p.get("urn", {}).get("label") in ("IUPAC Name", "Title", "Display Name"):
            val = p.get("value", {})
            if isinstance(val, dict) and "sval" in val:
                title = (val.get("sval") or title) if isinstance(val.get("sval"), str) else title
            elif isinstance(val, str):
                title = val
            if title and title != f"PubChem_{cid}":
                break
    infer = _infer_origin_from_synonyms_and_title([], title)
    ing = Ingredient(
        id=f"pubchem_{cid}",
        canonical_name=title,
        aliases=[],
        derived_from=[],
        contains=[],
        may_contain=[],
        animal_origin=infer.get("animal_origin", False),
        plant_origin=infer.get("plant_origin", False),
        synthetic=infer.get("synthetic", True),
        fungal=False,
        insect_derived=infer.get("insect_derived", False),
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
        uncertainty_flags=["pubchem_inferred"],
        regions=[],
    )
    return EnrichmentResult(ing, "medium", "pubchem", f"cid={cid}")
