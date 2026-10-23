#!/usr/bin/env python3
"""Fail CI if a *new* migration drops, renames, changes types, or disables RLS.

Historical files (through 20261014000000) are allowlisted. Anything later must
be expand-only so the old container keeps working during same-project blue/green.
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

LAST_SHIPPED = "20261014000000"

_PATTERNS = (
    ("DROP", re.compile(r"\bDROP\s+(TABLE|COLUMN|VIEW|INDEX|TYPE)\b", re.I)),
    ("RENAME", re.compile(r"\bRENAME\s+(COLUMN|TO)\b", re.I)),
    ("ALTER TYPE", re.compile(r"\bALTER\s+COLUMN\b[^;]*\bTYPE\b", re.I)),
    ("DISABLE RLS", re.compile(r"\bDISABLE\s+ROW\s+LEVEL\s+SECURITY\b", re.I)),
)


@dataclass(frozen=True)
class Hit:
    kind: str
    match: str


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    lines = []
    for line in sql.splitlines():
        if "--" in line:
            line = line[: line.index("--")]
        lines.append(line)
    return "\n".join(lines)


def find_forbidden(sql: str) -> list[Hit]:
    body = _strip_sql_comments(sql)
    hits: list[Hit] = []
    for kind, pat in _PATTERNS:
        for m in pat.finditer(body):
            hits.append(Hit(kind=kind, match=m.group(0)))
    return hits


def _version_of(path: Path) -> str:
    return path.name.split("_", 1)[0]


def lint_new_migrations(migrations_dir: Path, *, after: str = LAST_SHIPPED) -> list[str]:
    problems: list[str] = []
    if not migrations_dir.is_dir():
        return [f"missing migrations dir: {migrations_dir}"]
    for path in sorted(migrations_dir.glob("*.sql")):
        if _version_of(path) <= after:
            continue
        hits = find_forbidden(path.read_text(encoding="utf-8"))
        for hit in hits:
            problems.append(f"{path.name}: {hit.kind} ({hit.match})")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--migrations",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "supabase" / "migrations",
    )
    parser.add_argument("--after", default=LAST_SHIPPED)
    args = parser.parse_args(argv)
    problems = lint_new_migrations(args.migrations, after=args.after)
    if problems:
        print("FAIL expand-only:", *problems, sep="\n  ")
        return 1
    print(f"OK: no DROP/RENAME/ALTER TYPE/DISABLE RLS after {args.after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
