#!/usr/bin/env python3
"""Apply missing IKE-2 migrations one file at a time, each in a transaction.

Default is dry-run. Never runs DROP/RENAME/ALTER TYPE/DISABLE RLS files
(expand-only lint). Tracker repair is a separate --repair-tracker step.

    DATABASE_URL=... python scripts/apply_prod_migrations.py
    DATABASE_URL=... python scripts/apply_prod_migrations.py --apply
    DATABASE_URL=... python scripts/apply_prod_migrations.py --repair-tracker
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))

from scripts.check_migration_expand_only import LAST_SHIPPED, find_forbidden

MIGRATIONS = _REPO / "supabase" / "migrations"
REPAIR_SQL = _REPO / "deploy" / "repair_schema_migrations.sql"


def _connect(url: str):
    import psycopg2

    return psycopg2.connect(url)


def _applied(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("select version from supabase_migrations.schema_migrations order by version")
        return [r[0] for r in cur.fetchall()]


def _files() -> list[Path]:
    return sorted(MIGRATIONS.glob("*.sql"))


def plan(conn) -> dict:
    applied = _applied(conn)
    files = _files()
    missing = [p for p in files if p.name.split("_", 1)[0] not in applied]
    blocked = []
    for path in missing:
        hits = find_forbidden(path.read_text(encoding="utf-8"))
        if hits and path.name.split("_", 1)[0] > LAST_SHIPPED:
            blocked.append({"file": path.name, "hits": [h.kind for h in hits]})
    return {
        "applied": applied,
        "missing": [p.name for p in missing],
        "blocked": blocked,
    }


def apply_one(conn, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    version = path.name.split("_", 1)[0]
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            cur.execute(
                """
                insert into supabase_migrations.schema_migrations (version, name)
                values (%s, %s)
                on conflict (version) do nothing
                """,
                (version, path.stem),
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--repair-tracker", action="store_true")
    args = parser.parse_args(argv)
    url = (os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL") or "").strip()
    if not url:
        print("DATABASE_URL required", file=sys.stderr)
        return 2
    conn = _connect(url)
    try:
        report = plan(conn)
        if args.repair_tracker:
            sql = REPAIR_SQL.read_text(encoding="utf-8")
            if args.apply:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(sql)
                report["repair"] = "applied"
            else:
                report["repair"] = "dry-run"
            print(json.dumps(report, indent=2))
            return 0
        if report["blocked"]:
            print(json.dumps(report, indent=2))
            print("FAIL: expand-only blocked files", file=sys.stderr)
            return 1
        if not args.apply:
            print(json.dumps({**report, "dry_run": True}, indent=2))
            return 0
        applied_now = []
        for name in report["missing"]:
            apply_one(conn, MIGRATIONS / name)
            applied_now.append(name)
        report["applied_now"] = applied_now
        print(json.dumps(report, indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
