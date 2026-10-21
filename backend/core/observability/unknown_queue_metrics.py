"""Read-only unknown-queue size for /metrics. Does not enqueue or edit queue rows."""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def unknown_queue_snapshot() -> dict[str, Any]:
    """Best-effort pending/total counts. Returns nulls when Supabase is unset."""
    pending: Optional[int] = None
    total: Optional[int] = None
    try:
        from core.knowledge.ingredient_db import get_supabase_config
        from core.knowledge.ike2.unknown_queue import TABLE

        cfg = get_supabase_config()
        if not cfg:
            return {"pending": None, "total": None, "available": False}
        from supabase import create_client

        client = create_client(cfg.url, cfg.key)
        total = _count(client, TABLE, status=None)
        pending = _count(client, TABLE, status="pending")
        return {"pending": pending, "total": total, "available": True}
    except Exception as exc:
        logger.debug("unknown_queue snapshot skipped: %s", exc)
        return {"pending": pending, "total": total, "available": False}


def _count(client: Any, table: str, *, status: Optional[str]) -> Optional[int]:
    query = client.table(table).select("id", count="exact")
    if status:
        query = query.eq("status", status)
    result = query.limit(1).execute()
    count = getattr(result, "count", None)
    if count is None:
        data = getattr(result, "data", None) or []
        return len(data)
    return int(count)
