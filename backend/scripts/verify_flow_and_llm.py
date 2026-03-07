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
- Scan returns list ingredients and scorecard
"""
from __future__ import annotations

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

def main() -> int:
    from fastapi.testclient import TestClient
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
        if "<<<PROFILE_UPDATE>>>" not in body:
            failures.append("Chat greeting stream missing <<<PROFILE_UPDATE>>>")
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
        if "<<<INGREDIENT_AUDIT>>>" not in body:
            failures.append("Chat ingredient stream missing <<<INGREDIENT_AUDIT>>>")
        if "<<<PROFILE_UPDATE>>>" not in body:
            failures.append("Chat ingredient stream missing <<<PROFILE_UPDATE>>>")
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

    # 5. Scan (minimal PNG)
    png = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
        0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
        0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
        0x44, 0xAE, 0x42, 0x60, 0x82,
    ])
    r = client.post("/scan", files={"file": ("test.png", png, "image/png")})
    if r.status_code != 200:
        failures.append(f"POST /scan: {r.status_code} {r.text[:200]}")
    else:
        j = r.json()
        if not isinstance(j.get("ingredients"), list) or "dietary_scorecard" not in j:
            failures.append("Scan response missing ingredients list or dietary_scorecard")
        else:
            print("5. POST /scan → 200, ingredients list + dietary_scorecard")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nAll flow checks passed. Backend, LLM (when used), and response sequence OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
