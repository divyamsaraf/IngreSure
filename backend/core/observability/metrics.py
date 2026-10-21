"""In-process request counters for GET /metrics.

Tracks degraded and 5xx counts, latency samples for p95, and request totals.
Process-local: resets on restart. Not a substitute for a metrics backend.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from typing import Any, Optional

_LOCK = threading.Lock()
_LATENCY_CAP = 2048

_started_at = time.time()
_requests_total = 0
_degraded_total = 0
_status_5xx_total = 0
_status_4xx_total = 0
_latencies_ms: deque[int] = deque(maxlen=_LATENCY_CAP)
_by_route: dict[str, dict[str, int]] = {}


def reset_for_tests() -> None:
    global _started_at, _requests_total, _degraded_total, _status_5xx_total, _status_4xx_total
    with _LOCK:
        _started_at = time.time()
        _requests_total = 0
        _degraded_total = 0
        _status_5xx_total = 0
        _status_4xx_total = 0
        _latencies_ms.clear()
        _by_route.clear()


def record_request(
    *,
    route: str,
    status: int,
    latency_ms: int,
    degraded: bool = False,
) -> None:
    global _requests_total, _degraded_total, _status_5xx_total, _status_4xx_total
    path = route or "unknown"
    with _LOCK:
        _requests_total += 1
        if degraded:
            _degraded_total += 1
        if 500 <= status <= 599:
            _status_5xx_total += 1
        elif 400 <= status <= 499:
            _status_4xx_total += 1
        _latencies_ms.append(max(0, int(latency_ms)))
        bucket = _by_route.setdefault(path, {"requests": 0, "degraded": 0, "status_5xx": 0})
        bucket["requests"] += 1
        if degraded:
            bucket["degraded"] += 1
        if 500 <= status <= 599:
            bucket["status_5xx"] += 1


def _percentile(samples: list[int], q: float) -> Optional[int]:
    if not samples:
        return None
    ordered = sorted(samples)
    if len(ordered) == 1:
        return ordered[0]
    idx = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return ordered[idx]


def snapshot() -> dict[str, Any]:
    with _LOCK:
        samples = list(_latencies_ms)
        total = _requests_total
        degraded = _degraded_total
        five = _status_5xx_total
        four = _status_4xx_total
        by_route = {k: dict(v) for k, v in _by_route.items()}
        started = _started_at
    return {
        "requests_total": total,
        "degraded_total": degraded,
        "status_5xx_total": five,
        "status_4xx_total": four,
        "degraded_rate": (degraded / total) if total else 0.0,
        "status_5xx_rate": (five / total) if total else 0.0,
        "latency_ms": {
            "p50": _percentile(samples, 0.50),
            "p95": _percentile(samples, 0.95),
            "p99": _percentile(samples, 0.99),
            "samples": len(samples),
        },
        "by_route": by_route,
        "uptime_seconds": int(time.time() - started),
    }
