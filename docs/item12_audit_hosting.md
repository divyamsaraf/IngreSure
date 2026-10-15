# Item 12 — where audits actually run

| Runner | Store | What runs | Failure visibility |
|--------|-------|-----------|--------------------|
| **Celery Beat** (`ike2-scheduled-audits-daily`, 86400s) on the compose worker with `-B` | Whatever `SUPABASE_URL` + service role the **worker host** has (today: local Supabase when that stack is up) | Full live wrapper: asserted-false signature (registry + >3), DISCOVERED diff, L2↔L3 drift, lexicon vs verdict | Exit code on the task result only — **no Slack/email/pager**. On success writes `docs/item12_last_live_audit.json`; age exposed on `GET /health` as `ike2_live_audit`. |
| **GitHub Actions** `.github/workflows/ike2-nightly-audits.yml` (06:00 UTC + dispatch) | Hosted DB **only if** repo secrets `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` are set | Always: offline pytest. Live audits **skipped** when secrets empty — job summary **“Live audit: SKIPPED — no hosted DB”** + `::notice`. Set repo variable `REQUIRE_LIVE_AUDIT=1` to **fail** the job when secrets are missing. | Actions summary/notice; artifact when live ran. Nobody is paged. |

**Honest summary:** until a hosted read-only audit DB exists and secrets are wired, the live guard is local-machine uptime (Beat) or an **explicit skip** (Actions). Offline CI still catches registry / trust / view-parity without Supabase.

**Pre-pilot dependency (Items 14 + 29):** hosted read-only audit database + failure routing (Slack/email/pager). Tracked there — not closable from Item 12 alone.

## Ghee asserted-false recurrence — named writer

**Original pollution writer:** the Item 11 ontology seed/inject pass that wrote a **full boolean `asserted_flags` block** (including false-valued names) onto ~1,698 `source=ontology` rows (repaired 2026-10-05; see `item11_asserted_flags_live_repair.md`). That path is `scripts/seed_ike2_ontology.py` → `bulk_inject(..., "ontology")` with pre-true-only rows.

**Why it came back on `ghee`:** `reconcile()` **never drops** keys from `asserted_flags` — it only unions. A one-shot strip repair is not durable against any later merge that re-attaches asserted names, and IFCT bulk inject later OR-ed `plant_origin` onto the ontology `ghee` head (`item37` / `item11_phase1_flag_changes.md`) without clearing residual asserted-false keys. The durable guards are validate’s `asserted_flags_false_pollution` choke point and Item 12’s asserted-false signature audit (which caught this recurrence).
