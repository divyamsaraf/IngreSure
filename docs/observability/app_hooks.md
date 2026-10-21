# Observability hooks (do not apply here)

Track C ships import-safe modules only. **Do not edit `backend/app.py` on this
branch.** Apply the patches below in a later wiring PR.

## Backend (`backend/app.py`)

After env load / `log_config()`, before routes are used:

```python
from core.observability.sentry import init_sentry
init_sentry()
```

After the existing CORS middleware (so the request logger sees the final
status):

```python
from core.observability.middleware import StructuredRequestLogMiddleware
app.add_middleware(StructuredRequestLogMiddleware)
```

Next to the v1 router include:

```python
from core.observability.router import router as observability_router
app.include_router(observability_router)
```

### Optional: bind engine / degraded / verdict counts

Structured logs already infer `engine=ike2` for `/api/v1/*` and `/chat/*`,
and read verdict `status` from JSON responses. For streaming `/chat/grocery`
(no JSON body), set fields on `request.state` inside the handler — counts
and flags only, never ingredient text or profile fields:

```python
from core.observability.request_context import bind_request_observability
bind_request_observability(
    request,
    engine="ike2",
    degraded=False,
    verdict_counts={"safe": 2, "avoid": 1},
)
```

### Optional: persist miss_class from the resolver

`core.knowledge.ike2.miss_class.classify_miss_class` already tags L5 misses.
To persist counts (hashed keys only), add one call after classify — not on
this branch:

```python
from core.observability.miss_class_store import record_miss_class
record_miss_class(resolved.miss_class, normalized_key=atom)
```

## Frontend (no chat-page edits)

1. `npm i @sentry/nextjs` in `frontend/`.
2. Set `NEXT_PUBLIC_SENTRY_DSN` and `NEXT_PUBLIC_GIT_SHA` (or rely on
   `VERCEL_GIT_COMMIT_SHA`).
3. Add **new** files (do not rewrite chat pages):

`frontend/instrumentation-client.ts`:

```ts
import * as Sentry from "@sentry/nextjs";
import { initSentry } from "./sentry.client";
initSentry(Sentry);
```

`frontend/instrumentation.ts`:

```ts
export async function register() {
  const Sentry = await import("@sentry/nextjs");
  if (process.env.NEXT_RUNTIME === "edge") {
    const { initSentry } = await import("./sentry.edge");
    initSentry(Sentry);
    return;
  }
  const { initSentry } = await import("./sentry.server");
  initSentry(Sentry);
}
```

`frontend/sentry.client.ts`, `sentry.server.ts`, `sentry.edge.ts`, and
`sentry.shared.ts` are already on this branch. They no-op without a DSN or
without an SDK argument. `sendDefaultPii` is false; request bodies and
profile/ingredient keys are scrubbed.

## Environment

| Variable | Purpose |
| --- | --- |
| `SENTRY_DSN` | Backend Sentry (optional) |
| `NEXT_PUBLIC_SENTRY_DSN` / `SENTRY_DSN` | Frontend Sentry (optional) |
| `GIT_SHA` / `GITHUB_SHA` / `VERCEL_GIT_COMMIT_SHA` | `release` |
| `NEXT_PUBLIC_GIT_SHA` | Frontend release override |
| `METRICS_TOKEN` | Required for `GET /metrics` (404 if unset) |
| `OBSERVABILITY_MISS_CLASS_PATH` | Override miss_class JSON path |

Install backend SDK when wiring: `pip install sentry-sdk` (not added to
`requirements.txt` on this branch so import stays optional).
