# Soak and metrics (Item 12 / Item 58)

## Nightly soak

When `backend/scripts/soak_evaluate.py` is present:

```bash
cd backend
LLM_ENABLED=false python scripts/soak_evaluate.py
```

Or via the wrapper used by `.github/workflows/nightly-soak.yml`:

```bash
python backend/scripts/run_nightly_soak.py
```

`soak_evaluate.py` is expected to send a large batch of `/api/v1/evaluate-product`
requests (serial vs parallel), write `backend/.local_reports/soak_648.json`,
and fail if any 500 or serial/parallel mismatch occurs.

If that script is not on the branch yet, the nightly workflow skips and prints
the command above.

## /metrics

Mount `core.observability.router.router` and set `METRICS_TOKEN`. Then:

```bash
curl -H "Authorization: Bearer $METRICS_TOKEN" https://<host>/metrics
```

or `X-Metrics-Token: $METRICS_TOKEN`.

Returned fields used by alert rules (see `docs/observability/alert_rules.md`):

| Field | Meaning |
| --- | --- |
| `requests.degraded_rate` | degraded / requests since process start |
| `requests.status_5xx_rate` | 5xx / requests since process start |
| `requests.latency_ms.p95` | p95 of in-process latency samples |
| `unknown_queue.pending` | pending `ike2_unknown_queue` rows (null if no DB) |
| `miss_class.by_class` | persisted miss_class counts (no raw atoms) |
