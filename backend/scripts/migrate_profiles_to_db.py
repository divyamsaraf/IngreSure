#!/usr/bin/env python3
"""Migrate UUID profiles from data/profiles.json into public.users (USE_PROFILE_DB)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))

try:
    from dotenv import load_dotenv

    load_dotenv(_backend / ".env")
except ImportError:
    pass

os.environ.setdefault("USE_PROFILE_DB", "1")


def main() -> int:
    from core.profile_storage import migrate_profiles_json_to_db, use_profile_db

    if not use_profile_db():
        print("error: set USE_PROFILE_DB=1", file=sys.stderr)
        return 2
    summary = migrate_profiles_json_to_db()
    print(json.dumps(summary, indent=2))
    return 0 if not summary.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
