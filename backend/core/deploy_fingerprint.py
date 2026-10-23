"""Deploy identity for GET /health and post-deploy smoke checks.

Prefer env-injected ``GIT_SHA`` at deploy time; fall back to ``git rev-parse``
when the checkout is available. Schema version is the newest migration
filename stem under ``supabase/migrations/`` (shipped with the app) plus an
optional applied-migration probe against the live DB.
"""
from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path

from core import config

_REPO = Path(__file__).resolve().parents[2]
_MIGRATIONS = _REPO / "supabase" / "migrations"
_ENGINE = "ike2"


def _git_rev_parse() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPO,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return out.decode().strip() or None
    except Exception:
        return None


def git_sha() -> str:
    for key in ("GIT_SHA", "COMMIT_SHA", "SOURCE_VERSION"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    return _git_rev_parse() or "unknown"


@lru_cache(maxsize=1)
def shipped_schema_version() -> str:
    """Newest migration stem packaged with this deploy (filename order)."""
    if not _MIGRATIONS.is_dir():
        return "unknown"
    stems = sorted(p.stem for p in _MIGRATIONS.glob("*.sql"))
    return stems[-1] if stems else "unknown"


def applied_schema_version() -> str | None:
    """Latest version from ``supabase_migrations.schema_migrations`` when DB is up."""
    try:
        from core.knowledge.ingredient_db import get_supabase_client

        client = get_supabase_client()
        if client is None:
            return None
        # PostgREST may not expose schema_migrations; try RPC-free REST first.
        resp = (
            client.schema("supabase_migrations")
            .table("schema_migrations")
            .select("version")
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if rows and rows[0].get("version"):
            return str(rows[0]["version"])
    except Exception:
        return None
    return None


def fingerprint() -> dict:
    """Fields merged into GET /health."""
    applied = applied_schema_version()
    shipped = shipped_schema_version()
    return {
        "git_sha": git_sha(),
        "ike2_schema_version": applied or shipped,
        "ike2_schema_version_shipped": shipped,
        "ike2_schema_version_applied": applied,
        "engine": _ENGINE,
        "environment": os.environ.get("ENVIRONMENT", "") or "unset",
        "production": bool(config.PRODUCTION),
    }
