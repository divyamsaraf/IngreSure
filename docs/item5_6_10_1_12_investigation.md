# Targeted investigation: Items 5, 6, 10.1, 12

**Date:** 2026-09-17  
**Method:** Report only — exact paths against live code. Does not re-derive Phase 2 wholesale; cites it where still accurate.  
**Standard:** Same evidentiary bar as `docs/system_state_audit.md` / `docs/phase2_gap_analysis.md`.

---

## 1. Item 5 — Human review workflow (“force-human submit”)

### Verdict

**“Force-human” means: never set `auto=True` on the ledger row, and require `reviewer_id` + `approval_rationale` at commit time.**  
The only human action surface today is the **interactive terminal CLI** (`input()` in `run_induction.py`). There is **no** web UI, **no** durable pending review queue, and **no** async “someone reviews later” step. Accept in the CLI **immediately** writes L2 (ontology / variant aliases) and appends a promoted ledger row.

### Exact path (induction accept)

```
unknown_ingredients_log.json
  → scripts/run_induction.py (build_candidates)
  → dry-run: print candidates, exit
  → --no-dry-run: for each candidate, input("Accept …? [y/N/q]")
       y → submit_induced(..., decision="accept", reviewer_id=..., approval_rationale="induction accept")
       N → submit_induced(..., decision="reject") → ledger.append_non_promotable(...)
       q → break
```

**`submit_induced`** (`backend/core/knowledge/ike2/coverage_os/induction/submit.py`):

1. `build_promote_entry(cand)` → variant_alias or ontology_row payload (+ induction provenance).
2. If `decision != "accept"` → `PromoteLedger.append_non_promotable(..., rule_id="induction_reviewer_reject")` — **no** L2 write.
3. If accept → `decide_promote(...)` (`hybrid_gate.py`). If `gate.action == "rejected"` → return `None` (nothing written).
4. Comment at L85–86: *“Structural force-human: never auto=True, even if gate.action == auto_promote.”*
5. `commit_promotion(..., auto=False, reviewer_id=..., approval_rationale=...)`  
   (`promote_writer.py` L229–258):
   - **First** `apply_promotion` → mutates `ontology.json` and/or `variant_aliases.json` on disk.
   - **Then** `ledger.append_promoted(..., auto=False, ...)`.

**`PromoteLedger.append_promoted`** (`promote_ledger.py` L55–86): if `auto` is false, **requires** non-empty `reviewer_id` and `approval_rationale` or raises `ValueError`. Ledger row stores `auto: false`, `reviewer_id`, `approval_rationale`, `kind: "promoted"`.

### What “force-human” is *not*

| Mechanism | Exists? |
|-----------|---------|
| Web / admin UI for review | **No** (no matches under `frontend/` for induction/promote/reviewer) |
| HTTP review API | **No** (`submit_induced` callers: CLI + tests only) |
| Pending queue table / JSONL kind awaiting later approval | **No** — accept commits immediately; reject writes `non_promotable` immediately |
| Async notification to a reviewer | **No** |
| Separate post-submit human gate | **No** — the human **is** the CLI operator at `input()` time |

### Other “human-stamped” path (not interactive)

`backend/scripts/seed_neutralize_roles.py` calls `commit_promotion(..., auto=False, reviewer_id=…)` in batch with a fixed reviewer string (Phase 2a role seed). That is **pre-approved batch stamping**, not a review workflow.

### Call-site inventory for `submit_induced`

| Caller | Role |
|--------|------|
| `backend/scripts/run_induction.py` | **Only production operator path** |
| `backend/tests/ike2/coverage_os/induction/test_submit.py` | Unit |
| `backend/tests/ike2/coverage_os/induction/test_phase2b_exit.py` | Exit criteria |

`auto_lane_guards.py` (`select_sample_audit`, `log_volume_spike_if_needed`) is **log/stub only** — docstring: “Phase 1 is log/stub only — no daemon.” Not a review UI.

---

## 2. Item 6 — LLM/ML vs induction heuristics

### Verdict

**Induction (`cluster` / `propose_alias` / `propose_role`) is purely algorithmic / heuristic.** No Ollama, embeddings, or other LLM calls in `coverage_os/induction/` (grep clean). Alias proposal is deterministic folds only — comment in `propose_alias.py` L30: *“Deterministic folds only — head + single token drop. No fuzzy.”*

