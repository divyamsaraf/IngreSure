# Deploy notes — observability

Do not apply `app.py` hooks from this branch. After wiring
(`docs/observability/app_hooks.md`):

1. Set `GIT_SHA` (or rely on `GITHUB_SHA` / `VERCEL_GIT_COMMIT_SHA`) so
   Sentry `release` matches the deployed commit.
2. Set `SENTRY_DSN` on the API and `NEXT_PUBLIC_SENTRY_DSN` on the frontend
   only after `@sentry/nextjs` / `sentry-sdk` are installed.
3. Set `METRICS_TOKEN` and scrape `GET /metrics` over the private network.
   Do not expose `/metrics` without the token. Unset token → 404.
4. Optional: `OBSERVABILITY_MISS_CLASS_PATH` for a durable miss_class file
   outside the container filesystem.
5. Nightly soak: `.github/workflows/nightly-soak.yml` (Item 58).
6. Confirm structured logs (`logger=ingresure.request`) contain no query,
   ingredient, or profile fields before enabling log shipping.
