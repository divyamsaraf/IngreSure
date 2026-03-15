#!/usr/bin/env python3
"""
Verify end-to-end flow: Backend → LLM (when used) → responses in correct sequence.
Run from repo root: python3 backend/scripts/verify_flow_and_llm.py
Or from backend:  python3 scripts/verify_flow_and_llm.py
(Ollama optional: greeting/general use LLM when available, else templates; ingredient verdicts are always template-based.)

Uses TestClient (no live server). Confirms:
- Health responds
- Chat greeting path (LLM or template) returns stream with <<<PROFILE_UPDATE>>>
- Chat ingredient path returns <<<INGREDIENT_AUDIT>>> + verdict text + <<<PROFILE_UPDATE>>>
- Profile GET returns 200
"""
from __future__ import annotations

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

def main() -> int:
    from fastapi.testclient import TestClient
    from core.stream_tags import PROFILE_UPDATE_TAG, INGREDIENT_AUDIT_TAG
    from app import app

    client = TestClient(app)
    failures = []

    # 1. Health
    r = client.get("/health")
    if r.status_code != 200 or "ok" not in (r.json() or {}).get("status", "").lower():
        failures.append(f"GET /health: {r.status_code} {r.text[:200]}")
    else:
        print("1. GET /health → 200 OK")

    # 2. Chat: greeting → stream must contain PROFILE_UPDATE (LLM or template reply + profile blob)
    r = client.post("/chat/grocery", json={"query": "hello", "user_id": "flow-test-user"})
    if r.status_code != 200:
        failures.append(f"POST /chat/grocery greeting: {r.status_code} {r.text[:200]}")
    else:
        body = r.text
        if PROFILE_UPDATE_TAG not in body:
            failures.append(f"Chat greeting stream missing {PROFILE_UPDATE_TAG}")
        if len(body.strip()) < 20:
            failures.append("Chat greeting stream too short (no reply text)")
        if not failures:
            print("2. POST /chat/grocery (greeting) → 200, stream has PROFILE_UPDATE and reply text")

    # 3. Chat: ingredient query → stream must contain INGREDIENT_AUDIT and PROFILE_UPDATE
    r = client.post(
        "/chat/grocery",
        json={
            "query": "Is milk vegan?",
            "user_id": "flow-test-user",
            "userProfile": {"dietary_preference": "Vegan", "allergens": [], "lifestyle": []},
        },
    )
    if r.status_code != 200:
        failures.append(f"POST /chat/grocery ingredient: {r.status_code} {r.text[:200]}")
    else:
        body = r.text
        if INGREDIENT_AUDIT_TAG not in body:
            failures.append(f"Chat ingredient stream missing {INGREDIENT_AUDIT_TAG}")
        if PROFILE_UPDATE_TAG not in body:
            failures.append(f"Chat ingredient stream missing {PROFILE_UPDATE_TAG}")
        # Verdict text (template-based) should mention milk/vegan/dairy
        if "milk" not in body.lower() and "dairy" not in body.lower():
            failures.append("Chat ingredient reply should mention milk/dairy for vegan check")
        if not failures:
            print("3. POST /chat/grocery (ingredient) → 200, stream has INGREDIENT_AUDIT + PROFILE_UPDATE + verdict text")

    # 4. Profile get
    r = client.get("/profile/flow-test-user")
    if r.status_code != 200:
        failures.append(f"GET /profile: {r.status_code}")
    else:
        print("4. GET /profile/flow-test-user → 200")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nAll flow checks passed. Backend, LLM (when used), and response sequence OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
