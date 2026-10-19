#!/usr/bin/env python3
"""One-shot: legacy ``unknown_ingredients`` (unresolved) -> ``ike2_unknown_queue`` (Item 18).

Skips junk keys (single-character, ``zyzzx…`` test artifacts) and resolved rows.
Idempotent: frequency on conflict is ``max(existing, legacy)``. Legacy rows are
left untouched. Dry-run by default; pass ``--apply`` to write.

Run from backend: python scripts/ike2_migrate_unknown_queue.py [--apply]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
os.chdir(_backend)

from dotenv import load_dotenv

load_dotenv(_backend / ".env")

from core.knowledge.ike2.unknown_queue import TABLE, plan_legacy_migration


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write to ike2_unknown_queue (default: dry-run)")
    args = parser.parse_args(argv)

    from core.knowledge.ingredient_db import get_supabase_config
    from supabase import create_client

    cfg = get_supabase_config()
    if not cfg:
        raise SystemExit("Supabase not configured (need SUPABASE_URL + service role key)")
    c = create_client(cfg.url, cfg.key)

    legacy = c.table("unknown_ingredients").select("*").eq("resolved", False).execute().data or []
    existing = {r["normalized_key"]: r for r in (c.table(TABLE).select("*").execute().data or [])}
    ops = plan_legacy_migration(legacy, existing)

    if args.apply:
        for op in ops:
            if op["op"] == "insert":
                c.table(TABLE).insert(op["row"]).execute()
            elif op["op"] == "update":
                c.table(TABLE).update(op["row"]).eq("id", op["id"]).execute()

    summary = {
        "apply": args.apply,
        "legacy_unresolved": len(legacy),
        "ops": [{k: v for k, v in op.items() if k in ("op", "key", "reason")} for op in ops],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
