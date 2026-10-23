"""Sentry init for the FastAPI backend. Safe to import without sentry-sdk.

``init_sentry()`` is a no-op when SENTRY_DSN is unset or sentry_sdk is missing.
``send_default_pii`` is always False. Request bodies and profile/ingredient
fields are stripped in before_send. release = git SHA.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from core.observability.git_sha import git_sha
from core.observability.scrub import drop_request_bodies, scrub_value

logger = logging.getLogger(__name__)

_initialized = False


def _before_send(event: dict[str, Any], _hint: dict[str, Any] | None = None) -> dict[str, Any]:
    event = drop_request_bodies(event)
    if "extra" in event:
        event["extra"] = scrub_value(event.get("extra"))
    if "tags" in event and isinstance(event["tags"], dict):
        event["tags"] = scrub_value(event["tags"])
    user = event.get("user")
    if isinstance(user, dict):
        # Keep an opaque id only if present; drop email/ip/username.
        uid = user.get("id")
        event["user"] = {"id": uid} if uid else {}
    return event


def _before_send_transaction(event: dict[str, Any], _hint: dict[str, Any] | None = None) -> dict[str, Any]:
    return drop_request_bodies(event)


def init_sentry() -> bool:
    """Initialize Sentry if configured. Never raises. Safe to call more than once."""
    global _initialized
    if _initialized:
        return True
    dsn = (os.environ.get("SENTRY_DSN") or "").strip()
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
    except ImportError:
        logger.info("Sentry DSN set but sentry-sdk is not installed; skipping init")
        return False
    try:
        sentry_sdk.init(
            dsn=dsn,
            release=git_sha(),
            send_default_pii=False,
            before_send=_before_send,
            before_send_transaction=_before_send_transaction,
            integrations=[
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
        )
        _initialized = True
        logger.info("Sentry initialized release=%s pii=false", git_sha(short=True))
        return True
    except Exception as exc:
        logger.warning("Sentry init failed (non-fatal): %s", exc)
        return False


def reset_for_tests() -> None:
    """Test helper: allow init_sentry to run again."""
    global _initialized
    _initialized = False
