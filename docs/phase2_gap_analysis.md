# IngreSure — Phase 2 Gap Analysis (Items 3–14)

**Date:** 2026-09-17 (remapped 2026-09-17 evening)  
**Method:** Investigation only. Builds on `docs/system_state_audit.md`.  
**Authority:** Architecture tracker Master Task List titles win. An earlier draft used reconstructed working titles that **do not match** the tracker — see §0.

**Audit delta vs `docs/system_state_audit.md` (2026-08-06):** Item 16 Prompt 7 — `ComplianceEngine` deleted; `IKE2_MODE` retired; `/api/v1/evaluate-*` is IKE-2-only.

---

## 0. Tracker ID correspondence (mandatory)

Cursor’s first pass used **working titles**. Do **not** apply those sections item-for-item onto the tracker. Honest map:

| Tracker item (authoritative) | What the first pass actually covered | How to use that evidence |
|------------------------------|--------------------------------------|---------------------------|
| **3** — Core schema & versioning | Absorbed into Items 1/2 findings (schema already exists) | Effectively answered — see Items 1/2 specs |
| **3.1** — Framework sub-variants | Their “3.1” (fermentation/enzyme/fungal) | **Matches** — §3.1 below |
| **4** — Trust & Promotion Engine | Their “3” (rules) + “4” (Coverage OS) combined | **Matches** — §4 below (spans both) |
| **4.1** — Temporal confidence decay | Their “4.1” was Phase 2a role seed (wrong) | **Confirmed clean gap** — §4.1; Phase 2a/2b stay under Item **4** |
| **5** — Human review workflow | Their “5” was commodity head/L3 (wrong) | **Retargeted** — §5 (2026-09-17 follow-up) |
| **6** — LLM/ML pipeline | Their “6” was `lifecycle.py` (wrong) | **Retargeted** — §6 (2026-09-17 follow-up). `lifecycle.py` → Item **33** |
| **7** — Testing & QA | Their “7” | **Matches** — §7 |
| **8** — Service boundary | Partial signal from their “8” | **Partial** — §8 |
| **9** — B2B API & productization | Their “8, 9, 10, 10.1” combined | **Matches well** — §9 |
| **10** — Consumer app integration | Their “10” was B2B schema (wrong) | **Known-fine** from earlier work — §10 stub |
| **10.1** — Multi-restriction combination | Their “10.1” was API-key auth (wrong) | **Retargeted** — §10.1 (2026-09-17 follow-up) |
| **11** — Multi-region/i18n | Not this pass | Tracked separately — §11 stub |
| **12** — Observability & monitoring | Their “12” was Redis caching (wrong) | **Retargeted** — §12 (2026-09-17 follow-up). Redis → deferred / Item **33** notes |
| **13** — Security/privacy/compliance | Their “13” (RLS) | **Matches, partial** — §13 |
| **14** — Infra/deployment | Their “14” | **Matches** — §14 |

**Orphaned first-pass topics (keep evidence, refile):**

