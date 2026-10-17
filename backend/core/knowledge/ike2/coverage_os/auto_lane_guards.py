"""Auto-lane sample audit and volume-spike guards (Coverage OS Phase 1).

Phase 1 is log/stub only — no daemon. Callers may invoke
``select_sample_audit`` / ``log_volume_spike_if_needed`` after a batch of
``append_promoted(..., auto=True)`` rows (in-memory list is fine).
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

log = logging.getLogger(__name__)


def select_sample_audit(
    promotions: list[dict[str, Any]],
    *,
    every_n: int = 10,
) -> list[dict[str, Any]]:
    """Return every Nth auto promotion (1-indexed among auto rows)."""
    if every_n < 1:
        raise ValueError("every_n must be >= 1")
    autos = [p for p in promotions if p.get("auto")]
    return [p for i, p in enumerate(autos) if (i + 1) % every_n == 0]


def check_volume_spike(
    promotions: list[dict[str, Any]],
    *,
    window_seconds: int,
    threshold: int,
    now: Optional[float] = None,
) -> bool:
    """True if count of promotions with ts in [now - window, now] exceeds threshold."""
    if now is None:
        now = time.time()
    lo = now - window_seconds
    count = 0
    for p in promotions:
        ts = p.get("ts")
        if ts is None:
            continue
        try:
            t = float(ts)
        except (TypeError, ValueError):
            continue
        if lo <= t <= now:
            count += 1
    return count > threshold


def log_volume_spike_if_needed(
    promotions: list[dict[str, Any]],
    *,
    window_seconds: int,
    threshold: int,
    now: Optional[float] = None,
) -> bool:
    spiked = check_volume_spike(
        promotions,
        window_seconds=window_seconds,
        threshold=threshold,
        now=now,
    )
    if spiked:
        log.warning(
            "coverage_os auto-lane volume spike: count in last %ss exceeds %s",
            window_seconds,
            threshold,
        )
    return spiked
