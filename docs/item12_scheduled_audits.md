# Item 12 — First scheduled task: wrap existing one-off audits

**Status:** script landed 2026-10-13 (report-only; Beat/Sentry wiring still Item 12 proper).

## Script

```bash
cd backend
python scripts/ike2_item12_scheduled_audits.py
python scripts/ike2_item12_scheduled_audits.py --fail-on-findings
```

Writes `docs/item12_scheduled_audit_report.json`.

## Audits wrapped

| Audit | Prior one-offs | Blocking when |
|-------|----------------|---------------|
| Asserted-false signature | Item 11 live repair / pollution guard | >3 asserted falses on a row (non-curated) |
| DISCOVERED name diff | `bulk_inject --discovered-diff`, item37 ops | optional; informational by default |
| L2 ↔ L3 drift by name | `item37_l2_l3_layer_exposure.py`, Item 41 CI replay | any `live_true && l2_false` on verdict flags |
| Lexicon vs verdict (live) | Item 42 live lexicon scan | SAFE with name-implied flag absent (excl. enumerated false friends) |

## Not yet (rest of Item 12)

- Celery Beat schedule / cron  
- Sentry or alert routing on `--fail-on-findings`  
- request_history for `/api/v1/*`, structured request IDs, readiness `/health`  
- Replacing deleted `enrichment_metrics` writer  

This wrapper is the minimum that turns “standing audits are a plan” into a runnable command over the same one-off logic.
