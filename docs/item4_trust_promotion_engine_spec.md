# IngreSure — Build Specification: Item 4
## Trust & Promotion Engine

**Status:** Draft — ready to build (decisions locked 2026-09-17).  
**Companion:** `docs/phase2_gap_analysis.md` § Item 4 · `docs/item5_6_10_1_12_investigation.md` (human-review path) · Coverage OS specs under `docs/superpowers/specs/2026-07-21-*` / `2026-07-23-*` · tracker row **4**

---

## 0. How to use this document

Item 4 is **not** greenfield. The rule engine and Coverage OS promote/neutralize/induction spine already ship. This spec **unifies them as one Trust & Promotion Engine**, closes remaining gaps that are actually Item 4’s, and records binding product decisions so implementers do not rebuild what exists or invent parallel review mechanisms.

Facts in §1 come from Phase 2 (remapped) and the Item 5 force-human investigation — do not re-derive.

Keep this at `docs/item4_trust_promotion_engine_spec.md`.

---

## 1. Current state (confirmed — act on this)

### 1.1 Rule / trust evaluation (live)

| Layer | Path |
|-------|------|
| Seed SoT | `backend/core/knowledge/ike2/rules.py` — `RULE_SEED`, `SUPPORTED_RESTRICTIONS` (31), `seeded_rules()`, `load_rules()` |
| Evaluator | `compliance.py` — `evaluate()` (AND across restrictions; most-severe aggregate) |
| DB | `ike2_restriction_rules` + seed/delta migrations |
| Tests | `tests/ike2/test_rules.py`, `test_compliance.py` |

Nutrition/lifestyle ids in `data/restrictions.json` not in IKE-2 (**14**) are **out of scope** (same deferral class as Item 30).

### 1.2 Coverage OS (live library + operator CLI)

| Module | Status |
|--------|--------|
| `hybrid_gate.py` | Live — `decide_promote` → `auto_promote` \| `human_approval` \| `rejected` |
| `promote_ledger.py` / `promote_writer.py` | Live L2 writes to ontology / variant_aliases; ledger JSONL |
| `neutralize.py` | Live on chat path via `compound_expansion.py` |
| `induction/` + `scripts/run_induction.py` | Live; force-human submit |
| Phase 2a role seed | Live — 66-row ledger under Item **4** (not 4.1) |
| `commodity_head.py`, `flag_derive.py`, `truth_anchor.py` | Live identity helpers |
| `auto_lane_guards.py` | Stub / log only |
| `mirror_l3_inject` | Stub — **must stay documented no-op** (no reader) |
| Continuous auto-promote daemon / Beat | Does not exist — **out of scope** for Item 4 |

### 1.3 Human sign-off (binding — Item 5 decisions applied here)

- **One pattern everywhere:** when a human must sign off, **immediate-commit** with `auto=False`, `reviewer_id`, `approval_rationale` (see `submit_induced` / `commit_promotion`).
- **No** pending review queue, **no** admin UI under Item 4 or 5.
- Non-induction `human_approval` from the gate must use the **same** immediate-commit pattern — not a second mechanism.
- Unknown-queue triage is Item **18**, not Item 4/5.

---

## 2. Purpose

Make trust evaluation and coverage promotion a **single, documented engine**: deterministic rules decide compliance; Coverage OS proposes and (with human stamp when required) promotes identity/alias/role coverage without false-SAFE risk; stubs that exist only to confuse operators are explicitly frozen or deleted-as-docs.

---

## 3. Scope

### In scope

- Operator-facing documentation of the Trust & Promotion Engine (rules + Coverage OS as one system).
- Ensure every `human_approval` / force-human path uses one immediate-commit contract (CLI induction already does; gate callers that would auto-stamp without reviewer fields must not).
- Keep `mirror_l3_inject` as documented no-op (comment + test that it does not write).
- Leave `auto_lane_guards` as optional log helpers — do **not** build a daemon.
- Regression tests that induction submit never calls `commit_promotion(..., auto=True)`.
- Cross-links from this spec to Items **3.1** (sub-variant flags/rules), **4.1** (decay), **5** (review end-state = CLI), **7** (goldens).

