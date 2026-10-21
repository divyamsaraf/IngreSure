"""Auth for the /metrics router. Dedicated token; not a user session."""

from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request


def metrics_token() -> str:
    return (os.environ.get("METRICS_TOKEN") or "").strip()


def _extract_presented(request: Request) -> str:
    header = (request.headers.get("x-metrics-token") or "").strip()
    if header:
        return header
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def require_metrics_token(request: Request) -> None:
    """401 when the token mismatches; 404 when metrics are not configured."""
    expected = metrics_token()
    if not expected:
        raise HTTPException(status_code=404, detail="Not found")
    presented = _extract_presented(request)
    if not presented or not hmac.compare_digest(presented, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")
