#!/usr/bin/env python3
"""
Ensure backend/.env has local Supabase URL and service role key so seed/verify/enrich work.

Reads from `supabase status -o json` (run from repo root). Appends to .env only if
SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY are missing. Safe to run multiple times.

Run from repo root: python backend/scripts/setup_local_supabase_env.py
Or from backend: python scripts/setup_local_supabase_env.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent.parent
backend = Path(__file__).resolve().parent.parent
env_file = backend / ".env"


def main() -> int:
    if not env_file.exists():
        env_file.touch()
        print(f"Created {env_file}")

    try:
        out = subprocess.run(
            ["supabase", "status", "-o", "json"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if out.returncode != 0:
            print("Run from repo root with Supabase running: supabase start")
            print("  Then: python backend/scripts/setup_local_supabase_env.py")
            return 1
        data = json.loads(out.stdout)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print("Could not get supabase status:", e)
        return 1

    url = (data.get("API_URL") or "").strip()
    key = (data.get("SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        print("Missing API_URL or SERVICE_ROLE_KEY in supabase status")
        return 1

    content = env_file.read_text()
    has_url = "SUPABASE_URL=" in content
    has_key = "SUPABASE_SERVICE_ROLE_KEY=" in content

    to_append = []
    if not has_url:
        to_append.append(f"SUPABASE_URL={url}")
    if not has_key:
        to_append.append(f"SUPABASE_SERVICE_ROLE_KEY={key}")
    if "USE_KNOWLEDGE_DB=" not in content:
        to_append.append("USE_KNOWLEDGE_DB=true")

    if not to_append:
        print("backend/.env already has SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return 0

    with open(env_file, "a") as f:
        if content and not content.endswith("\n"):
            f.write("\n")
        f.write("\n# Local Supabase (from setup_local_supabase_env)\n")
        for line in to_append:
            f.write(line + "\n")
    print("Appended to backend/.env:", ", ".join(s.split("=")[0] for s in to_append))
    return 0


if __name__ == "__main__":
    sys.exit(main())
