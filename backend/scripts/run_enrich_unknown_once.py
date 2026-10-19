#!/usr/bin/env python3
"""
Run one batch of unknown-ingredient enrichment inline (no Celery/Redis required).

Executes the worker task ``enrich_unknown_batch`` synchronously: drains
``ike2_unknown_queue`` and writes results into ``ike2_*`` (Item 18).

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

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def run_batch(limit: int = 10) -> dict:
    from worker.tasks import enrich_unknown_batch

    return enrich_unknown_batch(min_frequency=1, limit=limit)


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    out = run_batch(limit=limit)
    print("Result:", out)
    sys.exit(0 if out.get("processed", 0) >= 0 else 1)
