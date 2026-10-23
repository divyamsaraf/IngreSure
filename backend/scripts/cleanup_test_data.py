#!/usr/bin/env python3
"""Remove flip-window test_* profile keys. Dry-run by default.

    python scripts/cleanup_test_data.py
    python scripts/cleanup_test_data.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

_PROFILES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "profiles.json"
TEST_PREFIX = "test_"


def _matches(key: str, prefix: str) -> bool:
    tail = key.split("user:")[-1] if key.startswith("user:") else key
    return tail.startswith(prefix) or key.startswith(f"user:{prefix}")


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2)
    fd, tmp = tempfile.mkstemp(prefix=".profiles.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def cleanup_profiles(*, dry_run: bool, prefix: str = TEST_PREFIX, path: Path | None = None) -> dict:
    target = path or _PROFILES_PATH
    if not target.exists():
        return {"would_delete": [], "deleted": [], "path": str(target), "dry_run": dry_run}
    data = json.loads(target.read_text(encoding="utf-8"))
    victims = sorted(k for k in data if _matches(k, prefix))
    if dry_run:
        return {"would_delete": victims, "deleted": [], "path": str(target), "dry_run": True}
    for key in victims:
        del data[key]
    _atomic_write(target, data)
    return {"would_delete": [], "deleted": victims, "path": str(target), "dry_run": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--prefix", default=TEST_PREFIX)
    args = parser.parse_args(argv)
    report = cleanup_profiles(dry_run=not args.apply, prefix=args.prefix)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