### Induction evidence

| Module | Mechanism |
|--------|-----------|
| `induction/cluster.py` | Load unknown-log JSON → frequency filter → `classify_miss_class(raw)` (rule heuristics) |
| `induction/propose_alias.py` | `simple_commodity_head` + token drop against ontology index; require **exactly one** target |
| `induction/propose_role.py` | Ontology row role heuristics / `ROLE_ENUM` — no network |

### Every LLM call site in `backend/` (Ollama only; no OpenAI/Anthropic in requirements)

| Site | Path | When |
|------|------|------|
| Intent fallback | `core/llm_intent.py` → `_call_ollama` → `requests.post(get_ollama_url(), …)` | Chat: after rule-based intent yields weak/general case (`app.py` uses when `llm_enabled()`) |
| Greeting / general / profile compose | `core/llm_response.py` → `_call_ollama` | Chat stream templates fallback |
| Verdict explanation prose | `core/llm_response.py` → `llm_compose_verdict_explanation` | `app.py` ~L691–708 — **optional overlay** on template explanation after compliance already ran |
| Enrichment origin classify | `core/knowledge/llm_classify.py` → `requests.post(get_ollama_url(), …)` | Worker / one-shot enrich when API confidence medium |
| Regional English-name hint | `core/external_apis/fetcher.py` → `_resolve_to_english_llm` | After Wikidata miss |
| Warmup ping | `app.py` lifespan ~L133–140 | Startup only if `llm_enabled()` |
| Live ping (tests/scripts) | `tests/integration_test.py`; `scripts/verify_flow_and_llm.py` | Non-serve |

**Config:** `core/config.py` — `llm_enabled()`, `get_ollama_url()`, `get_ollama_model()`, timeouts. Default URL `http://localhost:11434/api/generate`.

**Not found:** embeddings / vector matching / anomaly-detection ML; no `sentry`/`openai`/`torch`/`transformers` in `backend/requirements.txt`. Restaurant `embeddings` table was dropped (prior audit). Stale docs claiming scan LLM normalizer are **not** backed by code (no `llm_normalizer.py`).

**Compliance path:** never calls Ollama. LLM is UX / enrichment-assist only; fail → templates / skip (`LLM_ENABLED=false` or timeout → `None`).

---

## 3. Item 10.1 — Multi-restriction combination

### Verdict

**Already evaluates all active restrictions together.** Nested loop over every resolved ingredient × every rule whose `rule.restriction` is in `profile.restrictions`. Headline = `aggregate(verdicts)` = `max(...)` (most severe). **Not** one-restriction-at-a-time.

### Code

`backend/core/knowledge/ike2/compliance.py` `evaluate()` L362–418:

```text
for r in resolved:
    for rule in rules:
        if rule.restriction not in restrictions: continue
        … _verdict_for(r, rule, severity) …
        breakdown[(canonical, restriction)] = max(prev, new)
        verdicts.append(verdict)
for restriction in restrictions:
    if restriction not in covered:
        verdicts.append(UNCERTAIN)   # fail-closed uncovered
return ComplianceResult(aggregate(verdicts), …)
```

`backend/core/knowledge/ike2/verdict.py`:

```text
SAFE=0 < UNCERTAIN=1 < WARN=2 < FAIL=3
aggregate = max(verdicts)  # empty → UNCERTAIN
```

**Profile construction:** `bridge._profile_from_restriction_ids` → `{rid: "medical" for rid in restriction_ids}` — all IDs active simultaneously. Bridge `user_profile_model_to_restriction_ids` unions primary diet + allergens + lifestyle.

### Concrete example trace

**Profile:** `restriction_ids = ["vegan", "peanut_allergy"]`  
→ `profile.restrictions = {"vegan": "medical", "peanut_allergy": "medical"}`.

**Ingredients (resolved flags sketch):**

| Atom | Flags (illustrative) | vegan rule (`animal_origin`) | peanut_allergy rule (`peanut_source`) |
|------|----------------------|------------------------------|----------------------------------------|
| milk | `animal_origin=True` | **FAIL** | SAFE (no peanut) |
| peanut | `peanut_source=True`, plant | SAFE for vegan | **FAIL** |
| water | clean | SAFE | SAFE |

