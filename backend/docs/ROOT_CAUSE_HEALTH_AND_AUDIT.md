# Root cause: `/health` 404 and missing `<<<INGREDIENT_AUDIT>>>`

## Symptoms

- `curl http://127.0.0.1:8000/health` → **404 Not Found**
- `POST /chat/grocery` with "I am Jain. Can I eat potato chips?" returns:
  - Plain text: "Got it — I've updated your profile to **Jain**. Based on your **Jain** diet, **Potato chips** is **not suitable**..."
  - `<<<PROFILE_UPDATE>>>` block present
  - **No** `<<<INGREDIENT_AUDIT>>>` block

## Root cause (single)

**The process currently bound to port 8000 was started from an older revision of the code.**

It is **not** a bug in the current codebase. Evidence:

1. **Current `app.py`**
   - Defines **one** `GET /health` (lines 221–224) returning `status`, `service`, and `ingredient_audit_emitter: true`.
   - The v1 router (`core/api/v1`) only adds routes under `/api/v1/`; it does **not** define `/health` or override it.
   - There is only one FastAPI app and one uvicorn entry point: `app:app` in `app.py` (and `backend/Dockerfile` CMD).

2. **Current chat flow**
   - For an ingredient query (e.g. "I am Jain. Can I eat potato chips?"):
     - Intent is MIXED or INGREDIENT_QUERY with profile update; ingredients are extracted ("potato chips").
     - Compliance runs → `template_verdict()` builds `response_text` → `build_ingredient_audit_payload(..., explanation_text=response_text)` → **only** `yield audit_block` and `yield _profile_json(profile)` (no `yield response_text` in current code).
   - So with **current** code, the stream would contain `<<<INGREDIENT_AUDIT>>>` and no long plain‑text verdict in the body.

3. **What the running server does**
   - Serves `GET /` with `{"status":"ok","service":"IngreSure AI Scanner"}` (same as current `root()`).
   - Returns **404** for `GET /health` → that process has **no** `/health` route (older revision).
   - Returns the verdict as **plain text** plus `<<<PROFILE_UPDATE>>>` and **no** `<<<INGREDIENT_AUDIT>>>` → that revision still had `yield response_text` and did not yet emit the audit block.

**Conclusion:** The server on port 8000 is an **old** instance (started before adding `/health` and the audit-only yield). Restarting the backend from the **current** repo (so the new `app.py` is loaded) fixes both issues.

## What to do

1. **Stop** the process using port 8000 (e.g. Ctrl+C in the terminal where it runs, or `kill $(lsof -ti :8000)`).
2. **Start** the backend from the **current** codebase:
   ```bash
   cd /Users/divyam/Documents/IngreSure/backend
   USE_NEW_ENGINE=true uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```
   Or use the restart script (stops port 8000 then starts uvicorn):
   ```bash
   ./backend/scripts/restart_backend.sh
   ```
3. **Verify**
   - `curl http://127.0.0.1:8000/health` → 200 and body includes `"ingredient_audit_emitter": true`.
   - `python3 scripts/verify_chat_audit.py` (from `backend/`) → reports that the response contains `<<<INGREDIENT_AUDIT>>>`.

After a correct restart, the frontend will receive the audit block and the premium UI (summary pills, grouped cards, “Read more”) will work.
