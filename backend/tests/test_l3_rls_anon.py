"""Anon key must not read ike2_* tables on local Supabase (RLS, no policies)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_BACKEND, ".env"))

_IKE2_RELATIONS = (
    "ike2_ingredient_groups",
    "ike2_ingredients",
    "ike2_aliases",
    "ike2_alias_disambiguation",
    "ike2_restriction_rules",
    "ike2_resolution_cache",
    "ike2_unknown_queue",
    "ike2_shadow_diffs",
    "ike2_group_merges",
    "ike2_v_alias_resolution",
)


def _local_url() -> str:
    return (os.getenv("SUPABASE_URL") or "").strip()


def _anon_key() -> str:
    return (
        os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or ""
    ).strip()


def _has_local_anon() -> bool:
    url = _local_url()
    key = _anon_key()
    if not url or not key:
        return False
    return "127.0.0.1" in url or "localhost" in url


pytestmark = pytest.mark.skipif(
    not _has_local_anon(),
    reason="needs local supabase + SUPABASE_ANON_KEY from supabase start",
)

_REVOKE_SQL = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations_draft"
    / "20261023120000_ike2_revoke_anon.sql"
)


def _local_db_url() -> str:
    url = (
        os.getenv("SUPABASE_DB_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    ).strip()
    if "127.0.0.1" not in url and "localhost" not in url:
        pytest.skip("refuse non-local DATABASE_URL for revoke apply")
    return url


def _sql_statements(sql: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            out.append("\n".join(buf))
            buf = []
    return out


def _apply_revoke_draft_locally() -> None:
    """Apply the draft REVOKE SQL on localhost only. Never production."""
    import psycopg2

    url = _local_db_url()
    sql = _REVOKE_SQL.read_text(encoding="utf-8")
    conn = psycopg2.connect(url)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            for stmt in _sql_statements(sql):
                cur.execute(stmt)
    finally:
        conn.close()


def test_anon_key_cannot_read_ike2_tables():
    """Expected policy: RLS on, no GRANT/policies for anon → empty or error.

    Never invent keys. Uses SUPABASE_ANON_KEY / NEXT_PUBLIC_SUPABASE_ANON_KEY
    from the environment after `supabase start`.
    """
    from supabase import create_client

    url = _local_url()
    key = _anon_key()
    assert "supabase.co" not in url
    _apply_revoke_draft_locally()
    client = create_client(url, key)
    leaked = []
    for name in _IKE2_RELATIONS:
        try:
            resp = client.table(name).select("*").limit(5).execute()
            rows = getattr(resp, "data", None) or []
            if rows:
                leaked.append((name, len(rows)))
        except Exception:
            # Permission / RLS / missing GRANT is the intended deny path.
            continue
    assert leaked == [], (
        "anon key read ike2_* rows (expected RLS deny / empty): "
        f"{leaked}. See deploy/l3_local_suites.md."
    )
