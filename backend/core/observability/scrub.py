"""Redact ingredient text, profile/health fields, and request bodies.

Used by Sentry before_send and by any log helper in this package.
Never keep raw user text.
"""

from __future__ import annotations

from typing import Any, Iterable

REDACTED = "[REDACTED]"

# Keys whose values are ingredient text, chat text, or profile/health fields.
_SENSITIVE_KEYS = frozenset(
    {
        "query",
        "message",
        "user_input",
        "output_text",
        "ingredients",
        "ingredients_text",
        "raw_label",
        "raw_input",
        "raw_inputs",
        "ingredient",
        "atom",
        "canonical_name",
        "userprofile",
        "user_profile",
        "profile",
        "profile_update",
        "profile_context",
        "profile_context_sample",
        "dietary_preference",
        "diet_type",
        "allergens",
        "allergies",
        "lifestyle",
        "preferences",
        "restriction_ids",
        "restriction_ids_sample",
        "email",
        "name",
        "body",
        "data",
        "request_body",
        "payload",
        "text",
        "prompt",
        "content",
    }
)

_SENSITIVE_HEADER_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "x-api-key",
        "x-metrics-token",
        "x-anon-token",
    }
)


def is_sensitive_key(key: Any) -> bool:
    if key is None:
        return False
    return str(key).strip().lower() in _SENSITIVE_KEYS


def scrub_value(value: Any, *, key: Any = None) -> Any:
    """Return a copy of ``value`` with sensitive keys/bodies replaced."""
    if is_sensitive_key(key):
        return REDACTED
    if isinstance(value, dict):
        return {str(k): scrub_value(v, key=k) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub_value(v) for v in value]
    if isinstance(value, tuple):
        return tuple(scrub_value(v) for v in value)
    return value


def scrub_headers(headers: Iterable[tuple[Any, Any]] | dict[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if headers is None:
        return out
    items = headers.items() if isinstance(headers, dict) else headers
    for raw_k, raw_v in items:
        key = str(raw_k)
        if key.lower() in _SENSITIVE_HEADER_KEYS:
            out[key] = REDACTED
        else:
            out[key] = str(raw_v)
    return out


def drop_request_bodies(event: dict[str, Any]) -> dict[str, Any]:
    """Strip request bodies and breadcrumbs that may carry ingredient/profile text."""
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("body", None)
        request.pop("api_target", None)
        if "headers" in request:
            request["headers"] = scrub_headers(request.get("headers"))
        event["request"] = request

    extra = event.get("extra")
    if isinstance(extra, dict):
        event["extra"] = scrub_value(extra)

    contexts = event.get("contexts")
    if isinstance(contexts, dict):
        event["contexts"] = scrub_value(contexts)

    breadcrumbs = event.get("breadcrumbs")
    if isinstance(breadcrumbs, dict):
        values = breadcrumbs.get("values")
        if isinstance(values, list):
            breadcrumbs["values"] = [_scrub_breadcrumb(b) for b in values]
    elif isinstance(breadcrumbs, list):
        event["breadcrumbs"] = [_scrub_breadcrumb(b) for b in breadcrumbs]
    return event


def _scrub_breadcrumb(crumb: Any) -> Any:
    if not isinstance(crumb, dict):
        return crumb
    data = crumb.get("data")
    if isinstance(data, dict):
        crumb = dict(crumb)
        crumb["data"] = scrub_value(data)
    return crumb
