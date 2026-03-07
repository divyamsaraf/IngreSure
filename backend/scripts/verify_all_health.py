#!/usr/bin/env python3
"""
Verify all APIs, services, and key flows are healthy.
Run from repo root: python backend/scripts/verify_all_health.py
Or from backend:  python scripts/verify_all_health.py

Exit 0 if all critical checks pass; 1 otherwise. Loads backend/.env if present.
"""
from __future__ import annotations

import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Add backend to path
_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
try:
    from dotenv import load_dotenv
    load_dotenv(_backend / ".env")
    load_dotenv(_backend.parent / ".env")
except ImportError:
    pass

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 15


def ok(msg: str) -> None:
    print(f"  OK: {msg}")


def fail(msg: str) -> None:
    print(f"  FAIL: {msg}")


def check_backend_health() -> bool:
    print("\n1. Backend health")
    try:
        req = urllib.request.Request(f"{BACKEND_URL}/health", method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            if r.getcode() != 200:
                fail(f"health returned {r.getcode()}")
                return False
            data = r.read().decode()
            if "ok" not in data.lower():
                fail(f"health body: {data[:80]}")
                return False
        ok("Backend /health returned 200")
        return True
    except urllib.error.URLError as e:
        fail(f"Backend unreachable: {e.reason}")
        return False
    except Exception as e:
        fail(str(e))
        return False


def check_external_apis() -> bool:
    print("\n2. External enrichment APIs (USDA, OFF, PubChem, ChEBI, Wikidata)")
    try:
        from scripts.check_external_apis import main as check_main
        # Script exits 0 if at least one API works
        code = check_main()
        if code != 0:
            fail("All 5 APIs failed or none configured")
            return False
        ok("At least one API working (unknown-ingredient lookup will run)")
        return True
    except Exception as e:
        fail(str(e))
        return False


def check_supabase() -> bool:
    print("\n3. Supabase (knowledge DB, unknowns)")
    try:
        from scripts.verify_supabase import main as supabase_main
        code = supabase_main()
        if code != 0:
            fail("Supabase not reachable or not configured")
            return False
        return True
    except Exception as e:
        fail(str(e))
        return False


def check_redis() -> bool:
    print("\n4. Redis (Celery broker)")
    try:
        import redis
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(url, decode_responses=True)
        r.ping()
        ok("Redis ping OK")
        return True
    except Exception as e:
        fail(f"Redis unreachable: {e}")
        return False


def check_regional_resolution() -> bool:
    print("\n5. Regional ingredient resolution (e.g. bajra -> pearl millet)")
    try:
        from core.external_apis.regional_names import get_canonical_queries
        from core.knowledge.canonicalizer import CanonicalResolver
        q = get_canonical_queries("bajra")
        if "pearl millet" not in q:
            fail(f"get_canonical_queries('bajra') = {q}")
            return False
        ok(f"Built-in mapping: bajra -> {q[0]}")
        res = CanonicalResolver().resolve_with_fallback("bajra", try_api=True, log_unknown=False)
        if res.ingredient is None:
            fail("resolve_with_fallback('bajra') returned no ingredient")
            return False
        if "pearl" not in (res.ingredient.canonical_name or "").lower() and "millet" not in (res.ingredient.canonical_name or "").lower():
            fail(f"Resolved to unexpected name: {res.ingredient.canonical_name}")
            return False
        ok(f"Resolved bajra -> {res.ingredient.canonical_name} (source={res.source_layer})")
        return True
    except Exception as e:
        fail(str(e))
        return False


def check_chat_grocery() -> bool:
    print("\n6. Chat /chat/grocery (bajra)")
    try:
        import json
        req = urllib.request.Request(
            f"{BACKEND_URL}/chat/grocery",
            data=json.dumps({
                "query": "bajra",
                "user_id": "verify-health",
                "userProfile": {"dietary_preference": "vegan", "allergens": [], "lifestyle": []},
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.getcode() != 200:
                fail(f"POST /chat/grocery returned {r.getcode()}")
                return False
            body = r.read().decode()
            if "Couldn't find reliable information" in body and "bajra" in body.lower():
                fail("Response still says couldn't find info for bajra")
                return False
            if "manual verification" in body.lower() and "bajra" in body.lower():
                fail("Response suggests manual verification for bajra")
                return False
        ok("Chat returned 200 and resolved bajra")
        return True
    except urllib.error.URLError as e:
        fail(f"Request failed: {e.reason}")
        return False
    except Exception as e:
        fail(str(e))
        return False


def main() -> int:
    print("IngreSure health and API verification")
    print(f"  BACKEND_URL={BACKEND_URL}")

    results = []
    results.append(("Backend health", check_backend_health()))
    results.append(("External APIs", check_external_apis()))
    results.append(("Supabase", check_supabase()))
    results.append(("Redis", check_redis()))
    results.append(("Regional resolution", check_regional_resolution()))
    results.append(("Chat grocery", check_chat_grocery()))

    passed = sum(1 for _, v in results if v)
    total = len(results)
    print("\n" + "=" * 50)
    print(f"Result: {passed}/{total} checks passed")
    if passed < total:
        for name, v in results:
            if not v:
                print(f"  - {name}: FAILED")
        return 1
    print("  All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
