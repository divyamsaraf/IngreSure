#!/usr/bin/env python3
"""Read-only production verification (REST plus optional SQL).

Owner runs this against the *same* Supabase project with a service-role key
already in their shell env. This script never prints secrets. Non-zero on fail.

    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python scripts/verify_prod.py
    DATABASE_URL=...  # optional direct Postgres for RLS / size / tracker
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv(_BACKEND / ".env")
load_dotenv(_REPO / ".env")

EXPECTED_RULES = 58
VIEW = "ike2_v_alias_resolution"
_VIEW_COLS = ("source", "asserted_flags", "canonical_name", "normalized_alias")


def required_view_columns() -> tuple[str, ...]:
    return _VIEW_COLS


def summarize(report: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []
    rules = report.get("rules")
    if rules != EXPECTED_RULES:
        failures.append(f"rules={rules!r} (want {EXPECTED_RULES})")
    cols = set(report.get("view_columns") or [])
    missing = [c for c in _VIEW_COLS if c not in cols]
    if missing:
        failures.append(f"view {VIEW} missing columns {missing}")
    if report.get("flags_null"):
        failures.append(f"null flags={report['flags_null']}")
    missing_objects = report.get("missing_objects") or []
    if missing_objects:
        failures.append(f"missing objects: {missing_objects}")
    return not failures, failures


def _client():
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required (not printed)")
    from supabase import create_client

    return create_client(url, key)


def _count(client, table: str, **eq) -> int | None:
    q = client.table(table).select("id", count="exact").limit(1)
    for k, v in eq.items():
        q = q.eq(k, v)
    resp = q.execute()
    return getattr(resp, "count", None)


def _rest_report(client) -> dict:
    report: dict = {
        "view": VIEW,
        "view_columns": [],
        "rules": None,
        "counts": {},
        "flags_null": None,
        "alias_language_null": None,
        "alias_region_null": None,
        "missing_objects": [],
        "applied_migrations": [],
    }
    view_rows = client.table(VIEW).select("*").limit(1).execute().data or []
    if not view_rows:
        report["missing_objects"].append(VIEW)
    else:
        report["view_columns"] = sorted(view_rows[0].keys())
    report["rules"] = _count(client, "ike2_restriction_rules")
    report["counts"] = {
        "ike2_ingredient_groups": _count(client, "ike2_ingredient_groups"),
        "ike2_aliases": _count(client, "ike2_aliases"),
        "ike2_unknown_queue_pending": _count(client, "ike2_unknown_queue", status="pending"),
        "ontology_source_groups": _count(client, "ike2_ingredient_groups", source="ontology"),
    }
    # Sample: flags must not be JSON null. PostgREST returns the array.
    sample = (
        client.table("ike2_ingredient_groups")
        .select("canonical_name,asserted_flags,animal_origin")
        .limit(20)
        .execute()
        .data
        or []
    )
    report["flags_null"] = sum(1 for r in sample if r.get("asserted_flags") is None)
    return report


def _sql_extras() -> dict:
    url = (os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL") or "").strip()
    extra = {"sql": False}
    if not url:
        extra["sql_skipped"] = "no DATABASE_URL"
        return extra
    try:
        import psycopg2
    except ImportError:
        extra["sql_skipped"] = "psycopg2 not installed"
        return extra
    conn = psycopg2.connect(url)
    conn.set_session(readonly=True, autocommit=True)
    extra["sql"] = True
    with conn.cursor() as cur:
        cur.execute(
            """
            select version
            from supabase_migrations.schema_migrations
            order by version
            """
        )
        extra["applied_migrations"] = [r[0] for r in cur.fetchall()]
        cur.execute(
            """
            select relname, relrowsecurity
            from pg_class
            where relname like 'ike2_%%' and relkind = 'r'
            order by 1
            """
        )
        extra["rls"] = {name: bool(on) for name, on in cur.fetchall()}
        cur.execute("select pg_database_size(current_database())")
        extra["db_size_bytes"] = cur.fetchone()[0]
        cur.execute(
            """
            select
              count(*) filter (where language is null),
              count(*) filter (where region is null),
              count(*)
            from public.ike2_aliases
            """
        )
        lang_null, region_null, total = cur.fetchone()
        extra["alias_language_null"] = lang_null
        extra["alias_region_null"] = region_null
        extra["alias_total"] = total
        files = sorted(
            p.name.split("_", 1)[0]
            for p in (_REPO / "supabase" / "migrations").glob("*.sql")
        )
        extra["missing_tracker"] = [v for v in files if v not in extra["applied_migrations"]]
    conn.close()
    return extra


def main() -> int:
    client = _client()
    report = _rest_report(client)
    report.update(_sql_extras())
    ok, failures = summarize(report)
    if report.get("missing_tracker"):
        failures.append(f"tracker missing {report['missing_tracker']}")
        ok = False
    print(json.dumps(report, indent=2, default=str))
    if not ok:
        print("FAIL:", *failures, sep="\n  ")
        return 1
    print("OK: verify_prod")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
