#!/usr/bin/env python3
"""
Verify Supabase connectivity (knowledge DB, unknown_ingredients).
Run from repo root: python backend/scripts/verify_supabase.py
Or from backend:  python scripts/verify_supabase.py

Prints OK or FAIL and how to fix. Loads backend/.env via dotenv if present.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add backend to path
_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))

# Load .env before importing config
try:
    from dotenv import load_dotenv
    load_dotenv(_backend / ".env")
    load_dotenv(_backend.parent / ".env")
except ImportError:
    pass


def main() -> int:
    from core.config import get_supabase_url

    url = get_supabase_url()
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or ""
    ).strip()

    print("Supabase verification")
    print("  SUPABASE_URL (effective):", url or "(not set)")
    print("  SUPABASE_SERVICE_ROLE_KEY:", "set" if key else "not set")

    if not url or not key:
        print("\n  FAIL: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env")
        print("  Local: run 'supabase start' then 'python backend/scripts/setup_local_supabase_env.py'")
        print("  Docker: use same .env; backend gets RUNNING_IN_DOCKER=1 so URL is rewritten to host.docker.internal")
        return 1

    try:
        from supabase import create_client
        client = create_client(url, key)
        # First request may trigger connection; errors can appear here (e.g. in Docker)
        try:
            client.table("ingredient_groups").select("id").limit(1).execute()
        except Exception as e:
            err = str(e)
            if "relation" in err.lower() or "does not exist" in err.lower():
                print("\n  OK: Connected to Supabase; ingredient_groups missing (run: supabase db reset)")
                return 0
            if "Name or service not known" in err or "Errno -2" in err or "getaddrinfo" in err:
                _print_docker_fix()
                return 1
            raise
        print("\n  OK: Supabase reachable; ingredient_groups table exists.")

        # List public tables and RLS status if the helper exists (after 20260306000000_enable_rls)
        try:
            rpc = client.rpc("get_public_tables_rls").execute()
            if getattr(rpc, "data", None):
                print("\n  Tables and RLS:")
                for row in rpc.data:
                    name = row.get("tablename") or ""
                    rls = row.get("rls_enabled")
                    status = "RLS ON" if rls else "RLS OFF (unrestricted)"
                    print(f"    {name}: {status}")
        except Exception:
            pass  # RPC may not exist before migration

        print("\n  Table usage (required vs optional):")
        print("    Required for knowledge base: ingredient_groups, ingredients, ingredient_aliases, unknown_ingredients")
        print("    Optional: enrichment_metrics (analytics only; can drop if not used)")
        print("    Optional: users (auth/demo). Menu/restaurant tables removed in 20260306100000.")
        print("  To fix 'RLS disabled': run  supabase db reset  or  supabase db push  (applies 20260306000000_enable_rls).")
        return 0
    except OSError as e:
        err = str(e)
        print("\n  FAIL: Cannot reach Supabase (network/DNS):", err[:120])
        if "Name or service not known" in err or "Errno -2" in err:
            _print_docker_fix()
        return 1
    except Exception as e:
        err = str(e)
        if "Name or service not known" in err or "Errno -2" in err or "getaddrinfo" in err:
            print("\n  FAIL: Cannot reach Supabase (network/DNS):", err[:120])
            _print_docker_fix()
            return 1
        print("\n  FAIL:", type(e).__name__, err[:120])
        if "JWT" in err or "key" in err.lower():
            print("  Fix: Use SUPABASE_SERVICE_ROLE_KEY from 'supabase status -o json' (SERVICE_ROLE_KEY)")
        return 1


def _print_docker_fix() -> None:
    print("\n  Fix (backend in Docker, Supabase on host):")
    print("    1. Start Supabase on the host:  supabase start")
    print("    2. In backend/.env set:          SUPABASE_URL=http://127.0.0.1:54321")
    print("    3. Get key:                      supabase status -o json  → SERVICE_ROLE_KEY")
    print("    4. Compose sets RUNNING_IN_DOCKER=1 so URL becomes host.docker.internal:54321")
    print("    5. docker-compose.yml must have: extra_hosts: [host.docker.internal:host-gateway]")


if __name__ == "__main__":
    sys.exit(main())
