# Deployment guide — IngreSure

Production shape: **Vercel** (Next.js UI) + **OCI** (or any host) for **FastAPI**. Redis, Celery, and Ollama are **optional** and controlled by **environment** and **Docker Compose profiles** — no separate application code paths per topology.

**At-a-glance cutover / stage status:** architecture tracker + [`docs/item16_legacy_cutover_spec.md`](docs/item16_legacy_cutover_spec.md) (not a separate PHASES.md).

**OCI VM (Oracle Cloud), step by step:** [OCI_STEP_BY_STEP.md](OCI_STEP_BY_STEP.md).

## Phases (recommended order)

### Phase 1 — Local Docker (default: API + UI)

1. `cp backend/.env.example backend/.env` and `cp frontend/.env.example frontend/.env.local`; add secrets (e.g. `USDA_FDC_API_KEY`).
2. `docker compose up --build` — starts **backend** + **frontend** only (lighter default).
3. Ollama on the host: defaults come from committed [`backend/.env.compose`](backend/.env.compose); override in `backend/.env` if needed.

### Phase 2 — Redis + Celery (optional)

When you have RAM and want resolution cache + background workers:

1. Add to `backend/.env`: `REDIS_URL=redis://redis:6379/0`
2. `docker compose --profile cache up -d`

### Phase 3 — OCI API only (no Next.js container)

1. `docker compose up -d backend` (or same with `--profile cache` if Redis/worker on that host).
2. Put **TLS** in front (Caddy, nginx, load balancer) → public `https://…`. For Caddy on the host, use **`bind 0.0.0.0`** in the site block so IPv4 clients can connect; see [`deploy/Caddyfile.example`](deploy/Caddyfile.example) and [OCI_STEP_BY_STEP.md](OCI_STEP_BY_STEP.md) Appendix G.
3. On the server, `backend/.env`: `CORS_ORIGINS` = your Vercel origins; `OLLAMA_API_URL` if LLM is reachable (see below).

### Phase 4 — Vercel

In the Vercel project → Environment variables:

- `BACKEND_URL` = `https://<your-public-api-host>` (no trailing slash).

Backend `CORS_ORIGINS` must include `https://<your-app>.vercel.app` (and custom domains).

### Phase 5 — Ollama on a second VM

1. Same VCN preferred. LLM VM NSG: inbound **TCP 11434** only from the API host or subnet.
2. API `backend/.env`: `OLLAMA_API_URL=http://<llm_private_ip>:11434/api/generate`
3. Override any value from `backend/.env.compose` by setting the same variable in `backend/.env` (loaded second).

### Phase 6 — Redis on a dedicated host (later)

Set on **API** and **worker** hosts: `REDIS_URL=redis://<redis_private_ip>:6379/0` (or `rediss://` if TLS). NSG: **6379** from API + worker only.

## Environment quick reference

| Variable | Where | Purpose |
|----------|-------|---------|
| `BACKEND_URL` | Vercel | Public HTTPS API URL |
| `CORS_ORIGINS` | `backend/.env` | Browser origins allowed |
| `OLLAMA_API_URL` | `backend/.env` / `.env.compose` | Ollama `…/api/generate` URL |
| `REDIS_URL` | `backend/.env` | Empty = no cache; set when Redis runs |

## Compose env file order

`backend` and `worker` load:

1. [`backend/.env.compose`](backend/.env.compose) (committed defaults for Docker)
2. [`backend/.env`](backend/.env) (secrets and overrides — **not** committed)

Later file wins on duplicate keys.

## Rollback

- Wrong API URL → fix Vercel `BACKEND_URL` or `backend/.env`.
- Redis issues → remove `REDIS_URL`, `docker compose up -d` without `cache` profile.
- LLM down → app falls back to templates for conversational text; compliance path unchanged.

## Multi-user note

Heavy concurrent **profile** writes use `data/profiles.json` (read–modify–write). For many replicas or high write concurrency, plan a move to a transactional store (e.g. Supabase). See plan discussion in project docs if present.
