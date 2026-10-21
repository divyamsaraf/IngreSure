"""Helpers for routes to attach observability fields to request.state.

Call from evaluate/chat handlers (see docs/observability/app_hooks.md).
Do not pass ingredient text or profile fields.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


def bind_request_observability(
    request: Any,
    *,
    engine: Optional[str] = None,
    degraded: Optional[bool] = None,
    verdict_counts: Optional[Mapping[str, int]] = None,
) -> None:
    """Write structured fields onto ``request.state``. Missing state is a no-op."""
    state = getattr(request, "state", None)
    if state is None:
        return
    if engine is not None:
        state.engine = str(engine)
    if degraded is not None:
        state.degraded = bool(degraded)
    if verdict_counts is not None:
        clean: dict[str, int] = {}
        for key, value in verdict_counts.items():
            try:
                clean[str(key).lower()] = int(value)
            except (TypeError, ValueError):
                continue
        state.verdict_counts = clean
