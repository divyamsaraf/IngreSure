"""
Append-only request history to Supabase (public.request_history).

No-op when Supabase URL / service key are unset so local/dev without DB keeps working.
Uses SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY (not the anon key) so RLS-protected inserts succeed.

Toggle with REQUEST_HISTORY_ENABLED (default on). Set to 0/false/no/off to disable all writes.

Inserts never raise to callers; failures are logged only.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from supabase import create_client

from core.config import get_supabase_url

logger = logging.getLogger(__name__)

# Max characters stored for assistant-visible stream text (excludes stripped tag payloads).
_DEFAULT_OUTPUT_CAP = 8000
_output_cap_logged = False


def _output_max_chars() -> int:
    global _output_cap_logged
    raw = os.environ.get("REQUEST_HISTORY_OUTPUT_MAX_CHARS", "").strip()
    if not raw:
        return _DEFAULT_OUTPUT_CAP
    try:
        n = int(raw)
        return max(256, min(n, 500_000))
    except ValueError:
        if not _output_cap_logged:
            _output_cap_logged = True
            logger.warning(
                "REQUEST_HISTORY_OUTPUT_MAX_CHARS invalid; using default %s",
                _DEFAULT_OUTPUT_CAP,
            )
        return _DEFAULT_OUTPUT_CAP


_client = None
_client_init_failed = False
_missing_table_logged = False


def request_history_writes_enabled() -> bool:
    """
    When False, record_request_history is a no-op (no Supabase client created for history).

    REQUEST_HISTORY_ENABLED:
      - unset: enabled (writes when URL + service key exist)
      - 1, true, yes, on: enabled
      - 0, false, no, off: disabled
    """
    raw = os.environ.get("REQUEST_HISTORY_ENABLED", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    return True


def _service_supabase_client():
    """
    Client for server-side writes. Requires service role (or key that bypasses RLS).
    """
    global _client, _client_init_failed
    if not request_history_writes_enabled():
        return None
    if _client_init_failed:
        return None
    if _client is not None:
        return _client
    url = get_supabase_url().strip()
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.environ.get("SUPABASE_KEY", "").strip()
    )
    if not url or not key:
        return None
    try:
        _client = create_client(url, key)
        return _client
    except Exception as e:
        _client_init_failed = True
        logger.warning("request_history: Supabase client unavailable: %s", e)
        return None


def _json_ready(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.astimezone(timezone.utc).isoformat()
    if isinstance(val, Enum):
        return val.value
    if isinstance(val, dict):
        return {str(k): _json_ready(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_json_ready(v) for v in val]
    if isinstance(val, (str, int, float, bool)):
        return val
    try:
        json.dumps(val)
        return val
    except TypeError:
        return str(val)


def _format_audit_payload_for_history(data: dict) -> str:
    """
    Turn INGREDIENT_AUDIT JSON (summary / groups / explanation) into plain text for analytics.
    Matches what users see from cards + verdict prose (explanation).
    """
    parts: list[str] = []
    summary = (data.get("summary") or "").strip()
    if summary:
        parts.append(summary)

    status_title = {"avoid": "Avoid", "safe": "Safe", "depends": "Depends"}
    groups = data.get("groups") or []
    if isinstance(groups, list):
        for g in groups:
            if not isinstance(g, dict):
                continue
            st = (g.get("status") or "").strip().lower()
            label = status_title.get(st, st[:1].upper() + st[1:] if st else "Group")
            items = g.get("items") or []
            if not isinstance(items, list):
                continue
            parts.append(f"{label} ({len(items)})")
            for it in items:
                if isinstance(it, dict):
                    name = (it.get("name") or "").strip()
                    if name:
                        parts.append(name)

    expl = data.get("explanation")
    if isinstance(expl, str) and expl.strip():
        parts.append(expl.strip())

    return "\n\n".join(parts)


def strip_stream_tags_for_history(text: str) -> str:
    """
    Build human-readable text from the raw streamed body for request_history.output_text.

    - INGREDIENT_AUDIT blocks: JSON is parsed; summary, group lines, and explanation are kept.
    - PROFILE_UPDATE blocks: removed (profile JSON only; narrative lives in audit explanation).
    - Plain chunks (e.g. \"Checking ingredients…\") are kept.
    """
    from core.stream_tags import INGREDIENT_AUDIT_TAG, PROFILE_UPDATE_TAG

    if not text:
        return ""
    s = text

    while True:
        start = s.find(INGREDIENT_AUDIT_TAG)
        if start < 0:
            break
        mid = start + len(INGREDIENT_AUDIT_TAG)
        end = s.find(INGREDIENT_AUDIT_TAG, mid)
        if end < 0:
            s = s[:start]
            break
        inner = s[mid:end].strip()
        replacement = ""
        if inner:
            try:
                payload = json.loads(inner)
                if isinstance(payload, dict):
                    replacement = _format_audit_payload_for_history(payload)
            except json.JSONDecodeError:
                pass
        insert = f"\n\n{replacement}\n\n" if replacement else "\n\n"
        s = s[:start] + insert + s[end + len(INGREDIENT_AUDIT_TAG) :]

    while True:
        start = s.find(PROFILE_UPDATE_TAG)
        if start < 0:
            break
        mid = start + len(PROFILE_UPDATE_TAG)
        end = s.find(PROFILE_UPDATE_TAG, mid)
        if end < 0:
            s = s[:start]
            break
        s = s[:start] + s[end + len(PROFILE_UPDATE_TAG) :]

    return s.strip()


def truncate_output(text: str) -> str:
    cap = _output_max_chars()
    if not text or len(text) <= cap:
        return text
    return text[:cap] + "\n…[truncated]"


def record_request_history(
    *,
    started_at: datetime,
    completed_at: Optional[datetime],
    user_id: Optional[str],
    route: str,
    status: int,
    error_code: Optional[str] = None,
    user_input: Optional[str] = None,
    output_text: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    profile_update: Optional[dict[str, Any]] = None,
) -> None:
    """
    Best-effort insert. Swallows all errors.
    """
    global _missing_table_logged
    if not request_history_writes_enabled():
        return
    client = _service_supabase_client()
    if not client:
        return
    try:
        if completed_at is None:
            completed_at = datetime.now(timezone.utc)
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        delta_ms = int((completed_at - started_at).total_seconds() * 1000)
        if delta_ms < 0:
            delta_ms = 0
        row = {
            "started_at": started_at.astimezone(timezone.utc).isoformat(),
            "completed_at": completed_at.astimezone(timezone.utc).isoformat(),
            "duration_ms": delta_ms,
            "user_id": user_id,
            "route": route,
            "status": status,
            "error_code": error_code,
            "user_input": user_input,
            "output_text": output_text,
            "metadata": _json_ready(metadata),
            "profile_update": _json_ready(profile_update),
        }
        client.table("request_history").insert(row).execute()
    except Exception as e:
        msg = str(e)
        # Hosted Supabase returns PGRST205 when the table was never migrated.
        missing_table = "PGRST205" in msg or (
            "request_history" in msg and "schema cache" in msg
        )
        if missing_table:
            if not _missing_table_logged:
                _missing_table_logged = True
                logger.warning(
                    "request_history: table public.request_history is missing on Supabase. "
                    "Apply supabase/migrations/20260409120000_request_history.sql "
                    "(Supabase Dashboard → SQL Editor, or `supabase link` + `supabase db push`). "
                    "Or set REQUEST_HISTORY_ENABLED=false to silence inserts until then."
                )
            else:
                logger.debug("request_history insert skipped (table missing)")
        else:
            logger.warning("request_history insert failed (non-fatal): %s", e)
