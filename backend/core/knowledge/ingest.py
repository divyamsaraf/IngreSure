"""
Layer 1 ingestion: ensure group + ingredients + aliases from curated sources.
Used by USDA, OFF, FAO, IFCT/INDB ingestion pipelines with canonical merge.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.knowledge.ingredient_db import IngredientKnowledgeDB, ALLOWED_INGREDIENT_SOURCES
from core.ontology.ingredient_schema import Ingredient
from core.normalization.normalizer import normalize_ingredient_key

logger = logging.getLogger(__name__)


def _ensure_group(
    client: Any,
    canonical_name: str,
    source: str,
    confidence: str = "high",
    **flags: Any,
) -> Optional[str]:
    """Create or get ingredient_group id for this canonical name. Returns group_id or None."""
    if source not in ALLOWED_INGREDIENT_SOURCES:
        source = "system"
    sel = (
        client.table("ingredient_groups")
        .select("id")
        .eq("canonical_name", canonical_name)
        .is_("superseded_by", None)
        .limit(1)
        .execute()
    )
    if sel.data:
        return sel.data[0]["id"]
    origin_type = "unknown"
    if flags.get("animal_origin"):
        origin_type = "animal"
    elif flags.get("plant_origin"):
        origin_type = "plant"
    elif flags.get("synthetic"):
        origin_type = "synthetic"
    elif flags.get("fungal"):
        origin_type = "fungal"
    elif flags.get("insect_derived"):
        origin_type = "insect"
    payload = {
        "canonical_name": canonical_name,
        "origin_type": origin_type,
        "animal_origin": bool(flags.get("animal_origin", False)),
        "plant_origin": bool(flags.get("plant_origin", False)),
        "synthetic": bool(flags.get("synthetic", False)),
        "fungal": bool(flags.get("fungal", False)),
        "insect_derived": bool(flags.get("insect_derived", False)),
        "animal_species": flags.get("animal_species"),
        "egg_source": bool(flags.get("egg_source", False)),
        "dairy_source": bool(flags.get("dairy_source", False)),
        "gluten_source": bool(flags.get("gluten_source", False)),
        "nut_source": flags.get("nut_source"),
        "soy_source": bool(flags.get("soy_source", False)),
        "sesame_source": bool(flags.get("sesame_source", False)),
        "alcohol_content": flags.get("alcohol_content"),
        "root_vegetable": bool(flags.get("root_vegetable", False)),
        "onion_source": bool(flags.get("onion_source", False)),
        "garlic_source": bool(flags.get("garlic_source", False)),
        "fermented": bool(flags.get("fermented", False)),
        "knowledge_state": "VERIFIED",
        "version": 1,
        "uncertainty_flags": flags.get("uncertainty_flags") or [],
        "derived_from": flags.get("derived_from") or [],
        "contains": flags.get("contains") or [],
        "may_contain": flags.get("may_contain") or [],
        "regions": flags.get("regions") or [],
    }
    ins = client.table("ingredient_groups").insert(payload).execute()
    if not ins.data:
        return None
    return ins.data[0]["id"]


def ensure_group_with_aliases(
    db: IngredientKnowledgeDB,
    canonical_name: str,
    aliases: List[str],
    source: str = "ontology",
    *,
    alias_type: str = "synonym",
    language: str = "en",
    region: Optional[str] = None,
    **group_flags: Any,
) -> Optional[str]:
    """
    Ensure a canonical group exists and all aliases point to it. Used by Layer 1 pipelines.
    If group already exists, only missing aliases are added. Returns group_id or None.
    """
    if not db.enabled or not db._client or not canonical_name:
        return None
    client = db._client
    group_id = _ensure_group(client, canonical_name, source, **group_flags)
    if not group_id:
        return None
    # Ensure we have one ingredient row for this group (use canonical name as normalized)
    canon_norm = normalize_ingredient_key(canonical_name)
    ing_sel = (
        client.table("ingredients")
        .select("id")
        .eq("group_id", group_id)
        .is_("superseded_by", None)
        .limit(1)
        .execute()
    )
    if not ing_sel.data:
        ing_ins = client.table("ingredients").insert({
            "name": canonical_name,
            "normalized_name": canon_norm,
            "group_id": group_id,
            "source": source,
            "confidence": "high",
            "version": 1,
        }).execute()
        if not ing_ins.data:
            return group_id
        ingredient_id = ing_ins.data[0]["id"]
    else:
        ingredient_id = ing_sel.data[0]["id"]
    # Add aliases (canonical + list); skip if normalized_alias already exists
    to_add = [canonical_name] + [a for a in aliases if a and a != canonical_name]
    for raw in to_add:
        norm = normalize_ingredient_key(raw)
        if not norm:
            continue
        existing = (
            client.table("ingredient_aliases")
            .select("id")
            .eq("normalized_alias", norm)
            .limit(1)
            .execute()
        )
        if existing.data:
            continue
        payload: Dict[str, Any] = {
            "alias": raw,
            "normalized_alias": norm,
            "ingredient_id": ingredient_id,
            "alias_type": "canonical" if raw == canonical_name else alias_type,
            "language": language,
        }
        if region is not None:
            payload["region"] = region
        try:
            client.table("ingredient_aliases").insert(payload).execute()
        except Exception as e:
            logger.debug("ingest alias insert skip norm=%s: %s", norm[:40], e)
    return group_id
