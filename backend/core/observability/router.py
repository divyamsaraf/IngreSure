"""Auth-protected /metrics. Mount via app.include_router(router)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.observability.auth import require_metrics_token
from core.observability.git_sha import git_sha
from core.observability.metrics import snapshot as request_snapshot
from core.observability.miss_class_store import snapshot_miss_classes
from core.observability.unknown_queue_metrics import unknown_queue_snapshot

router = APIRouter(tags=["observability"])


@router.get("/metrics")
def get_metrics(request: Request, _: None = Depends(require_metrics_token)) -> dict:
    _ = request
    return {
        "release": git_sha(),
        "requests": request_snapshot(),
        "miss_class": snapshot_miss_classes(),
        "unknown_queue": unknown_queue_snapshot(),
        "alerts": {
            "degraded_rate_warn_above": 0.01,
            "status_5xx_rate_warn_above": 0.005,
        },
    }
