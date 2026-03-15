#!/usr/bin/env python3
"""
Check that data/profile_options.json and frontend/src/constants/profile_options.json
are identical (same JSON content). Use in CI or pre-commit to avoid drift.

Run from repo root:
  python backend/scripts/check_profile_options_sync.py
  python3 backend/scripts/check_profile_options_sync.py

Exit code: 0 if in sync, 1 if different or files missing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def repo_root() -> Path:
    """Assume script lives in backend/scripts/; repo root is backend's parent."""
    script_dir = Path(__file__).resolve().parent
    backend_dir = script_dir.parent
    return backend_dir.parent


def load_json(path: Path) -> dict | list | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        return None


def main() -> int:
    root = repo_root()
    backend_file = root / "data" / "profile_options.json"
    frontend_file = root / "frontend" / "src" / "constants" / "profile_options.json"

    if not backend_file.is_file():
        print(f"Missing: {backend_file}", file=sys.stderr)
        return 1
    if not frontend_file.is_file():
        print(f"Missing: {frontend_file}", file=sys.stderr)
        return 1

    backend_data = load_json(backend_file)
    frontend_data = load_json(frontend_file)
    if backend_data is None or frontend_data is None:
        return 1

    if backend_data != frontend_data:
        print(
            "profile_options.json is out of sync: data/ and frontend/src/constants/ differ.",
            file=sys.stderr,
        )
        print("Update frontend/src/constants/profile_options.json to match data/profile_options.json (or run a sync step).", file=sys.stderr)
        return 1

    print("profile_options.json in sync (data/ and frontend/src/constants/).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
