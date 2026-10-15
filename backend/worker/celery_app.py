"""
Celery application for background enrichment workers.

Phase 4:
  - Define an isolated Celery app that runs in its own container/process.
  - Do NOT import this from the FastAPI app; the web API must remain
    independent of worker lifecycle.
"""

from __future__ import annotations

import os

from celery import Celery


def _default_broker_url() -> str:
    # Use REDIS_URL if set; otherwise default to a local Redis service name
    return os.environ.get("REDIS_URL", "redis://redis:6379/0")


celery_app = Celery(
    "ingresure_worker",
    broker=_default_broker_url(),
    backend=os.environ.get("CELERY_RESULT_BACKEND", _default_broker_url()),
    include=["worker.tasks"],
)

# Item 23: Beat runs embedded in the single compose worker (`worker -B`).
# Running more than one worker replica with -B would double-schedule.
celery_app.conf.beat_schedule = {
    "enrich-unknown-batch-hourly": {
        "task": "enrich_unknown_batch",
        "schedule": 3600.0,
        "kwargs": {"min_frequency": 1, "limit": 50},
    },
    # Item 12: nightly IKE-2 live audits (asserted-false, DISCOVERED, L2↔L3 drift,
    # lexicon vs verdict). Report-only; writes .local_reports/item12_*.json.
    "ike2-scheduled-audits-daily": {
        "task": "ike2_scheduled_audits",
        "schedule": 86400.0,
    },
}

