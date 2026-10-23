#!/usr/bin/env python3
"""Restore a custom-format pg_dump into a throwaway local Postgres container.

NEVER uses production credentials or a remote DSN. The drill always
``docker run``s ``pgvector/pgvector:pg17`` on 127.0.0.1, restores, compares
row counts, then tears the container down. The dump file is never deleted.

Usage (from repo root):
  python scripts/restore_dump_drill.py \\
    --counts /path/to/counts.json \\
    --checksum-file /path/to/dump.sha256
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_DUMP = (
    Path.home()
    / "Documents"
    / "IngreSure-backups"
    / "gcufjqokqqmcuuayaybu-full-role-postgres-20261022T2354Z.dump"
)
DOCKER_IMAGE = "pgvector/pgvector:pg17"
_SCHEMAS = ("public", "ike2_staging")
_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class ChecksumMismatch(ValueError):
    pass


class RemoteHostForbidden(ValueError):
    pass


def assert_local_only(host: str) -> None:
    h = (host or "").strip().lower()
    if h not in _LOCAL_HOSTS:
        raise RemoteHostForbidden(
            f"refusing non-local host {host!r}; drill is local-Postgres only"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(dump: Path, expected: str) -> None:
    actual = sha256_file(dump)
    exp = (expected or "").strip().split()[0].lower()
    if actual.lower() != exp:
        raise ChecksumMismatch(f"{dump}: sha256 {actual} != {exp}")


def compare_row_counts(actual: dict, expected: dict) -> list[str]:
    mismatches = []
    for key in sorted(set(actual) | set(expected)):
        got = actual.get(key)
        want = expected.get(key)
        if got != want:
            mismatches.append(f"{key}: actual={got} expected={want}")
    return mismatches


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_postgres(name: str, timeout_s: float = 45.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        proc = subprocess.run(
            ["docker", "exec", name, "pg_isready", "-U", "postgres"],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return
        time.sleep(0.5)
    raise RuntimeError(f"postgres in {name} did not become ready")


def _pg_restore(dump: Path, name: str) -> None:
    subprocess.run(
        ["docker", "cp", str(dump), f"{name}:/tmp/restore.dump"],
        check=True,
        capture_output=True,
        text=True,
    )
    proc = subprocess.run(
        [
            "docker",
            "exec",
            name,
            "pg_restore",
            "-U",
            "postgres",
            "-d",
            "postgres",
            "-F",
            "c",
            "--no-owner",
            "--no-acl",
            "/tmp/restore.dump",
        ],
        capture_output=True,
        text=True,
    )
    # pg_restore can warn on extension ownership while still loading tables.
    if proc.returncode != 0 and "ERROR" in (proc.stderr or "").upper():
        raise RuntimeError(proc.stderr or proc.stdout or "pg_restore failed")


def _count_tables(name: str) -> dict[str, int]:
    sql = (
        "SELECT n.nspname || '.' || c.relname "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname IN ('public', 'ike2_staging') AND c.relkind = 'r' "
        "ORDER BY 1;"
    )
    listed = subprocess.run(
        ["docker", "exec", name, "psql", "-U", "postgres", "-d", "postgres", "-At", "-c", sql],
        capture_output=True,
        text=True,
        check=True,
    )
    counts: dict[str, int] = {}
    for line in listed.stdout.splitlines():
        qual = line.strip()
        if not qual or "." not in qual:
            continue
        schema, table = qual.split(".", 1)
        if schema not in _SCHEMAS:
            continue
        count_sql = f'SELECT count(*) FROM "{schema}"."{table}";'
        row = subprocess.run(
            [
                "docker",
                "exec",
                name,
                "psql",
                "-U",
                "postgres",
                "-d",
                "postgres",
                "-At",
                "-c",
                count_sql,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        counts[qual] = int((row.stdout or "0").strip() or "0")
    return counts


def run_isolated_restore(dump: Path) -> dict[str, int]:
    """Bring up throwaway pg17+pgvector, restore, count, tear down."""
    assert_local_only("127.0.0.1")
    name = f"ingresure-restore-drill-{os.getpid()}"
    port = _free_port()
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "-e",
                "POSTGRES_HOST_AUTH_METHOD=trust",
                "-e",
                "POSTGRES_PASSWORD=drill",
                "-p",
                f"127.0.0.1:{port}:5432",
                DOCKER_IMAGE,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        _wait_for_postgres(name)
        _pg_restore(dump, name)
        return _count_tables(name)
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, text=True)


def _expected_checksum(dump: Path, checksum: str | None, checksum_file: Path | None) -> str:
    if checksum:
        return checksum
    path = checksum_file or Path(str(dump) + ".sha256")
    if not path.is_file():
        raise ChecksumMismatch(f"no expected sha256 (pass --checksum or {path})")
    return path.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", default=str(DEFAULT_DUMP), help="custom-format pg_dump (-F c)")
    parser.add_argument("--counts", required=True, help="JSON object of schema.table -> row count")
    parser.add_argument("--checksum", default=None, help="expected sha256 hex")
    parser.add_argument("--checksum-file", default=None, help="file containing expected sha256")
    args = parser.parse_args(argv)

    dump = Path(args.dump).expanduser()
    if not dump.is_file():
        print(f"dump not found: {dump}", file=sys.stderr)
        return 2
    try:
        expected = _expected_checksum(
            dump,
            args.checksum,
            Path(args.checksum_file) if args.checksum_file else None,
        )
        verify_checksum(dump, expected)
        expected_counts = json.loads(Path(args.counts).read_text(encoding="utf-8"))
        if not isinstance(expected_counts, dict):
            print("counts JSON must be an object", file=sys.stderr)
            return 2
        actual = run_isolated_restore(dump)
        mismatches = compare_row_counts(actual, expected_counts)
        if mismatches:
            print("row-count mismatch:", file=sys.stderr)
            for line in mismatches:
                print(f"  {line}", file=sys.stderr)
            return 1
    except ChecksumMismatch as exc:
        print(f"checksum mismatch: {exc}", file=sys.stderr)
        return 1
    except RemoteHostForbidden as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"restore drill failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "dump": str(dump), "tables": len(actual)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
