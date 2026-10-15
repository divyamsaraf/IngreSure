# IngreSure — Services Overview

> **September 2026:** Chat and `/api/v1/evaluate-*` serve **IKE-2 only** (Item 16 Prompt 7). `IKE2_MODE` and legacy `ComplianceEngine` are removed. See `docs/README.md` and `docs/item16_legacy_cutover_spec.md`.

What runs where, what uses what, and what is required in Docker.

---

## Summary

| Service | Used? | Where used | In Docker? | Required in Docker? |
|--------|--------|------------|-------------|---------------------|
| **Frontend** (Next.js) | Yes | UI: /, /chat; proxies chat & profile to backend | Yes (ingresure-frontend) | **Yes** — for the app UI |
| **Backend** (FastAPI) | Yes | /chat/grocery, /profile, API v1, /health | Yes (ingresure-backend) | **Yes** — core API |
| **LLM (Ollama)** | Optional | Chat intent fallback + reply prose; optional enrichment classify (worker). **Not** used for compliance or scan/OCR | **No** — runs on **host** | **N/A** — host Ollama via `host.docker.internal:11434` when enabled |
| **Redis** | Optional | Celery broker only | Yes (ingresure-redis) | **No** — only needed if you use the worker |
| **Celery worker** | Optional | Background: enrich unknown ingredients (`ike2_unknown_queue`) | Yes (ingresure-worker) | **No** — chat/profile work without it |
| **Supabase** | Optional | Backend: knowledge DB (ingredient_groups, etc.), optional profile storage | **No** — run via `supabase start` or use hosted | **N/A** — not in docker-compose |

---

## 1. Frontend (Next.js)

- **Role:** Web UI — home, Grocery Assistant (chat).
- **Uses:** Backend via `BACKEND_URL` (in Docker: `http://backend:8000`).
  - **Chat:** Browser → frontend `/api/chat` → backend `/chat/grocery`.
  - **Profile:** Browser → frontend `/api/profile` → backend `/profile` or `/profile/{id}`.
- **In Docker:** Yes — `ingresure-frontend`, port 3000.
- **Required:** Yes — this is the only UI.

---

## 2. Backend (FastAPI)

- **Role:** API — chat (grocery safety), profile, API v1 evaluate/resolve, health.
- **Uses:**
  - **Ollama (LLM, optional):** Chat intent fallback, chat responses (greetings, general, verdict phrasing), optional enrichment classification in the worker. **Compliance and resolve never call Ollama.** `OLLAMA_API_URL` in Docker points to `http://host.docker.internal:11434/api/generate`.
  - **Supabase (optional):** Knowledge DB (IKE-2 `ike2_*` tables), optional profile storage. If not set, backend still runs (file-based profile, ontology JSON only).
  - **Redis:** Not used by the backend process itself; only by the Celery worker.
- **In Docker:** Yes — `ingresure-backend`, port 8000.
- **Required:** Yes — core of the app.

---

## 3. LLM (Ollama)

- **Role:** Local LLM for chat UX (intent fallback, greetings/general/verdict phrasing) and optional enrichment classification. See `docs/AI_ENGINE.md` and `docs/item6_llm_pipeline_spec.md`.
- **Where it runs:** On the **host** (not in Docker). Install and run: `ollama serve`, `ollama pull llama3.2:3b`.
- **Docker:** Backend container reaches it via `OLLAMA_API_URL=http://host.docker.internal:11434/api/generate` (set in docker-compose).
- **Required:** **No.** Without it (`LLM_ENABLED=false` or Ollama down): chat falls back to templates; enrichment skips classify. Verdicts are unchanged.

---

## 4. Redis

- **Role:** Message broker for Celery (task queue).
- **Used by:** Only the Celery worker (and scripts that trigger tasks, e.g. `trigger_enrich_batch.py`).
- **In Docker:** Yes — `ingresure-redis`, port 6379.
- **Required in Docker:** **No** for basic app (chat, profile). **Yes** only if you run the Celery worker and want to trigger enrichment via the queue.

---

## 5. Celery worker

- **Role:** Background job: enrich unknown ingredients (USDA → OFF → PubChem → ChEBI → Wikidata, optional LLM classify).
- **Used when:** You use Supabase knowledge DB and run enrichment (e.g. `trigger_enrich_batch.py` or future triggers).
- **In Docker:** Yes — `ingresure-worker`.
- **Required in Docker:** **No** for basic app. Chat and profile work without it; only “enrich unknown ingredients” needs it.

---

## 6. Supabase

- **Role:** Postgres + Auth; optional knowledge DB (ingredient_groups, ingredients, etc.) and optional profile storage.
- **Where it runs:** Not in docker-compose. Either:
  - Local: `supabase start` (separate containers, e.g. `supabase_db_ingresure`), or
  - Hosted project (e.g. supabase.com).
- **Required:** No. Backend runs without it (file-based profile, no knowledge DB). Needed only for ingredient knowledge and optional profile persistence.

---

## Docker: what is required?

- **Minimum to run the app (UI + API):**
  - **Docker:** `backend` + `frontend`.
  - **Host (optional):** Ollama for natural chat prose (`ollama serve`, model pulled). Not required for compliance.
  - Optional: Supabase (local or hosted) if you want knowledge DB.

- **Current docker-compose (all 4 services):**
  - **backend** — required.
  - **frontend** — required.
  - **redis** — required only if you use the worker.
  - **worker** — required only for background enrichment.

To run a **lighter stack without Redis/worker** (chat + profile only), you can start only backend and frontend:

```bash
docker compose up --build backend frontend
```

Redis and worker will not start; the app will work for chat and profile. Enrichment (unknown ingredients) will not run in the background unless you run scripts like `run_enrich_unknown_once.py` manually without Celery.

---

## Flow and sequence (Chat)

**Chat (Grocery Assistant)**

1. **Frontend** → User types message → `ChatInterface` sends `POST` to Next.js `/api/chat` with `{ message, user_id, userProfile }`.
2. **Next.js** → `api/chat/route.ts` proxies to backend `POST ${BACKEND_URL}/chat/grocery` with `{ query, user_id, userProfile }`.
3. **Backend** (in order):
   - Load/merge profile; handle `/update` slash-command if present.
   - **Intent:** Rule-based `detect_intent(query)` first; if result is ambiguous (GENERAL_QUESTION, no ingredients), **LLM fallback** `llm_extract_intent(query)` when `llm_enabled()`.
   - **GREETING** → **LLM** `llm_compose_greeting(profile)` or template → stream reply + `<<<PROFILE_UPDATE>>>` JSON.
   - **General question (no ingredients)** → **LLM** `llm_compose_general(query, profile)` or template → stream + `<<<PROFILE_UPDATE>>>`.
   - **Ingredient query** → Parse ingredients → expand compounds → **IKE-2 compliance** (no LLM) → template / optional LLM verdict phrasing overlay → stream `<<<INGREDIENT_AUDIT>>>` JSON + reply text + `<<<PROFILE_UPDATE>>>`.
4. **Frontend** → Reads stream; parses `<<<PROFILE_UPDATE>>>` and `<<<INGREDIENT_AUDIT>>>`; updates profile state and audit cards; displays reply text.

There is **no** production scan/OCR → LLM-normalizer path. Label text is pasted/typed into chat (or evaluated via `/api/v1`).

**Verification script:**

```bash
python backend/scripts/verify_flow_and_llm.py
```

Checks: health, chat greeting stream (PROFILE_UPDATE + reply), chat ingredient stream (INGREDIENT_AUDIT + PROFILE_UPDATE + verdict text), profile get.
