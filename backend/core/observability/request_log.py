"""Build structured request log records. No raw user text."""

from __future__ import annotations

import json
from typing import Any, Optional

_VERDICT_STATUSES = frozenset(
    {
        "safe",
        "avoid",
        "depends",
        "not_safe",
        "uncertain",
        "warn",
        "fail",
        "pass",
        "ok",
    }
)

_ENGINE_DEFAULT_BY_PREFIX = (
    ("/api/v1/", "ike2"),
    ("/chat/", "ike2"),
)


def default_engine_for_path(path: str) -> Optional[str]:
    for prefix, engine in _ENGINE_DEFAULT_BY_PREFIX:
        if path.startswith(prefix):
            return engine
    return None


def _bump(counts: dict[str, int], raw: Any) -> None:
    if not isinstance(raw, str):
        return
    key = raw.strip().lower()
    if key in _VERDICT_STATUSES:
        counts[key] = counts.get(key, 0) + 1


def extract_observability_fields(payload: Any) -> dict[str, Any]:
    """Pull engine / degraded / verdict counts from a JSON payload.

    Only status enums and boolean/layer flags are read. Ingredient names,
    audit item text, and profile fields are ignored.
    """
    counts: dict[str, int] = {}
    degraded = False
    engine: Optional[str] = None
    if not isinstance(payload, dict):
        return {"verdict_counts": counts, "degraded": degraded, "engine": engine}

    schema = payload.get("schema_version")
    if isinstance(schema, str) and schema.lower().startswith("ike2"):
        engine = "ike2"

    verdict = payload.get("verdict")
    if isinstance(verdict, dict):
        _bump(counts, verdict.get("status"))
    elif isinstance(verdict, str):
        _bump(counts, verdict)

    ike2 = payload.get("ike2")
    if isinstance(ike2, dict):
        inner_schema = ike2.get("schema_version")
        if isinstance(inner_schema, str) and inner_schema.lower().startswith("ike2"):
            engine = "ike2"
        _bump(counts, ike2.get("external_verdict"))
        if ike2.get("degraded") is True:
            degraded = True

    for flag_key in ("degraded", "is_degraded"):
        if payload.get(flag_key) is True:
            degraded = True

    layer = payload.get("resolution_layer")
    if isinstance(layer, str) and "degraded" in layer.lower():
        degraded = True
        engine = engine or "ike2"

    knowledge = payload.get("knowledge_state")
    if isinstance(knowledge, str) and knowledge.upper() in {"UNCLASSIFIED", "DEGRADED"}:
        degraded = True

    return {"verdict_counts": counts, "degraded": degraded, "engine": engine}


def merge_fields(*parts: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    degraded = False
    engine: Optional[str] = None
    for part in parts:
        for key, n in (part.get("verdict_counts") or {}).items():
            try:
                counts[str(key)] = counts.get(str(key), 0) + int(n)
            except (TypeError, ValueError):
                continue
        if part.get("degraded"):
            degraded = True
        if part.get("engine"):
            engine = str(part["engine"])
    return {"verdict_counts": counts, "degraded": degraded, "engine": engine}


def fields_from_request_state(request: Any) -> dict[str, Any]:
    state = getattr(request, "state", None)
    if state is None:
        return {"verdict_counts": {}, "degraded": False, "engine": None}
    counts = getattr(state, "verdict_counts", None) or {}
    if not isinstance(counts, dict):
        counts = {}
    return {
        "verdict_counts": {str(k): int(v) for k, v in counts.items() if _safe_int(v) is not None},
        "degraded": bool(getattr(state, "degraded", False)),
        "engine": getattr(state, "engine", None),
    }


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_log_record(
    *,
    request_id: str,
    route: str,
    method: str,
    status: int,
    latency_ms: int,
    engine: Optional[str],
    degraded: bool,
    verdict_counts: dict[str, int],
) -> dict[str, Any]:
    return {
        "event": "http_request",
        "request_id": request_id,
        "route": route,
        "method": method,
        "status": status,
        "latency_ms": latency_ms,
        "engine": engine,
        "degraded": bool(degraded),
        "verdict_counts": verdict_counts,
    }


def encode_log_record(record: dict[str, Any]) -> str:
    return json.dumps(record, separators=(",", ":"), sort_keys=True)
