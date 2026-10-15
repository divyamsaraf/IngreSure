# Item 12 — audits at zero + schedule

## Baseline

[`item12_scheduled_audit_report.json`](item12_scheduled_audit_report.json) reports
all four audits non-blocking:

- asserted-false signature: 0
- DISCOVERED name diff: 0
- L2↔L3 drift by name: 0
- lexicon vs verdict SAFE gaps: 0

Cleared on the way to zero (beyond the original five):

- 4 sulfured-fruit L2 alias heads + commodity-head refuse
- whipped-topping egg sticky clear via frozen reviewed list
- ghee ontology asserted-false pollution (direct patch to curated asserts)
- custard-apple fruit false dairy/egg from `custard` lexicon (name override +
  asserted clears)

## Schedule

- **Celery Beat:** `ike2-scheduled-audits-daily` → task `ike2_scheduled_audits`
  (`backend/worker/celery_app.py`, `backend/worker/tasks.py`).
- **GitHub Actions:** [`.github/workflows/ike2-nightly-audits.yml`](../.github/workflows/ike2-nightly-audits.yml)
  — 06:00 UTC cron + `workflow_dispatch`; uploads
  `item12-scheduled-audit` artifact when Supabase secrets are set; always runs
  the offline replay/clears CI slice.
