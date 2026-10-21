# Alert rules (Item 12)

Source of truth for thresholds: `GET /metrics` after the router is mounted
(`docs/observability/app_hooks.md`). Counters are **process-local** until a
metrics backend is wired; page/scrape `/metrics` from each replica.

These are operational thresholds, not legal or medical advice.

## 1. Degraded rate > 1%

- **Signal:** `requests.degraded_rate`
- **Warn when:** `degraded_total / requests_total > 0.01` over a 15-minute window
  (or since process start if no windowed backend yet)
- **Meaning:** IKE-2 answered with a degraded layer / unclassified knowledge
  state, or a handler set `request.state.degraded`
- **Action:** Check `/metrics` `by_route`, miss_class snapshot, and recent
  structured logs (`event=http_request`, `degraded=true`). Do not pull raw
  user text from `request_history` unless an on-call review requires it.

Suggested PromQL (when scraped):

```
sum(rate(ingresure_degraded_total[15m]))
  / sum(rate(ingresure_requests_total[15m])) > 0.01
```

## 2. 5xx rate > 0.5%

- **Signal:** `requests.status_5xx_rate`
- **Warn when:** `status_5xx_total / requests_total > 0.005` over 15 minutes
- **Page when:** any sustained 5xx on `/chat/grocery` or `/api/v1/evaluate-*`
- **Action:** Sentry release = git SHA; confirm `send_default_pii=false` and
  that the event has no request body.

```
sum(rate(ingresure_status_5xx_total[15m]))
  / sum(rate(ingresure_requests_total[15m])) > 0.005
```

## 3. p95 latency

- **Signal:** `requests.latency_ms.p95` (in-process samples, cap 2048)
- **Warn when:**
  - `/api/v1/evaluate-*` p95 > **2500 ms** for 15 minutes
  - `/chat/grocery` p95 > **8000 ms** for 15 minutes
  - all-routes p95 > **5000 ms** for 15 minutes
- **Action:** Check LLM_ENABLED / Ollama warmup, DB latency, and soak report
  (`backend/.local_reports/soak_648.json` from nightly Item 58).

## 4. Unknown-queue growth

- **Signal:** `unknown_queue.pending` (and `unknown_queue.total`)
- **Warn when:**
  - pending count grows **> 20% week over week**, or
  - pending increases by **> 50 rows / 24h** on a stable ontology
- **Action:** Inspect miss_class distribution (`miss_class.by_class`) — counts
  and hashed keys only. Promote via the existing induction path; do not dump
  `raw_inputs` from `ike2_unknown_queue` into tickets.

Until a time-series backend exists, snapshot `unknown_queue.pending` nightly
(alongside soak) and compare to the previous artifact.
