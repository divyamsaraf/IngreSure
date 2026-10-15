# Batch 1 — Prompt 1 investigation report

**Date:** 2026-09-17  
**Scope:** Item 4 / 4.1 / 3.1 Prompt 1 only — investigation, no code changes.  
**Also recorded in:** each spec’s stage log.

---

## Item 4 Prompt 1 — Caller inventory

### Production (non-test) callers

| Symbol | Caller | Behavior vs human-sign-off contract |
|--------|--------|-------------------------------------|
| `submit_induced` | `backend/scripts/run_induction.py` | Interactive y/N → accept/reject. Accept always `commit_promotion(..., auto=False, reviewer_id=…)` via `submit.py` L85–96. |
| `decide_promote` + `commit_promotion` | `backend/scripts/seed_neutralize_roles.py` | Calls gate; on `rejected` skips; on **`auto_promote` or `human_approval`** always `commit_promotion(..., auto=False, reviewer_id=…, approval_rationale="phase2a role seed")` L110–120. |
| `decide_promote` | inside `submit_induced` only (prod) | Used to get `rule_id` / reject short-circuit; never flips `auto=True`. |

### Test-only callers

`tests/ike2/coverage_os/**` — `test_submit.py`, `test_phase2b_exit.py`, `test_phase2a_*.py`, `test_phase1_integration.py`, `test_hybrid_gate*.py`, `test_promote_writer*.py`, `test_safety_class.py`.

### Violations?

**None found.** No production path commits with `auto=True` after `human_approval`. No production path drops `human_approval` silently without either commit (seed) or reject/skip-only-on-`rejected` (induction).

**Course correction:** Prompt 5 has nothing to “fix” for a violating caller — treat as confirmation pass; proceed Prompts 2–4 (docs, L3 no-op freeze, force-human guardrail test).

---

## Item 4.1 Prompt 1 — Is `updated_at` a trust-refresh signal?

### Verdict: **No — add `trust_refreshed_at`**

| Evidence | Path |
|----------|------|
| Column exists with default `now()` | `supabase/migrations/20260616000000_ike2_schema.sql` L65 |
| No auto-bump trigger | Grep of `supabase/migrations` — no `BEFORE UPDATE` / `set_updated_at` for `ike2_*` |
| Reconcile updates omit `updated_at` | `bulk_inject.py` `SupabaseWriter.update_group` L173–190 — sets flags + `knowledge_state` only |
| Coverage OS promote ≠ IKE-2 DB clock | `promote_writer.py` mutates `ontology.json` / `variant_aliases.json` (L2), not `ike2_ingredient_groups` |

So `updated_at` often remains **insert-time** even after trust-relevant flag merges. Using it as TTL clock would under-decay (rows look “fresh”) or, if something else bumps it later without meaning trust refresh, over-decay.

**Next prompt:** Proceed Prompt 2 as written (migration + explicit refresh on inject/reconcile). Backfill `COALESCE(updated_at, created_at)` with eyes open that many values are insert-time.

---

## Item 3.1 Prompt 1 — Bare enzymes + Option A vs B

### How bare `enzymes` is represented today

| Layer | Representation |
|-------|----------------|
| Truth anchor | `_add_compound(["enzymes", "enzyme"], "enzymes")` → `verdict_cap="WARN"`, `knowledge_state="VERIFIED"`, **empty origin flags** (`truth_anchor.py` L36–39, L225) |
| Ontology L2 | No canonical `enzymes` row (only `enzyme-treated starches`) |
| Named animal enzymes | `rennet` / `animal rennet` / `pepsin` / etc. use **`animal_origin=True`** (generic), not an enzyme-specific flag |
| Microbial rennet / chymosin | No ontology rows; no anchors found |

Compliance already respects `verdict_cap` (`compliance.py` ~L307) so bare enzymes cannot firm-SAFE — but subtype (animal vs microbial) is not modeled.

### Recommendation: **Option A** (booleans)

Add `enzyme_animal_source` (and optionally `enzyme_microbial_source`) as boolean group flags + RULE_SEED fields.

| Why A | Why not B (alone) |
|-------|-------------------|
| Matches existing `RULE_SEED` `field` × bool pattern (`rules.py`) | Text enum needs new operator/path in rule matching |
| Fits Coverage OS `is_animalish` / human_approval predicates once set | Mutually exclusive enum is nicer semantically but higher glue cost |
| Can CHECK-imply `animal_origin` when `enzyme_animal_source` (same spirit as `egg_implies_animal`) | Can revisit enum later if needed |

Keep bare `enzymes` as compound `verdict_cap=WARN` until subtype is known.

### Cross-check → Item 4 (not a sequencing dependency)

If 3.1 work discovers a **new** uncertain-origin enzyme identity that needs promoting into L2/IKE-2, route it through Coverage OS `decide_promote` → immediate-commit with reviewer fields (animalish → `human_approval`). Do **not** add a side door.

**Diets that should grow rules (for Prompt 2):** vegan, vegetarian, lacto/ovo variants, Jain — animal enzyme FAIL via `enzyme_animal_source` and/or existing `animal_origin` implication; unknown enzyme stays fail-closed via `verdict_cap` / UNCERTAIN.

---

## What this means for next prompts

| Spec | Next step | Straight or course-correct? |
|------|-----------|------------------------------|
| **4** | Prompts 2–4 (docs, L3 no-op test, auto=False guard) | **Straight** — Prompt 5 N/A (no violation) |
| **4.1** | Prompt 2 (`trust_refreshed_at`) | **Confirmed necessary** (not optional) |
| **3.1** | Prompt 2 schema + RULE_SEED for Option A | **Straight** with Option A locked |

Batch 2 specs still wait until some of this is implemented.
