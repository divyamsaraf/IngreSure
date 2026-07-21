"""
CORS origin validation guard for production environments.

Extracted as a pure function so it can be unit tested without starting the
FastAPI app (app.py calls this before app.add_middleware(CORSMiddleware, ...)).
"""
from __future__ import annotations

from typing import List


def validate_cors_origins(origins: List[str], is_production: bool) -> None:
    """
    In production, CORS_ORIGINS must be explicitly set to specific, non-wildcard
    origin(s). Raises RuntimeError when is_production and origins is empty or
    contains "*". No-op when is_production is False (dev may allow-all).
    """
    if not is_production:
        return
    if not origins or "*" in origins:
        raise RuntimeError(
            "CORS_ORIGINS must be set to a specific, non-wildcard, comma-separated "
            "origin list when ENVIRONMENT=production. Refusing to start with an "
            "open or empty CORS policy in production."
        )
