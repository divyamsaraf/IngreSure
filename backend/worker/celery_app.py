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
)

# Keep configuration minimal for now; tuning (acks_late, concurrency, etc.)
# can be added once tasks are in active use.

