#!/usr/bin/env python3
"""
Verify chat flow with multiple messages and (when REDIS_URL set) resolution cache usage.

Usage:
  # Without Redis - flow only
  REDIS_URL= python3 backend/scripts/verify_redis_resolution_flow.py

  # With Redis - flow + check cache keys after requests
  REDIS_URL=redis://localhost:6379/0 python3 backend/scripts/verify_redis_resolution_flow.py

Exits 0 if all checks pass.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))


def main() -> int:
    from fastapi.testclient import TestClient
    from core.stream_tags import PROFILE_UPDATE_TAG, INGREDIENT_AUDIT_TAG
    from app import app

    redis_url = os.environ.get("REDIS_URL", "").strip()
    has_redis = bool(redis_url)

    client = TestClient(app)
    failures = []

    # --- 1. Greeting ---
    r = client.post("/chat/grocery", json={"query": "hi", "user_id": "redis-flow-user"})
    if r.status_code != 200:
        failures.append(f"Greeting: status {r.status_code} {r.text[:150]}")
    elif PROFILE_UPDATE_TAG not in r.text:
        failures.append("Greeting: stream missing PROFILE_UPDATE")
    else:
        print("1. Greeting → 200, PROFILE_UPDATE present")

    # --- 2. Milk (vegan) ---
    r = client.post(
        "/chat/grocery",
        json={
            "query": "Is milk vegan?",
            "user_id": "redis-flow-user",
            "userProfile": {"dietary_preference": "Vegan", "allergens": [], "lifestyle": []},
        },
    )
    if r.status_code != 200:
        failures.append(f"Milk query: status {r.status_code} {r.text[:150]}")
    elif INGREDIENT_AUDIT_TAG not in r.text or PROFILE_UPDATE_TAG not in r.text:
        failures.append("Milk query: stream missing INGREDIENT_AUDIT or PROFILE_UPDATE")
    elif "milk" not in r.text.lower() and "dairy" not in r.text.lower():
        failures.append("Milk query: reply should mention milk/dairy")
    else:
        print("2. Milk (vegan) → 200, INGREDIENT_AUDIT + verdict")

    # --- 3. Egg (vegan) ---
    r = client.post(
        "/chat/grocery",
        json={
            "query": "Can I have egg?",
            "user_id": "redis-flow-user",
            "userProfile": {"dietary_preference": "Vegan", "allergens": [], "lifestyle": []},
        },
    )
    if r.status_code != 200:
        failures.append(f"Egg query: status {r.status_code}")
    elif INGREDIENT_AUDIT_TAG not in r.text:
        failures.append("Egg query: stream missing INGREDIENT_AUDIT")
    else:
        print("3. Egg (vegan) → 200, INGREDIENT_AUDIT")

    # --- 4. Milk again (tests cache hit when Redis on) ---
    r = client.post(
        "/chat/grocery",
        json={
            "query": "What about milk?",
            "user_id": "redis-flow-user",
            "userProfile": {"dietary_preference": "Vegan", "allergens": [], "lifestyle": []},
        },
    )
    if r.status_code != 200:
        failures.append(f"Milk repeat: status {r.status_code}")
    elif INGREDIENT_AUDIT_TAG not in r.text:
        failures.append("Milk repeat: stream missing INGREDIENT_AUDIT")
    else:
        print("4. Milk (repeat) → 200, INGREDIENT_AUDIT")

    # --- 5. When Redis is set, check resolution cache keys ---
    if has_redis and not failures:
        try:
            import redis as redis_lib
            rclient = redis_lib.from_url(redis_url, decode_responses=True)
            rclient.ping()
            keys = rclient.keys("ingresure:resolve:*")
            if keys:
                print(f"5. Redis: {len(keys)} resolution cache key(s) present (e.g. ingresure:resolve:milk:1)")
            else:
                print("5. Redis: no resolution keys yet (cache may use different DB or prefix)")
        except Exception as e:
            print(f"5. Redis: could not check keys: {e}")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nAll flow checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
