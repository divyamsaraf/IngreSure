#!/usr/bin/env python3
"""
Trigger the Celery task enrich_unknown_batch (requires Redis and worker).

If REDIS_URL is set, sends the task and prints the result when using result.get().
Otherwise runs the same logic inline via run_enrich_unknown_once (no worker needed).

Usage:
  # With Redis + worker running (e.g. docker-compose up -d redis; docker-compose run --rm worker):
  REDIS_URL=redis://localhost:6379/0 python scripts/trigger_enrich_batch.py [limit]

  # Without Redis (runs one batch inline):
  python scripts/trigger_enrich_batch.py [limit]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
os.chdir(_backend)

from dotenv import load_dotenv
load_dotenv(_backend / ".env")
load_dotenv(_backend.parent / ".env")


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    redis_url = os.environ.get("REDIS_URL", "").strip()

    if redis_url and "redis" in redis_url:
        try:
            from worker.celery_app import celery_app
            from worker.tasks import enrich_unknown_batch
            result = enrich_unknown_batch.apply_async(kwargs={"limit": limit})
            out = result.get(timeout=120)
            print("Celery result:", out)
            return 0
        except Exception as e:
            print("Celery task failed (is the worker running?):", e)
            print("Fallback: run without Redis: python scripts/run_enrich_unknown_once.py", limit)
            return 1
    else:
        import subprocess
        print("REDIS_URL not set; running one batch inline (no worker).", flush=True)
        r = subprocess.run(
            [sys.executable, str(_backend / "scripts" / "run_enrich_unknown_once.py"), str(limit)],
            cwd=str(_backend),
            env=os.environ.copy(),
        )
        return r.returncode


if __name__ == "__main__":
    sys.exit(main())
