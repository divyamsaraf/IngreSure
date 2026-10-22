"""Process-wide degraded-mode counter for swallowed engine exceptions."""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_COUNT = 0


def record(reason: str, *, where: str) -> None:
    global _COUNT
    with _LOCK:
        _COUNT += 1
        n = _COUNT
    logger.exception("DEGRADED where=%s count=%s reason=%s", where, n, reason)


def snapshot() -> dict:
    with _LOCK:
        return {"count": _COUNT}
