# API v1 and frontend endpoints

## Two audiences

- **Frontend (web app):** Uses a small set of endpoints for the chat UI, profile, and config. These are the only endpoints the Next.js app and BFF call.
- **Programmatic clients (API v1):** The `/api/v1/*` routes are for scripts, integrations, and other programmatic use. The frontend does **not** call them.

## Endpoints used by the frontend

| Method | Path | Purpose |
|--------|------|--------|
| `GET` | `/health` | Health check (e.g. Docker/K8s). |
| `GET` | `/config` | Profile options (diet/allergen/lifestyle) and `max_chat_message_length`. Frontend fetches this once (e.g. via BFF `/api/config`) and uses it for forms and validation. |
| `GET` | `/profile/{user_id}` | Get user profile by ID. |
| `POST` | `/profile` | Create or update profile (body: `user_id`, optional `dietary_preference`, `allergens`, `lifestyle`). |
| `POST` | `/chat/grocery` | Conversational ingredient check. Request: `query`, optional `user_id`, optional `userProfile`. Response: streaming text with embedded stream tags (see [stream-protocol.md](stream-protocol.md)). |

The frontend BFF (Next.js API routes) proxies to the backend using these paths. Do not rely on the frontend calling `/api/v1/*`.

## API v1 (programmatic only)

**Prefix:** `/api/v1`

These routes are for programmatic access (scripts, external services, CLI tools). They are **not** used by the web frontend.

| Method | Path | Purpose |
|--------|------|--------|
| `POST` | `/api/v1/resolve-ingredient` | Resolve one name to IKE-2 facts (no compliance). `try_api` and `log_unknown` are ignored. |
| `GET` | `/api/v1/ingredient/{name}` | Same IKE-2 resolve by name. `try_api` is ignored. |
| `POST` | `/api/v1/evaluate-compliance` | Evaluate a list of ingredients against `restriction_ids`; returns a compliance verdict. |
| `POST` | `/api/v1/evaluate-product` | Parse ingredient label text into ingredients and evaluate compliance. |

API v1 is mounted on the same FastAPI app; if the v1 router fails to load (e.g. missing dependency), the main app still runs and the frontend is unaffected.

## Summary

- **Frontend:** `/health`, `/config`, `/profile`, `/chat/grocery` only.
- **Programmatic:** Use `/api/v1/*` for resolve and evaluate; do not depend on the frontend calling these.
