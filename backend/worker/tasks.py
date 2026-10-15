"""
Celery tasks for background ingredient enrichment (Item 18).

  - ``enrich_unknown_batch`` drains ``ike2_unknown_queue`` (status=pending),
    looks each key up via the external API fetcher, and writes successful
    results into ``ike2_*`` through the bulk spine (adapt -> validate_rows ->
    reconcile) as source ``enrichment_api`` (always DISCOVERED for new groups).
  - ``process_product_ingredients_batch`` resolves label tokens through the
    IKE-2 resolver; L5 misses are enqueued by the resolver itself.

Scheduled by Celery Beat (``worker.celery_app.beat_schedule``, Item 23).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, List

from worker.celery_app import celery_app
from core.knowledge.ingredient_db import IngredientKnowledgeDB
from core.external_apis.fetcher import fetch_ingredient_from_apis
from core.external_apis.base import EnrichmentResult
from core.knowledge.llm_classify import classify_ingredient_origin, apply_classification_to_ingredient
from core.knowledge.ike2.unknown_queue import TABLE as QUEUE_TABLE


logger = logging.getLogger(__name__)

ENRICHMENT_SOURCE = "enrichment_api"
# Beat re-runs the batch periodically; stop re-querying APIs for keys that
# keep failing so they don't starve newer unknowns.
MAX_ATTEMPTS = 5


def _get_db() -> IngredientKnowledgeDB:
    return IngredientKnowledgeDB()


def _make_writer(client):
    from core.knowledge.ike2.etl.bulk_inject import SupabaseWriter

    return SupabaseWriter(client)


def _enrichment_record(key: str, result: EnrichmentResult) -> dict[str, Any]:
    """Map an API hit onto a bulk-spine record keyed by the queue key, so the
    resolver's alias lookup on that key finds it. API aliases are not carried
    over (unreviewed single-name lookups must not claim other names)."""
    raw = result.ingredient.to_dict()
    raw["canonical_name"] = key
    raw["aliases"] = []
    return raw


@celery_app.task(name="enrich_unknown_batch")
def enrich_unknown_batch(min_frequency: int = 1, limit: int = 50) -> dict[str, Any]:
    from core.knowledge.ike2.etl.bulk_inject import inject

    db = _get_db()
    if not db.enabled:
        logger.warning("enrich_unknown_batch: knowledge DB not configured; skipping.")
        return {"processed": 0, "reason": "knowledge_db_disabled"}

    client = db._client  # type: ignore[attr-defined]
    try:
        rows: List[dict[str, Any]] = (
            client.table(QUEUE_TABLE)
            .select("*")
            .eq("status", "pending")
            .gte("frequency", min_frequency)
            .order("frequency", desc=True)  # type: ignore[arg-type]
            .limit(limit)
            .execute()
            .data
        ) or []
    except Exception as e:
        logger.error("enrich_unknown_batch: failed to read %s: %s", QUEUE_TABLE, e)
        return {"processed": 0, "error": str(e)}

    logger.info("enrich_unknown_batch: loaded %d queued unknowns (min_frequency=%d)", len(rows), min_frequency)
    counts = {"processed": 0, "resolved": 0, "rejected": 0, "exhausted": 0}

    for row in rows:
        key = row.get("normalized_key") or ""
        if not key:
            continue
        result = fetch_ingredient_from_apis(key, use_cache=True)
        if result.ingredient and result.confidence == "medium":
            try:
                classification = classify_ingredient_origin(key, description="")
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

        now_iso = datetime.now(timezone.utc).isoformat()
        enrichment = dict(row.get("enrichment") or {})
        enrichment["attempts"] = int(enrichment.get("attempts") or 0) + 1
        enrichment["last_attempt_at"] = now_iso
        update: dict[str, Any] = {"updated_at": now_iso}

        if result.ingredient and result.confidence != "low":
            enrichment["api_source"] = result.source
            enrichment["api_confidence"] = result.confidence
            try:
                writer = _make_writer(client)
                stats = inject([_enrichment_record(key, result)], ENRICHMENT_SOURCE, writer)
                if stats.rejected:
                    enrichment["reject"] = writer._rejects[0] if writer._rejects else None
                    update["status"] = "rejected"
                    counts["rejected"] += 1
                else:
                    update["status"] = "resolved"
                    update["classification_decision"] = f"{ENRICHMENT_SOURCE}:{result.source}"
                    counts["resolved"] += 1
            except Exception as e:
                logger.warning("enrich_unknown_batch: ike2 write failed key=%s: %s", key[:80], e)
        if "status" not in update and enrichment["attempts"] >= MAX_ATTEMPTS:
            update["status"] = "exhausted"
            counts["exhausted"] += 1

        update["enrichment"] = enrichment
        try:
            client.table(QUEUE_TABLE).update(update).eq("id", row["id"]).execute()
        except Exception as e:
            logger.warning("enrich_unknown_batch: failed to update queue row key=%s: %s", key[:80], e)
        counts["processed"] += 1

    return counts


@celery_app.task(name="process_product_ingredients_batch")
def process_product_ingredients_batch(
    ingredient_strings: List[str],
    *,
    min_tokens: int = 1,
) -> dict[str, Any]:
    """
    Flatten product ingredient strings and resolve each token via IKE-2.
    Unresolved (L5) tokens are enqueued to ike2_unknown_queue by the resolver.
    """
    from core.normalization.parser import flatten_ingredients
    from core.knowledge.ike2.resolver import resolve

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
            res = resolve(token, None)
            if res.status == "resolved":
                resolved_count += 1
            elif res.resolution_layer == "L5_unknown_queue":
                enqueued_count += 1
    return {"resolved": resolved_count, "enqueued": enqueued_count, "strings_processed": len(ingredient_strings)}


@celery_app.task(name="ike2_scheduled_audits")
def ike2_scheduled_audits() -> dict[str, Any]:
    """Item 12: run live IKE-2 audits; write report under docs/."""
    from scripts.ike2_item12_scheduled_audits import main as run_audits

    code = run_audits([])
    return {"exit_code": code}
