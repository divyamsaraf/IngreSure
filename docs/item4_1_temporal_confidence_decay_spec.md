# IngreSure — Build Specification: Item 4.1
## Temporal confidence decay

**Status:** Done (batch 1) — policy + CLI + compliance golden.  
**Companion:** `docs/phase2_gap_analysis.md` § Item 4.1 · `supabase/migrations/20260918000000_ike2_trust_refreshed_at.sql` · `core/knowledge/ike2/decay.py` · `scripts/ike2_decay_knowledge.py` · Item **4** (must not confuse with Phase 2a role seed) · tracker row **4.1**

---

## 0. How to use this document

Item **4.1** is **temporal confidence decay** — aging of trust over time — **not** Coverage OS Phase 2a/2b (those file under Item **4**). No decay job, TTL policy, or automatic `knowledge_state` demotion exists today. Spec carefully; implement narrowly.

Keep this at `docs/item4_1_temporal_confidence_decay_spec.md`.

---

## 1. Current state (confirmed — act on this)

| Exists | Path / note |
|--------|-------------|
| Enum | `ike2_knowledge_state`: `UNCLASSIFIED \| DISCOVERED \| AUTO_CLASSIFIED \| VERIFIED \| LOCKED \| DEPRECATED` |
| Timestamps | `ike2_ingredient_groups.created_at`, `updated_at` (no dedicated `verified_at` / `last_trusted_at`) |
| Rule gating | `compliance.py` / rules use `min_knowledge_state` + `_KS_RANK` |
| `DEPRECATED` | Filtered from alias resolution view; **nothing** auto-transitions into it by age |
| LOCKED | E-number catalog path; must **not** decay |

**Does not exist:** decay policy config, batch job, Beat schedule for decay, tests for age-based demotion.

---

## 2. Purpose

Prevent stale auto-classified / verified knowledge from indefinitely authorizing firm SAFE when evidence has not been refreshed — fail-closed over time without manual archaeology of every row.

---

## 3. Scope

### In scope

- Define a **small, explicit decay policy** (states, TTLs, floors).
- Add a durable timestamp for “last trust event” if `updated_at` is too noisy (prefer additive column `trust_refreshed_at`, defaulting from `updated_at` / `created_at` on backfill).
- Offline / operator CLI (and optionally later Beat) that demotes eligible rows one step down the trust ladder.
- Tests for: LOCKED never decays; VERIFIED → lower state after TTL; already-low states have defined floors; decay never raises trust; compliance after decay cannot invent SAFE from demoted rows when rules require higher `min_knowledge_state`.

### Explicitly out of scope

- Real-time per-request decay inside `resolve()` (keep offline/batch — hot path stays simple).
- Auto-promote / Coverage OS daemon (Item 4).
- Deleting rows; use state transitions only.
- Decaying legacy `ingredient_groups` (IKE-2 tables only).
- Item 33 / `lifecycle.py` unification.

---

## 4. Target design

### 4.1 Ladder (decay only moves **down**)

```
LOCKED          → never decays (catalog / human-locked)
VERIFIED        → AUTO_CLASSIFIED  after T_verified (default proposal: 180d)
AUTO_CLASSIFIED → DISCOVERED       after T_auto     (default proposal: 90d)
DISCOVERED      → UNCLASSIFIED     after T_disc     (default proposal: 365d)  [optional; may no-op in v1]
UNCLASSIFIED    → no further decay
DEPRECATED      → terminal for resolve (manual or merge supersession — not age-driven in v1)
```

**v1 recommendation:** implement VERIFIED→AUTO_CLASSIFIED and AUTO_CLASSIFIED→DISCOVERED only. Leave DISCOVERED→UNCLASSIFIED and age→DEPRECATED as **documented P2** unless Prompt 1 finds a product need.

### 4.2 Clock source

- Prefer `trust_refreshed_at timestamptz` on `ike2_ingredient_groups`.
- Set/refresh on: bulk_inject reconcile that confirms state, explicit human verify, promote paths that touch the group (if any write IKE-2 L3 later — today L2-only promote does not).
- Backfill: `COALESCE(updated_at, created_at)`.
- Do **not** treat every unrelated column bump as refresh if a narrower trigger list is feasible.

