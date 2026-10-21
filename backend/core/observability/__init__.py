"""Import-safe observability: Sentry, structured request logs, metrics.

Nothing in this package starts network I/O or requires optional deps on import.
Call ``init_sentry()`` and mount the middleware / router from app startup
(see docs/observability/app_hooks.md). This package does not compute verdicts.
"""

from core.observability.git_sha import git_sha
from core.observability.metrics import snapshot as metrics_snapshot
from core.observability.miss_class_store import record_miss_class, snapshot_miss_classes
from core.observability.request_context import bind_request_observability
from core.observability.sentry import init_sentry

__all__ = [
    "bind_request_observability",
    "git_sha",
    "init_sentry",
    "metrics_snapshot",
    "record_miss_class",
    "snapshot_miss_classes",
]
