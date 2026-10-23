# Staging owner actions (L1.6)

No production credentials in git, in chat, or in the staging env file.
Cursor does planning, dry runs, and verification. Production stays owner-only.

1. Create a **new** Supabase project for staging (not the production project). Free/Pro is about **$0–25/month**. Record the project ref only — not the service-role key — in any shared note.
2. Copy `deploy/staging/env.template` to a host-local file (for example `deploy/staging/.env`, gitignored). Fill every name: `ENVIRONMENT=staging`, `B2B_API_KEYS`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `CORS_ORIGINS` (the Vercel preview origin), `GIT_SHA`, `RATE_LIMIT_*`, `SENTRY_DSN`. Use staging values only.
3. Add `deploy/staging/Caddyfile.snippet` to `/etc/caddy/Caddyfile` with a hostname distinct from `ingresure-api.gleeze.com`. Point DNS at the instance. Set `CADDY_STAGING_API_V1_KEY` in the Caddy service environment (not in git). Then `sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy`.
4. Build/tag the API image, set `INGRESURE_API_IMAGE` and `GIT_SHA` on the host, and start the staging container on **127.0.0.1:8002**:
   `cd deploy/staging && docker compose up -d`
   Confirm it is not bound on `0.0.0.0:8002`.
5. Give Cursor the **staging** keys (`SUPABASE_URL`, service-role key, a staging B2B key) so migrate, seed, and G3 can run against staging. Do **not** give production keys.

Production remains owner-only. Before **any** production migration, take a manual `pg_dump` (direct `:5432` URI). The production project is on the free tier: **no PITR**, and the backups list was empty.
