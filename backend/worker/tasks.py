"""
Celery tasks for background ingredient enrichment.

Phase 4 scope:
  - Define task entry points that can be scheduled or triggered manually.
  - Use the existing external API fetcher to enrich unknown ingredients.
  - Write results into the new Supabase knowledge tables where possible.

These tasks are safe to leave dormant; nothing in the FastAPI app depends
on them yet. They only run when the Celery worker is started explicitly.
"""

from __future__ import annotations

import logging
from typing import Any, List

from worker.celery_app import celery_app
from core.knowledge.ingredient_db import IngredientKnowledgeDB
from core.external_apis.fetcher import fetch_ingredient_from_apis
from core.external_apis.base import EnrichmentResult
from core.knowledge.llm_classify import classify_ingredient_origin, apply_classification_to_ingredient


logger = logging.getLogger(__name__)


def _get_db() -> IngredientKnowledgeDB:
    return IngredientKnowledgeDB()


@celery_app.task(name="enrich_unknown_batch")
def enrich_unknown_batch(min_frequency: int = 1, limit: int = 50) -> dict[str, Any]:
    """
    Background job: enrich a batch of unknown ingredients using external APIs.

    Current behavior (Phase 4):
      - Reads from unknown_ingredients table if Supabase is configured.
      - Logs what it *would* do; actual insert/update logic into
        ingredient_groups / ingredients / ingredient_aliases is left for
        a later, fully wired phase to avoid accidental schema misuse.
    """
    db = _get_db()
    if not db.enabled:
        logger.warning("enrich_unknown_batch: knowledge DB not configured; skipping.")
        return {"processed": 0, "reason": "knowledge_db_disabled"}

    client = db._client  # type: ignore[attr-defined]
    try:
        resp = (
            client.table("unknown_ingredients")
            .select("*")
            .eq("resolved", False)
            .gte("frequency", min_frequency)
            .order("frequency", desc=True)  # type: ignore[arg-type]
            .limit(limit)
            .execute()
        )
    except Exception as e:
        logger.error("enrich_unknown_batch: failed to read unknown_ingredients: %s", e)
        return {"processed": 0, "error": str(e)}

    rows: List[dict[str, Any]] = resp.data or []
    logger.info("enrich_unknown_batch: loaded %d unknown ingredients (min_frequency=%d)", len(rows), min_frequency)

    processed = 0
    for row in rows:
        key = row.get("normalized_key") or ""
        if not key:
            continue
        result = fetch_ingredient_from_apis(key, use_cache=True)
        # Optional LLM classification when APIs return medium confidence or inferred flags
        if result.ingredient and result.confidence == "medium":
            try:
                classification = classify_ingredient_origin(key, description="", timeout=15)
                if classification:
                    updated = apply_classification_to_ingredient(result.ingredient, classification)
                    result = EnrichmentResult(
                        updated, result.confidence, result.source, result.raw_response_summary
                    )
            except Exception as e:
                logger.debug("enrich_unknown_batch: llm classify skip key=%s: %s", key[:40], e)
        logger.info(
            "enrich_unknown_batch: lookup key=%s success=%s confidence=%s source=%s",
            key[:80], bool(result.ingredient), result.confidence, result.source,
        )
        # Always update resolution_attempts and last_attempt_at for traceability
        now_iso = None
        try:
            from datetime import datetime, timezone
            now_iso = datetime.now(timezone.utc).isoformat()
        except Exception:
            pass
        attempts = (row.get("resolution_attempts") or 0) + 1
        base_update = {
            "resolution_attempts": attempts,
            "last_attempt_at": now_iso,
        }
        if result.ingredient and result.confidence != "low":
            group_id = db.upsert_from_enrichment(result, normalized_key=key)
            # Mark unknown as resolved when we successfully persisted it
            try:
                update = {
                    **base_update,
                    "resolved": True,
                    "resolved_group_id": group_id,
                    "resolution_source": result.source,
                }
                client.table("unknown_ingredients").update(update).eq("id", row["id"]).execute()
            except Exception as e:
                logger.warning("enrich_unknown_batch: failed to update unknown_ingredients for key=%s: %s", key, e)
        else:
            try:
                client.table("unknown_ingredients").update(base_update).eq("id", row["id"]).execute()
            except Exception as e:
                logger.debug("enrich_unknown_batch: failed to update last_attempt_at for key=%s: %s", key, e)

        processed += 1

    return {"processed": processed}


@celery_app.task(name="process_product_ingredients_batch")
def process_product_ingredients_batch(
    ingredient_strings: List[str],
    *,
    min_tokens: int = 1,
) -> dict[str, Any]:
    """
    Layer 3: Flatten product ingredient strings, resolve each token or enqueue to unknown_ingredients.
    Call with a list of raw label strings (e.g. from OFF bulk). Unresolved tokens go to DB for discovery.
    """
    from core.normalization.parser import flatten_ingredients
    from core.knowledge.canonicalizer import CanonicalResolver
    from core.normalization.normalizer import normalize_ingredient_key

    db = _get_db()
    resolver = CanonicalResolver()
    resolved_count = 0
    enqueued_count = 0
    for raw in ingredient_strings:
        if not raw or not isinstance(raw, str):
            continue
        tokens = flatten_ingredients(raw)
        if len(tokens) < min_tokens:
            continue
        for token in tokens:
            if not token:
                continue
            res = resolver.resolve_with_fallback(token, try_api=False, log_unknown=True)
            if res.ingredient is not None:
                resolved_count += 1
            else:
                enqueued_count += 1
                # log_unknown=True already routes to unknown_ingredients when DB enabled
    return {"resolved": resolved_count, "enqueued": enqueued_count, "strings_processed": len(ingredient_strings)}

