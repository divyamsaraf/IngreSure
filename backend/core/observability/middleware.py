"""Structured request-log middleware. No raw user text.

Emits one JSON log line per request: request_id, route, status, latency_ms,
engine, degraded, verdict_counts. Records in-process metrics.

Mount with ``app.add_middleware(StructuredRequestLogMiddleware)`` after CORS
(see docs/observability/app_hooks.md). Does not compute verdicts.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from core.observability.metrics import record_request
from core.observability.request_log import (
    build_log_record,
    default_engine_for_path,
    encode_log_record,
    extract_observability_fields,
    fields_from_request_state,
    merge_fields,
)

logger = logging.getLogger("ingresure.request")

_SKIP_PATHS = frozenset({"/metrics", "/favicon.ico"})


def _request_id(request: Request) -> str:
    incoming = (request.headers.get("x-request-id") or "").strip()
    if incoming and len(incoming) <= 128:
        return incoming
    return str(uuid.uuid4())


def _decode_json_body(response: Response) -> Optional[Any]:
    if not isinstance(response, JSONResponse):
        return None
    body = getattr(response, "body", None)
    if not body:
        return None
    try:
        return json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


class StructuredRequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = _request_id(request)
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            latency_ms = int((time.perf_counter() - started) * 1000)
            _emit(
                request,
                request_id=request_id,
                status=500,
                latency_ms=latency_ms,
                response_payload=None,
            )
            raise

        latency_ms = int((time.perf_counter() - started) * 1000)
        payload = _decode_json_body(response)
        _emit(
            request,
            request_id=request_id,
            status=response.status_code,
            latency_ms=latency_ms,
            response_payload=payload,
        )
        response.headers["X-Request-ID"] = request_id
        return response


def _emit(
    request: Request,
    *,
    request_id: str,
    status: int,
    latency_ms: int,
    response_payload: Optional[Any],
) -> None:
    route = request.url.path
    if route in _SKIP_PATHS:
        return
    state_fields = fields_from_request_state(request)
    body_fields = extract_observability_fields(response_payload) if response_payload is not None else {}
    merged = merge_fields(state_fields, body_fields)
    engine = merged.get("engine") or default_engine_for_path(route)
    degraded = bool(merged.get("degraded"))
    verdict_counts = merged.get("verdict_counts") or {}
    record = build_log_record(
        request_id=request_id,
        route=route,
        method=request.method,
        status=status,
        latency_ms=latency_ms,
        engine=engine,
        degraded=degraded,
        verdict_counts=verdict_counts,
    )
    logger.info(encode_log_record(record))
    record_request(route=route, status=status, latency_ms=latency_ms, degraded=degraded)