### 4.3 Execution

```
scripts/ike2_decay_knowledge.py [--dry-run] [--as-of ISO]
  → select eligible groups
  → demote one step
  → bump version / updated_at
  → emit JSON summary (counts by transition)
```

Celery Beat wiring is **optional later** (coordinate with Item 23 only if desired); v1 = operator CLI + docs.

### 4.4 Compliance interaction

Decay does not invent new rules. It only changes `knowledge_state`, which interacts with the **SAFE floor** in `_verdict_for` (UNCLASSIFIED → UNCERTAIN, DISCOVERED → WARN on a clean pass).

**Decay never silences a still-true hazard FAIL.** A positive trigger (`peanut_source`, `gluten_source`, etc.) produces FAIL regardless of `knowledge_state` (Item **34**). Demoting VERIFIED→AUTO_CLASSIFIED or AUTO→DISCOVERED must not turn Avoid into Depends when the hazard flag remains true.

Golden coverage: clean-pass AUTO→DISCOVERED loses firm SAFE; triggered FAIL survives demotion.

---

## 5. Safety invariants

1. LOCKED never decays.
2. Decay never increases `knowledge_state` rank.
3. Dry-run default on CLI.
4. No hot-path decay inside resolve/evaluate.
5. TTLs are config/constants with tests — not magic scattered numbers.

---

## 6. Numbered build prompts for Cursor

**Prompt 1** — Investigate: is `updated_at` updated on every write path that should count as trust refresh? Recommend `trust_refreshed_at` yes/no with evidence. Do not implement yet.

**Prompt 2** — Migration: add `trust_refreshed_at` (if Prompt 1 says yes) + backfill; document TTL constants in `ike2/decay.py` (new module).

**Prompt 3** — Pure function `next_decay_state(state, age_days, policy) -> state | None` + unit tests (LOCKED, boundaries, floors).

**Prompt 4** — CLI `ike2_decay_knowledge.py` dry-run then apply; tests with fake clock / injected `as_of`.

**Prompt 5** — One compliance integration test: VERIFIED-gated rule → SAFE before decay; after demotion → not firm SAFE.

**Prompt 6** — Docs: link from Item 4 engine doc; stage log; tracker Notes. Do **not** schedule Beat unless separately authorized.

---

## 7. Success criteria

- [x] Policy + TTLs documented and tested.
- [x] LOCKED immune.
- [x] CLI dry-run default.
- [x] At least one compliance interaction test proves fail-closed after demotion.
- [x] No confusion with Phase 2a in tracker Notes.

### Stage log

| When | Notes |
|------|-------|
| 2026-09-17 | Greenfield draft; Phase 2a explicitly **not** this item. |
| 2026-09-17 | **Prompt 1 done — course correction:** `updated_at` unreliable; add `trust_refreshed_at`. |
| 2026-09-17 | **Prompt 2 done.** Migration `20260918000000_ike2_trust_refreshed_at.sql`. Module `ike2/decay.py` with TTL constants + **explicit L2/Coverage OS out-of-scope** (human-approved at promote). `bulk_inject.update_group` sets `trust_refreshed_at`. Tests: `test_decay_policy.py`. |
| 2026-09-17 | **Prompt 3 done.** `next_decay_state()` + `test_decay_next_state.py` (LOCKED immune, boundaries, floors, custom policy). |
| 2026-09-18 | **Prompt 4 done.** CLI `scripts/ike2_decay_knowledge.py` (`--dry-run` default / `--apply`); `plan_decays` + fake-clock tests `test_decay_cli_plan.py`. |
| 2026-09-18 | **Prompt 5 done.** Compliance goldens `test_decay_compliance_interaction.py` (AUTO→DISCOVERED loses firm SAFE; VERIFIED→AUTO softens VERIFIED-gated FAIL). |
| 2026-09-18 | **Prompt 6 done.** Linked from `trust_promotion_engine.md`; Beat **not** scheduled. Item **4.1** closed for batch 1. |
| 2026-09-18 | **Course correction (Item 34):** §4.4 rewritten — decay never silences still-true hazard FAIL. Golden flipped to assert FAIL survives demotion. |
