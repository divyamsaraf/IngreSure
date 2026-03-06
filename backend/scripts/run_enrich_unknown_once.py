#!/usr/bin/env python3
"""
Run one batch of unknown-ingredient enrichment (no Celery/Redis required).

Uses same logic as worker task enrich_unknown_batch: read unknown_ingredients,
fetch from APIs (USDA → OFF → PubChem → ChEBI → Wikidata), upsert to
ingredient_groups/ingredients/ingredient_aliases, mark unknown as resolved.

Requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY in env or backend/.env
Optional: USDA_FDC_API_KEY for better food matches

Run from backend: python scripts/run_enrich_unknown_once.py [limit]
  limit: max unknowns to process (default 10)
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
os.chdir(_backend)

from dotenv import load_dotenv
load_dotenv(_backend / ".env")
load_dotenv(_backend.parent / ".env")

# Replicate worker task logic (no Celery)
from core.knowledge.ingredient_db import IngredientKnowledgeDB
from core.external_apis.fetcher import fetch_ingredient_from_apis
from core.external_apis.base import EnrichmentResult
from core.knowledge.llm_classify import classify_ingredient_origin, apply_classification_to_ingredient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def run_batch(limit: int = 10) -> dict:
    db = IngredientKnowledgeDB()
    if not db.enabled:
        logger.warning("Supabase not configured; set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return {"processed": 0, "reason": "knowledge_db_disabled"}

    client = db._client
    try:
        resp = (
            client.table("unknown_ingredients")
            .select("*")
            .eq("resolved", False)
            .gte("frequency", 1)
            .order("frequency", desc=True)
            .limit(limit)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to read unknown_ingredients: %s", e)
        return {"processed": 0, "error": str(e)}

    rows = resp.data or []
    logger.info("Loaded %d unknown ingredients (limit=%d)", len(rows), limit)
    processed = 0
    for row in rows:
        key = row.get("normalized_key") or ""
        if not key:
            continue
        result = fetch_ingredient_from_apis(key, use_cache=True)
        if result.ingredient and result.confidence == "medium":
            try:
                classification = classify_ingredient_origin(key, description="", timeout=15)
                if classification:
                    updated = apply_classification_to_ingredient(result.ingredient, classification)
                    result = EnrichmentResult(
                        updated, result.confidence, result.source, result.raw_response_summary
                    )
            except Exception as e:
                logger.debug("LLM classify skip key=%s: %s", key[:40], e)
        logger.info(
            "key=%s success=%s confidence=%s source=%s",
            key[:60], bool(result.ingredient), result.confidence, result.source,
        )
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()
        attempts = (row.get("resolution_attempts") or 0) + 1
        base_update = {"resolution_attempts": attempts, "last_attempt_at": now_iso}
        if result.ingredient and result.confidence != "low":
            group_id = db.upsert_from_enrichment(result, normalized_key=key)
            if group_id:
                try:
                    client.table("unknown_ingredients").update({
                        **base_update,
                        "resolved": True,
                        "resolved_group_id": group_id,
                        "resolution_source": result.source,
                    }).eq("id", row["id"]).execute()
                except Exception as e:
                    logger.warning("Failed to update unknown_ingredients for key=%s: %s", key, e)
            else:
                try:
                    client.table("unknown_ingredients").update(base_update).eq("id", row["id"]).execute()
                except Exception as e:
                    logger.debug("Failed to update last_attempt_at for key=%s: %s", key, e)
        else:
            try:
                client.table("unknown_ingredients").update(base_update).eq("id", row["id"]).execute()
            except Exception as e:
                logger.debug("Failed to update last_attempt_at for key=%s: %s", key, e)
        processed += 1
    return {"processed": processed, "resolved": sum(1 for r in rows if r.get("normalized_key"))}


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    out = run_batch(limit=limit)
    print("Result:", out)
    sys.exit(0 if out.get("processed", 0) >= 0 else 1)
