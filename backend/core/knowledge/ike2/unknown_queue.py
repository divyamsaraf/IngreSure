"""IKE-2 unknown-ingredient discovery queue (Item 18).

``ike2_unknown_queue`` columns: normalized_key (unique), frequency, enrichment
(jsonb), classification_decision, status, created_at, updated_at. Fields the
legacy ``unknown_ingredients`` table had as columns (raw inputs, restriction
samples, attempts, last attempt) live inside ``enrichment``.

Writes here are telemetry: they must never raise into, delay, or change a
verdict. The resolver submits L5 misses to a single background thread.
"""
from __future__ import annotations

import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

TABLE = "ike2_unknown_queue"
MAX_RAW_INPUTS = 20

# Test artifacts seen in legacy unknown_ingredients / dynamic_ontology.
_JUNK_PATTERN = re.compile(r"^zyzzx\b")

_executor: Optional[ThreadPoolExecutor] = None
_executor_lock = threading.Lock()
_client = None


def is_junk_key(key: str) -> bool:
    k = (key or "").strip()
    return len(k) <= 1 or bool(_JUNK_PATTERN.match(k))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_client():
    global _client
    if _client is None:
        from core.knowledge.ingredient_db import get_supabase_config

        cfg = get_supabase_config()
        if not cfg:
            return None
        from supabase import create_client

        _client = create_client(cfg.url, cfg.key)
    return _client


def _with_raw_input(enrichment: Optional[dict], raw_input: Optional[str]) -> dict:
    out = dict(enrichment or {})
    raws = list(out.get("raw_inputs") or [])
    if raw_input and raw_input not in raws:
        raws = (raws + [raw_input])[:MAX_RAW_INPUTS]
    out["raw_inputs"] = raws
    return out


def enqueue_unknown(normalized_key: str, raw_input: Optional[str] = None, *, client=None) -> bool:
    """Upsert one discovery hit: insert pending at frequency 1, or bump frequency.

    Returns False (never raises) on junk keys, missing config, or write failure.
    """
    if not normalized_key or is_junk_key(normalized_key):
        return False
    try:
        c = client if client is not None else _default_client()
        if c is None:
            return False
        rows = (
            c.table(TABLE)
            .select("id, frequency, enrichment")
            .eq("normalized_key", normalized_key)
            .limit(1)
            .execute()
            .data
        )
        if rows:
            row = rows[0]
            c.table(TABLE).update({
                "frequency": (row.get("frequency") or 0) + 1,
                "enrichment": _with_raw_input(row.get("enrichment"), raw_input),
                "updated_at": _now(),
            }).eq("id", row["id"]).execute()
        else:
            c.table(TABLE).insert({
                "normalized_key": normalized_key,
                "frequency": 1,
                "status": "pending",
                "enrichment": _with_raw_input(None, raw_input),
            }).execute()
        return True
    except Exception as exc:
        logger.warning("IKE2_UNKNOWN_QUEUE_WRITE_FAILED key=%s: %s", normalized_key[:80], exc)
        return False


def record_miss(normalized_key: str, raw_input: Optional[str] = None) -> None:
    """Fire-and-forget enqueue from the resolver hot path. Never raises."""
    global _executor
    try:
        if not normalized_key or is_junk_key(normalized_key):
            return
        with _executor_lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ike2-unknown-queue")
            _executor.submit(enqueue_unknown, normalized_key, raw_input)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("IKE2_UNKNOWN_QUEUE_WRITE_FAILED key=%s: %s", (normalized_key or "")[:80], exc)


def plan_legacy_migration(legacy_rows: list[dict], existing: dict[str, dict]) -> list[dict[str, Any]]:
    """One-shot legacy ``unknown_ingredients`` -> queue plan (Item 18 step 3).

    Only unresolved, non-junk rows move. Idempotent on frequency: an existing
    queue row keeps ``max(existing, legacy)`` so re-runs never double-count.
    Returns ops ``{"op": "insert"|"update"|"skip", "key", "row"?, "reason"?}``.
    """
    ops: list[dict[str, Any]] = []
    for lr in legacy_rows:
        key = (lr.get("normalized_key") or "").strip()
        if lr.get("resolved"):
            ops.append({"op": "skip", "key": key, "reason": "resolved"})
            continue
        if not key or is_junk_key(key):
            ops.append({"op": "skip", "key": key, "reason": "junk"})
            continue
        legacy_freq = int(lr.get("frequency") or 0)
        legacy_fields = {
            "raw_inputs": list(lr.get("raw_inputs") or [])[:MAX_RAW_INPUTS],
            "restriction_ids_sample": list(lr.get("restriction_ids_sample") or []),
            "profile_context_sample": lr.get("profile_context_sample"),
            "attempts": int(lr.get("resolution_attempts") or 0),
            "last_attempt_at": lr.get("last_attempt_at"),
            "migrated_from": "unknown_ingredients",
        }
        cur = existing.get(key)
        if cur is None:
            ops.append({"op": "insert", "key": key, "row": {
                "normalized_key": key,
                "frequency": max(legacy_freq, 1),
                "status": "pending",
                "enrichment": legacy_fields,
            }})
            continue
        cur_freq = int(cur.get("frequency") or 0)
        if cur_freq >= legacy_freq and (cur.get("enrichment") or {}).get("migrated_from"):
            ops.append({"op": "skip", "key": key, "reason": "already_migrated"})
            continue
        enrichment = dict(cur.get("enrichment") or {})
        for raw in legacy_fields["raw_inputs"]:
            enrichment = _with_raw_input(enrichment, raw)
        for k in ("restriction_ids_sample", "profile_context_sample", "last_attempt_at"):
            enrichment.setdefault(k, legacy_fields[k])
        enrichment["attempts"] = max(int(enrichment.get("attempts") or 0), legacy_fields["attempts"])
        enrichment["migrated_from"] = "unknown_ingredients"
        ops.append({"op": "update", "key": key, "id": cur.get("id"), "row": {
            "frequency": max(cur_freq, legacy_freq),
            "enrichment": enrichment,
        }})
    return ops
