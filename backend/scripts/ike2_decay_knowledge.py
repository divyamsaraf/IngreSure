#!/usr/bin/env python3
"""Item 4.1: demote stale IKE-2 knowledge_state by trust_refreshed_at TTL.

Decay applies only to ``ike2_ingredient_groups`` (not Coverage OS L2). See
``core.knowledge.ike2.decay`` module docstring.

Usage (from backend/):
  python scripts/ike2_decay_knowledge.py              # dry-run (default)
  python scripts/ike2_decay_knowledge.py --apply
  python scripts/ike2_decay_knowledge.py --as-of 2026-09-18T00:00:00Z --dry-run

Requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY for live DB access.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
os.chdir(_backend)

from dotenv import load_dotenv

load_dotenv(_backend / ".env")
load_dotenv(_backend.parent / ".env")

from core.knowledge.ike2.decay import plan_decay_row

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _parse_as_of(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def plan_decays(
    rows: list[dict[str, Any]],
    *,
    as_of: datetime,
) -> list[dict[str, Any]]:
    """Pure planner: eligible demotions (no DB writes)."""
    out: list[dict[str, Any]] = []
    for row in rows:
        state = row.get("knowledge_state") or ""
        refreshed = row.get("trust_refreshed_at")
        if not refreshed:
            continue
        nxt = plan_decay_row(
            knowledge_state=str(state),
            trust_refreshed_at=refreshed,
            as_of=as_of,
        )
        if nxt is None:
            continue
        out.append(
            {
                "id": row.get("id"),
                "canonical_name": row.get("canonical_name"),
                "from_state": state,
                "to_state": nxt,
                "trust_refreshed_at": refreshed,
            }
        )
    return out


def _fetch_groups(client) -> list[dict[str, Any]]:
    # Page if needed; local DBs are small enough for one select.
    resp = (
        client.table("ike2_ingredient_groups")
        .select("id,canonical_name,knowledge_state,trust_refreshed_at")
        .in_("knowledge_state", ["VERIFIED", "AUTO_CLASSIFIED"])
        .execute()
    )
    return list(resp.data or [])


def _apply_decays(client, planned: list[dict[str, Any]], *, as_of: datetime) -> int:
    applied = 0
    now_iso = as_of.isoformat()
    for item in planned:
        gid = item["id"]
        if not gid:
            continue
        client.table("ike2_ingredient_groups").update(
            {
                "knowledge_state": item["to_state"],
                # Do not refresh trust_refreshed_at on decay — clock stays historical.
                "updated_at": now_iso,
            }
        ).eq("id", gid).execute()
        applied += 1
    return applied


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Plan only (default). Use --no-dry-run / --apply to write.",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Shorthand for --no-dry-run (write demotions).",
    )
    p.add_argument("--as-of", default=None, help="ISO timestamp for the decay clock.")
    p.add_argument("--limit", type=int, default=None, help="Max planned rows to show/apply.")
    args = p.parse_args(argv)

    dry_run = False if args.apply else args.dry_run
    as_of = _parse_as_of(args.as_of)

    from core.knowledge.ingredient_db import IngredientKnowledgeDB

    db = IngredientKnowledgeDB()
    if not db.enabled:
        logger.error("Supabase not configured; set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return 2

    rows = _fetch_groups(db._client)
    planned = plan_decays(rows, as_of=as_of)
    if args.limit is not None:
        planned = planned[: args.limit]

    summary = {
        "as_of": as_of.isoformat(),
        "dry_run": dry_run,
        "scanned": len(rows),
        "eligible": len(planned),
        "by_transition": {},
        "sample": planned[:20],
    }
    for item in planned:
        key = f"{item['from_state']}->{item['to_state']}"
        summary["by_transition"][key] = summary["by_transition"].get(key, 0) + 1

    if dry_run:
        summary["applied"] = 0
        print(json.dumps(summary, indent=2, default=str))
        logger.info("dry-run: no writes (%d eligible)", len(planned))
        return 0

    applied = _apply_decays(db._client, planned, as_of=as_of)
    summary["applied"] = applied
    print(json.dumps(summary, indent=2, default=str))
    logger.info("applied %d demotions", applied)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