| First-pass label | Refile under |
|------------------|--------------|
| Commodity head / `mirror_l3_inject` / identity expansion | Item **4** (Coverage OS / promote) + decision: L3 mirror stays documented no-op |
| `lifecycle.py` / dual knowledge_state | Item **33** (dual resolve engines) — delete after legacy resolve retirement |
| Redis resolution cache | Not urgent for IKE-2; revisit on horizontal scale (decision #12) |
| Celery Beat / enrichment schedule | Items **18** + **23** (Beat → `ike2_unknown_queue`) |

---

## 1. Decisions recorded (open questions answered)

### Trust / knowledge

| # | Decision |
|---|----------|
| 4.1 naming | Tracker **4.1** = temporal confidence decay (nothing exists). Phase 2a role seed + 2b induction file under Item **4**. |
| 14 missing restriction ids | **Out of scope** for now (nutrition/lifestyle ≠ safety-critical differentiator). Same deferral class as Item **30** (Buddhist/SDA). |
| Koji/miso/tamari/natto under Jain | **Depends** acceptable now (safe direction); **not** permanent target — bounded P2 backlog, truth-anchor pattern like tempeh. |
| L3 mirror | Stay **documented no-op**. No write path without a reader. |
| `lifecycle.py` | **Delete**, do not unify — **only after** legacy resolve retirement (Item **33**). |
| Item 7 bar | Expand never-SAFE corpus + **DB-rule-parity goldens now**; defer fuzz/property + continuous soak-in-CI to P2. |
| Item 2 L5 queue | **Option B** — explicit deferral; fix lying comments; Item **18** owns the write path in one place. |

### Items 5 / 6 / 10.1 / 12 (closed 2026-09-17 evening)

| Item | Decision |
|------|----------|
| **5** end state | CLI + force-human immediate-commit is **done enough**. No UI/API/pending queue until second reviewer or real bottleneck. |
| **5** non-induction `human_approval` | Same pattern: immediate-commit with `reviewer_id` — **no** separate pending queue. One review mechanism everywhere. |
| **5** unknown triage | Stays under Item **18**, not 5. |
| **5** reviewer identity | Single configured `reviewer_id` fine. |
| **6** approach | Harden existing Ollama touchpoints; **no** pipeline abstraction. Preserve: compliance never calls LLM. |
| **6** enrichment LLM | **In scope.** Induction heuristics **out of scope** (confirmed non-ML). |
| **6** stale docs | Retire scan-LLM claims in `AI_ENGINE.md` / `SERVICES_OVERVIEW.md` as part of Item 6. |
| **6** `LLM_ENABLED` default | **On** in production (fallback already safe). |
| **10.1** evaluate() | AND + most-restrictive **confirmed correct — do not rewrite.** Work = policy + golden + API breakdown. |
| **10.1** contradictory diets | **Reject at profile-set time** (warn/pick one); not silent AND. |
| **10.1** severity | Preserve medical vs preference through to API (no flatten-all-medical). |
| **10.1** HTTP | Per-restriction breakdown on evaluate — alongside Item **9** schema. |
| **10.1** acceptance | Named golden: vegan + peanut + gluten. |
| **12** approach | Productize `request_history` / `miss_class`; add **Sentry** now; defer OTel/Prometheus. |
| **12** `request_history` | Expand to `/api/v1/*`. |
| **12** `miss_class` | Persist (already computed). |
| **12** alerts | Document target set now, wire later: `false_safe_regression > 0`, `/health` failures, elevated 5xx on `/api/v1`. |

**Zero open questions remain** for Items 3.1, 4, 4.1, 5, 6, 7, 9, 10.1, 12, 13, 14.

---

## Item 3 — Core schema & versioning

**Status: already exists** (answered via Items 1 & 2 revision)

Canonical IKE-2 schema is live: `ike2_ingredient_groups`, `ike2_ingredients`, `ike2_aliases`, `ike2_alias_disambiguation`, `ike2_restriction_rules`, `ike2_unknown_queue`, `ike2_group_merges`, `ike2_knowledge_state` enum + CHECK implication system. See `docs/item1_item2_gap_report.md`, `supabase/migrations/20260616000000_ike2_schema.sql`. Remaining schema work is incremental (adapters, merges writers) under Items 1/2 — not a greenfield Item 3 build.

---

## Item 3.1 — Framework sub-variants (fermentation / enzyme / fungal)

**Status: partially exists**

| Capability | Evidence | Live? |
|------------|----------|-------|
| Jain `fungal` FAIL | `rules.py` RULE_SEED; migration seeds | Yes |
| Jain `fermented` WARN | `rules.py`; `test_jain_fermented_warns_not_fails` | Yes |
| Name→fungal derive | `flag_derive.py` (`yeast`, `tempeh`, `koji`, mushrooms, …) | Yes |
| Truth anchors | `truth_anchor.py` — yeast family `fungal=True`; bare `enzymes` → `verdict_cap=WARN` | Partial |
| Regression gate | `test_commodity_coverage_gate.py` yeast/Jain never firm SAFE | Yes |
| Enzyme origin subtypes | No microbial-vs-animal enzyme typing | **Missing** |
| Koji/miso/tamari/natto | Often Depends/UNCERTAIN, not firm Avoid | Partial — **Depends OK now**; firm Avoid = P2 backlog |

**Gap:** Yeast/fungal Jain FAIL closed; fermentation/enzyme **sub-variant** taxonomy incomplete. Spec Item 3.1 around remaining taxonomy + P2 backlog for common fermented foods.

---

## Item 4 — Trust & Promotion Engine

**Status: partially exists** — combines rule engine + Coverage OS (first-pass “3” + “4”)

### 4a. Restriction / diet rules (IKE-2)

| Layer | Path |
|-------|------|
| Seed SoT | `backend/core/knowledge/ike2/rules.py` — `RULE_SEED` (52), `SUPPORTED_RESTRICTIONS` (31), `load_rules()` |
| Evaluator | `compliance.py` — `evaluate()` |
| DB | `ike2_restriction_rules` + seed/delta migrations |
| Tests | `tests/ike2/test_rules.py`, `test_compliance.py` |

**Decision:** 14 nutrition/lifestyle ids in `restrictions.json` but not in IKE-2 → **out of scope** (not Item 4 work).

### 4b. Coverage OS / promote / neutralize

| Module | Stub vs live |
|--------|----------------|
| `hybrid_gate.py`, `promote_ledger.py`, `promote_writer.py` (L2) | **Live** |
| `neutralize.py` (chat via `compound_expansion.py`) | **Live** |
| `induction/` + `run_induction.py` | **Live library**; force-human submit |
| Phase 2a role seed (`seed_neutralize_roles.py`, 66-row ledger) | **Live** — files under Item **4**, not 4.1 |
| `auto_lane_guards.py` | **Stub** (log only) |
| `mirror_l3_inject` | **Stub** — **decision: stay documented no-op** |
| Continuous auto-promote / Beat | **Doesn't exist** |

### 4c. Commodity head / identity (formerly misfiled as “Item 5”)

`commodity_head.py`, `flag_derive.py`, `truth_anchor.py` — **live** and wired into resolve. Part of trust/coverage identity, not a separate human-review item.

**Gap for Item 4 specs:** productize trust+promote as one engine; automation still operator-CLI; L3 mirror no-op by decision.

---

## Item 4.1 — Temporal confidence decay

**Status: doesn't exist**

No code for time-based confidence decay, trust aging, or automatic `knowledge_state` demotion by age. Enum has `DEPRECATED` but nothing decays into it on a clock. Safe to spec as greenfield.

**Do not** confuse with Phase 2a role seed (that is Item **4**).

---

## Item 5 — Human review workflow

**Status: partially exists** *(retargeted investigation 2026-09-17)*

Human-approval **mechanics** for Coverage OS promote/induction are real. A productized **review workflow** (durable pending queue, admin UI, unknown triage) does **not**.

| Exists | Path |
|--------|------|
| Force-human submit | `coverage_os/induction/submit.py` — `submit_induced()` → `commit_promotion(..., auto=False, reviewer_id=…)` |
| Ledger enforcement | `promote_ledger.py` — `auto=False` requires reviewer + rationale |
| Gate decision enum | `hybrid_gate.py` — `human_approval` \| `auto_promote` \| `rejected` (not a queue) |
| Interactive CLI | `scripts/run_induction.py` — y/N accept |
| Tests | `tests/ike2/coverage_os/induction/test_submit.py` |

| Doesn't exist |
|---------------|
| Admin UI / review-queue API |
| Durable pending-proposals table/kind |
| `ike2_unknown_queue` triage UI (and no Python writes yet — Item 18) |
| `remediate_ike2_rejects.py` / staging→human-merge path |

**Reuse:** ~60–70% of trust/accountability primitives exist; remaining is queue + UI/API + triage glue.

**Open questions (Item 5):** **Closed** — CLI+force-human immediate-commit is end state; same pattern for non-induction `human_approval`; triage → Item 18; single `reviewer_id`. See §1.

---

## Item 6 — LLM/ML pipeline

**Status: done** (2026-10-07 — see `docs/item6_llm_pipeline_spec.md`; retargeted investigation 2026-09-17)

Production-wired **Ollama** for chat UX + optional enrichment assist — **not** a unified ML pipeline. Compliance never calls LLM.

| Capability | Status | Paths |
|------------|--------|-------|
| Config gates | Exists | `config.py` — `llm_enabled()`, Ollama URL/model, timeouts; CI forces `LLM_ENABLED=false` |
| Rule intent (primary) | Exists | `intent_detector.py` |
| LLM intent fallback | Exists | `llm_intent.py` |
| Chat compose / verdict prose | Exists | `llm_response.py`, `response_composer.py`; template fallback |
| Enrichment classify / English LLM | Exists (optional) | `llm_classify.py`, `fetcher.py`, worker tasks |
| Profile-update LLM | Dead | `llm_compose_profile_update` never called |
| Scan/OCR LLM | Doesn't exist | Stale docs only (`AI_ENGINE.md`, `SERVICES_OVERVIEW.md`) |
| Embeddings / `ml/` package | Doesn't exist | Restaurant embeddings dropped |

**Fail behavior:** LLM down → templates / skip enrichment assist; compliance unchanged.

**Open questions (Item 6):** **Closed** — see §1.

---

## Item 7 — Testing & QA

**Status: done** (2026-10-07 — see `docs/item7_testing_qa_spec.md`)

| Asset | Path | Role |
|-------|------|------|
| Exact-verdict corpus | `tests/ike2/golden/corpus.jsonl` (~62) | |
| Never-SAFE corpus | `must_never_be_safe.jsonl` (~112) | CI hard gate |
| Audit matrix | `audit_matrix.jsonl` (~18) | |
| Runner | `golden_runner.py` — uses **`seeded_rules()`**, not DB | |
| CI | `ci.yml` — never-SAFE + safety budget + shadow corpus | |

**Decision (Item 7 bar):** expand never-SAFE + add **DB-rule-parity goldens now**; defer fuzz/property + continuous soak-in-CI to P2.

---

## Item 8 — Service boundary

**Status: partially exists** (partial signal only)

| Exists | Gap |
|--------|-----|
| FastAPI app + `/api/v1` router + chat BFF boundary | Resolve and evaluate HTTP are IKE-2; evaluate response is still the legacy-shaped verdict |
| Frontend does not call `/api/v1/*` (B2C via BFF) | No crisp published service-boundary doc (which surfaces are internal vs product) |
| Worker isolated from FastAPI imports (by design comment) | Product resolve is IKE-2 (Item **33**). `IngredientRegistry` remains for ontology tests only. |

Spec should define: chat BFF = B2C; `/api/v1` = B2B product surface (Item 9); legacy resolve retirement (Item 33); worker/Beat as async boundary (18/23).

---

## Item 9 — B2B API & productization

**Status: partially exists** — richest findings (first-pass 8+9+10+10.1 auth/rate-limit combined)

### HTTP surface

| Route | Engine today |
|-------|--------------|
| `POST /api/v1/evaluate-compliance`, `evaluate-product` | **IKE-2** via `v1_evaluate.py` |
| `POST /api/v1/resolve-ingredient`, `GET /ingredient/{name}` | **IKE-2** via `map_ike2_to_resolved_response` (Item **33**) |
| Response shape | `ComplianceVerdict.to_dict()` — **no** `schema_version` |

### Rich assemble (library only)

`ike2/response.py` — `SCHEMA_VERSION = "ike2.v1"`; `assemble(..., mode="b2b"|"b2c")` — **no production HTTP caller**.

### Auth / rate limit

| Exists | Gap (decisions) |
|--------|-----------------|
| `rate_limit.py`, `B2B_API_KEYS`, tiers, `tenancy.resolve_caller` | Keys do **not** gate `/api/v1` → **require valid key, 401 in prod** |
| `rpm` parsed in key JSON | **Unused** → **wire to override tier limits** |
| Tenancy on `/profile` only | Not on `/api/v1` |

### Out of scope (decision)

- First-class B2C streaming API product (SSE/etc.) — keep custom text-stream.

**Spec Item 9:** mandatory keys + `assemble(b2b)`/`schema_version` on the wire + `rpm` override.

---

## Item 10 — Consumer app integration

**Status: already exists / known-fine** (not re-audited this pass)

Chat BFF + stream protocol + profile/anon-session already ship B2C. No Phase 2 blocker from this gap wave. Spec only if tracker still requires a formal close-out note.

---

## Item 10.1 — Multi-restriction combination

**Status: partially exists** *(retargeted investigation 2026-09-17)*

Engine already **ANDs** all active restrictions and aggregates with **most-severe** (`max`). Bridge/API accept multiple IDs. Missing: dedicated combination **policy**, named multi-restriction golden, severity fidelity, rich per-restriction API breakdown.

| Exists | Path |
|--------|------|
| `evaluate()` nested loop × all profile restrictions | `compliance.py` |
| Uncovered restriction → UNCERTAIN | same |
| Bridge unions diet + allergens + lifestyle | `user_profile_model_to_restriction_ids` |
| `restriction_ids: List[str]` on evaluate-compliance | `schemas.py` / `v1_evaluate` |

| Gaps |
|------|
| Bridge flattens every ID to `medical` severity |
| No contradictory-diet policy (vegan + pescatarian) |
| Design lists `test_multi_restriction_aggregates_most_severe` — **never implemented** |
| Evaluate HTTP lacks per-restriction status matrix |
| Attribution copy: diet-primary collapses multi-FAIL detail |

**Open questions (Item 10.1):** **Closed** — see §1.

---

## Item 11 — Multi-region / i18n

**Status: not investigated this pass** — already tracked separately.

Known fragments (do not treat as complete Item 11 audit): `ike2_alias_disambiguation`, regional name maps, Wikidata multi-language in fetcher. Spec when that track is scheduled.

---

## Item 12 — Observability & monitoring

**Status: partially exists** *(retargeted investigation 2026-09-17)*

| Surface | Status | Paths |
|---------|--------|-------|
| `request_history` | Exists (narrow) | Chat + profile only; **not** `/api/v1/*` |
| `enrichment_metrics` | Writer gone | The resolve metrics writer was deleted in Item 33 Prompt 5, so IKE-2 resolution telemetry starts from zero. Nothing reads the table (no script, dashboard, or endpoint). |
| Logging | Partial | Stdlib unstructured; no request IDs |
| `/health` | Partial | Liveness only; no dependency readiness |
| `miss_class` | Exists (engine) | Not persisted to ops telemetry |
| `ike2_shadow_diffs` | Historical / dormant | No serve-path writer post–Item 16 |
| CI safety gates | Exists | Pre-merge ≠ prod monitoring |
| Prometheus / OTel / Sentry / dashboards / alerts | **Doesn't exist** | Stub volume-spike log only |

**Open questions (Item 12):** **Closed** — see §1.

---

## Item 13 — Security / privacy / compliance

**Status: partially exists**

### RLS inventory

**RLS ON + policies:** `public.users` only (`users_select_own`, `users_update_own`).

**RLS ON + NO policies** (deny anon/authenticated; `service_role` bypasses):  
`ingredient_groups`, `ingredients`, `ingredient_aliases`, `unknown_ingredients`, `enrichment_metrics`, `request_history`, and all living `ike2_*` public tables (`ike2_ingredient_groups` … `ike2_group_merges`).

**Decision:** enable RLS + no-policies on **`ike2_staging.*`** for consistency.

### App-layer

Rate limits, CORS production guard, input sanitize, anon session — present. Tenancy narrow (profile). No multi-org RLS on knowledge tables. Profiles still file-backed.

---

## Item 14 — Infra / deployment

**Status: partially exists**

| Exists | Gap |
|--------|-----|
| `docker-compose.yml` (backend/frontend; redis+worker via `profile: cache`) | No Beat, no Supabase, no Caddy in compose |
| `deploy/Caddyfile.example` | Example only |
| `.github/workflows/ci.yml` | No CD |
| `DEPLOY.md` / OCI docs / `vercel.json` | Manual topology |

**Decision:** prod-like compose profile eventually, **not urgent**.

**Related:** Celery Beat → Item **23** with Item **18** (`ike2_unknown_queue`), not a second scheduler.

**Pre-pilot (with Item 29):** hosted **read-only** audit Supabase + wire `SUPABASE_*` into `.github/workflows/ike2-nightly-audits.yml`; failure routing (Slack/email/pager) when Item 12 `--fail-on-findings` exits non-zero. Until then Actions live audit is an explicit skip (`REQUIRE_LIVE_AUDIT=1` fails closed). Age of last successful live audit: `GET /health` → `ike2_live_audit` / `docs/item12_last_live_audit.json`.

---

## Item 33 — Dual resolve engines (new tracked priority)

**Status: core complete (2026-09-28)** — Prompts 1–6 done. Spec: `docs/item33_dual_resolve_engines.md`. Prompt 7 deferred: `IngredientRegistry` and unused `record_resolution_metric` stay. Hand-vs-catalog disagreements are guarded by `tests/ike2/test_hand_catalog_agreement.py`.

| Path | Engine (as of 2026-09-27) |
|------|--------|
| Chat + `/api/v1/evaluate-*` | IKE-2 resolver + compliance |
| `/api/v1/resolve-ingredient`, `GET /ingredient/{name}` | **IKE-2** resolve + `map_ike2_to_resolved_response` |
| Worker enrichment | **IKE-2** `ike2_unknown_queue` (Items 18+23) |
| Legacy `unknown_ingredients` | No longer written by resolve or `log_unknown` (Prompt 4). Safe to truncate. |
| `lifecycle.py` + Redis resolve cache | **Deleted** (Prompt 5). Compose Redis remains the Celery broker. |

**Also landed with this item (not Prompt 5):** cache-seed trust merge; catalog checker narrow list (E626/E630/E631 known hits); l-cysteine / cysteine / E920 / E910 converged to one vegan UNCERTAIN. Soy lecithin/E322 left as-is. Hand-vs-catalog disagreement on `animal_origin`, `verdict_cap`, and `uncertainty_flags` is a permanent test.

---

## Consolidated open questions

**All closed (2026-09-17).** Answers live in §1 (including Items 5 / 6 / 10.1 / 12 subsection). Spec-writing may proceed for: **3.1, 4, 4.1, 5, 6, 7, 9, 10.1, 12, 13, 14**. Separate tracks: **8** (thin, after 9/33), **33**, **11**, **18/23**, **29**.

---

## Appendix — First-pass section archive map

If you need the raw first-pass prose, it lived under wrong IDs in git history of this file (2026-09-17 afternoon). Evidence was **refiled**, not discarded: rules+Coverage OS → Item 4; fermentation → 3.1; golden → 7; B2B HTTP/auth → 9; RLS → 13; deploy → 14; lifecycle/Redis/dual-resolve → Item 33 / decisions.