**Per-cell contributions to `verdicts`:**  
milk×vegan FAIL, milk×peanut SAFE, peanut×vegan SAFE, peanut×peanut FAIL, water×vegan SAFE, water×peanut SAFE.

**`aggregate`:** `max(FAIL, SAFE, …) = FAIL` → external **NOT_SAFE**.

**Uncovered guard (tested):** `test_uncovered_restriction_is_never_safe` in `tests/ike2/test_compliance.py` — vegan SAFE + peanut on profile with **no** peanut rule → inject UNCERTAIN so headline cannot stay SAFE.

**Fixture:** `tests/fixtures/labels/stress_label.py` profile `vegan_peanut` with `["vegan", "peanut_allergy"]`. Design doc still lists `test_multi_restriction_aggregates_most_severe` — that **named** test was not found (aggregate behavior covered indirectly).

### Gaps (logic vs productization)

- Combination **engine** works (AND + most-severe).
- Still missing: contradictory-diet policy, preserving preference vs medical severity on the API path, per-restriction HTTP breakdown, named multi-restriction golden — as already noted in remapped Phase 2 §10.1.

---

## 4. Item 12 — Observability

### Verdict

**Partial, mostly unstructured.** No Sentry / OpenTelemetry / Prometheus / Datadog / structlog in `backend/requirements.txt` or app wiring. What exists: stdlib `logging`, append-only `request_history`, legacy `enrichment_metrics`, shallow `/health`, CI safety gates, Coverage OS WARNING stub.

### What exists

| Surface | Path | Nature |
|---------|------|--------|
| Default logging | `app.py` L37 `logging.basicConfig(level=logging.INFO)`; widespread `logging.getLogger(__name__)` | Unstructured text; no JSON schema / request-id middleware found |
| Request history DB | `core/request_history.py` → `public.request_history`; called from `app.py` for `/profile` and `/chat/grocery` | Append-only analytics; toggle `REQUEST_HISTORY_ENABLED`; **not** used by `/api/v1/*` |
| Enrichment metrics | `ingredient_db.record_resolution_metric` → `enrichment_metrics`; caller `canonicalizer.py` only | Legacy resolve path daily counters |
| Health | `GET /health` → `{status, service, ingredient_audit_emitter}` | Liveness only — no Supabase/Redis/LLM probes |
| Named log events | e.g. evaluate failure logs in `v1_evaluate.py`; `auto_lane_guards.log_volume_spike_if_needed` → `log.warning(...)` | Log lines only — no alert routing |
| `miss_class` | `ike2/miss_class.py` on L5 resolve | Engine tag for offline promote; **not** exported to metrics/APM |
| `ike2_shadow_diffs` | Writer retained; **no** serve-path caller post–Item 16 | Historical / future cutover infra |
| CI quality gates | `.github/workflows/ci.yml` | Pre-merge monitoring ≠ runtime |

### What does not exist

- Sentry (or any error-tracking DSN / SDK)
- Prometheus `/metrics`, OTel exporters, StatsD
- Alerting config (PagerDuty/Slack webhooks) in-repo
- Structured JSON access logs
- Dashboards-as-code

`print(...)` appears in operator CLIs (e.g. `bulk_inject.py`, `run_induction.py`) — not the FastAPI serve path’s primary telemetry.

---

## Open questions

**All closed (2026-09-17).** Answers recorded in `docs/phase2_gap_analysis.md` §1 (Items 5 / 6 / 10.1 / 12 subsection). Summary:

| Q | Answer |
|---|--------|
| 5 / CLI end state | Yes — CLI + force-human sufficient for now |
| 5 / non-induction pending | No — same immediate-commit pattern |
| 6 / scope | Chat + enrichment Ollama only; induction out of ML scope |
| 6 / stale docs | Retire as part of Item 6 |
| 10.1 / rewrite evaluate | No — policy + golden + API breakdown only |
| 10.1 / contradictory diets | Reject at profile-set |
| 12 / approach | Productize stores + Sentry; defer OTel/Prometheus |
| 12 / alert set | Document now: false_safe_regression>0, /health, elevated /api/v1 5xx |