### Explicitly out of scope

- Adding nutrition/lifestyle restriction categories (keto, paleo, …).
- Building review UI / pending queue (Item 5 closed as CLI-only).
- Implementing temporal decay (Item **4.1**).
- Enzyme/fermentation taxonomy completion (Item **3.1**).
- Wiring Celery Beat / auto-promote at scale (Items **18** / **23**).
- Dual-resolve retirement (Item **33**).
- Turning on a real L3 write path.

---

## 4. Target design

```
                    ┌─────────────────────────────┐
  resolved atoms ──►│  rules + compliance.evaluate │──► verdict
                    └─────────────────────────────┘
                                    ▲
                    flags / knowledge_state / truth anchors
                                    │
  unknowns / tear ──► induction propose (heuristic)
                                    │
                         hybrid_gate.decide_promote
                           │              │
                    auto_promote*    human_approval
                           │              │
                           └──────┬───────┘
                                  ▼
                    commit_promotion (L2 + ledger)
                    *auto only where gate + product policy allow;
                     induction always auto=False (force-human)
```

\*Today induction never uses `auto=True`. Prefer keeping auto-promote rare; any new auto path must still honor deny lists / dual-origin collision / umbrella checks in `hybrid_gate.py`.

---

## 5. Safety invariants

1. Coverage promote must not create false SAFE (gate + never-SAFE goldens).
2. Induction accept path **always** `auto=False` with reviewer fields.
3. `mirror_l3_inject` writes nothing.
4. Nutrition/lifestyle gaps must not be “fixed” by inventing weak SAFE rules.
5. One human-sign-off pattern only (immediate-commit).

---

## 6. Numbered build prompts for Cursor

**Prompt 1** — Inventory (no behavior change): list every caller of `decide_promote`, `commit_promotion`, `submit_induced`. Confirm each `human_approval` / force-human path supplies reviewer fields at commit. Record in this file’s stage log.

**Prompt 2** — Docs: add a short `docs/trust_promotion_engine.md` (or expand this §4) pointing operators at `run_induction.py`, `seed_neutralize_roles.py`, ledger location under `data/coverage_os/`, and the L3 no-op decision. Update `docs/README.md` link.

**Prompt 3** — Freeze L3 no-op: strengthen `mirror_l3_inject` docstring + unit test asserting no file/DB write side effects.

**Prompt 4** — Guardrail test: static or unit check that `submit_induced` accept path never passes `auto=True` (already true — lock it).

**Prompt 5** — If Prompt 1 finds a caller that takes `human_approval` and either auto-stamps without reviewer fields or drops the candidate silently, fix that caller to immediate-commit with configured `reviewer_id` **or** skip with an explicit log — never invent a pending queue.

**Prompt 6** — Stage log + tracker Notes: Item 4 In Progress → close when Prompts 1–5 done; point Item 5 to “satisfied by CLI force-human” rather than a new build.

---

## 7. Success criteria

- [x] Operator doc exists; README linked.
- [x] L3 mirror documented + tested as no-op.
- [x] Induction force-human `auto=False` locked by test.
- [x] No second review mechanism introduced.
- [x] Tracker Item 4 Notes reference this file (and Item 5 → CLI force-human close-out).

### Stage log

| When | Notes |
|------|-------|
| 2026-09-17 | Draft from remapped Phase 2 + Item 5 decisions. |
| 2026-09-17 | **Prompt 1 done.** Production callers: `run_induction.py`, `seed_neutralize_roles.py` — both force `auto=False`. No violating callers (Prompt 5 N/A). |
| 2026-09-17 | **Prompts 2–4 done.** Operator doc `docs/trust_promotion_engine.md` + README link. `mirror_l3_inject` docstring + `test_mirror_l3_noop.py`. Guardrail `test_submit_has_no_auto_true_call_site` locks no `auto=True`. |
| 2026-09-17 | **Prompt 6 done (close-out).** Item 5 pointed to `docs/item5_human_review_closeout.md` (satisfied by CLI force-human). Spec success criteria checked. |
