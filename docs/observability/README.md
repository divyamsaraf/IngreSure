# Observability (Item 12)

| Piece | Location |
| --- | --- |
| Sentry (backend) | `backend/core/observability/sentry.py` |
| Sentry (frontend) | `frontend/sentry.client.ts`, `sentry.server.ts`, `sentry.edge.ts` |
| Request logs + middleware | `backend/core/observability/middleware.py` |
| `/metrics` router | `backend/core/observability/router.py` |
| miss_class persistence | `backend/core/observability/miss_class_store.py` |
| App wiring (not applied) | [app_hooks.md](./app_hooks.md) |
| Alert rules | [alert_rules.md](./alert_rules.md) |
| Soak (Item 58) | `backend/scripts/README_soak_metrics.md` |
| Privacy inventory | [../privacy/data_inventory.md](../privacy/data_inventory.md) |
