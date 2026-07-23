# Coverage OS Phase 2b — Induction (Aliases + Roles)

**Date:** 2026-07-23  
**Status:** Design approved (brainstorming locks)  
**Scope:** Phase **2b only** (offline induction of aliases and ontology roles into the Phase 1 gate/ledger/writer). Facets remain deferred.  
**Depends on:** Phase 1 (`docs/superpowers/specs/2026-07-21-coverage-os-phase1-design.md`) and Phase 2a (`docs/superpowers/specs/2026-07-21-coverage-os-phase2a-typed-neutralize-design.md`).

## Problem

Coverage still grows mostly by hand/corpus picks into the gate. Miss and unknown signals exist (`unknown_ingredients_log.json`, miss_class / matrix Depends) but do not systematically become versioned L2 writes. Phase 2a proved `variant_alias` and `ontology_row`(+`role`) write paths; induction must feed **those** paths under the same safety bar — without a new auto shortcut and without inventing targets.

**Goal:** Offline induction clusters frequency + miss_class → deterministic proposals (alias and/or role) → **structural force-human** submit → ledger/writer → measurable precision before any induced auto.

## Locked decisions

1. **Scope = A.** Aliases + roles only. Facets deferred as a **named residual / future phase** (no facet `write_kind` in 2b).

2. **Mining source = C.** Hybrid: `unknown_ingredients_log.json` **frequency** + **miss_class** (M1–M8) as **one pipeline with two co-equal signals**. Frequency drives volume/prioritization; miss_class supplies candidate-type context. Neither alone is sufficient.

3. **Auto in v1 = C.** **All** induced candidates force `human_approval`. Policy sits **in front of** the gate; `decide_promote` predicates are unchanged. Auto for induced aliases is a later follow-up after the precision bar.

4. **Alias target = A.** Deterministic unique closed-form resolve/fold/head hit, else **no proposal**. No LLM targeting; no co-occurrence.

5. **Role proposal = C.** Pattern-fill (new tokens matching neutralize adjacency) **+** backfill empty roles on existing rows from tear telemetry.

6. **Approach = 2.** Single `coverage_os/induction/` pipeline (`cluster` → `propose` → `submit` force-human wrapper). Not a JSONL queue + separate manual walk-through; not matrix-primary inversion of mining.

7. **Exit criteria = C.** Plumbing + no new false Safes vs Phase 2a baseline + **precision bar** (A + A1 + A2). See §8.

8. **`safety_class` source of truth = gate/deny_lists helpers only.** Induction must **not** invent a parallel classifier. See §5–§6.

## Non-goals

- Facet store / facet `write_kind` (**named residual / future phase**).
- Turning on auto for induced aliases (follow-up after precision bar).
- Runtime L4 fuzzy/LLM at verdict; LLM-assisted targeting in v1.
- Co-occurrence or probabilistic alias targeting.
- Changing `decide_promote` predicates (force-human is a wrapper **in front**).
- Label-decomposer `derived_from` residual (already named in 2a).
- A second animalish/allergen/umbrella keyword surface inside induction.

## Architecture

```text
unknown_ingredients_log.json ──┐
                               ├─► cluster ──► propose ──► submit (force-human)
miss_class / matrix Depends ───┘         │         │
                                         │         ▼
                                         │   decide_promote (unchanged)
                                         │         │
                                         │         ▼  (always human path for induced)
                                         │   commit_promotion(auto=False, reviewer_…)
                                         ▼
                              candidate record (provenance + safety_class)
                                         │
                                         ▼
                              precision query on ledger
```

**Package:** `backend/core/knowledge/ike2/coverage_os/induction/`  
**Modules (proposed):** `cluster.py`, `propose_alias.py`, `propose_role.py`, `submit.py`, `precision.py`, `types.py`, and a thin `safety_class.py` (or equivalent) that **only** composes existing helpers — no local frozensets.

### `submit` contract (structural force-human)

- Never calls the auto-lane.
- Always records a human decision, then `commit_promotion(..., auto=False, reviewer_id=..., approval_rationale=...)`.
- Induced path **must not** invoke `auto=True` **even if** `decide_promote` would return `auto_promote`.
- Force-human is enforced by this code path existing, not by a documented CLI convention.

Same lesson as Phase 1 `deny_lists.py` and Phase 2a `neutralize.apply_policies`: one shared surface every consumer calls.

## Candidate shape

Every candidate carries at least:

| Field | Meaning |
|-------|---------|
| `proposal_kind` | `variant_alias` \| `ontology_role` |
| `raw` / `canonical` or `role` | Deterministic proposal payload |
| `frequency` | From unknown-log cluster |
| `miss_class` | M1–M8 when available |
| `provenance` | Sources, cluster_id, rule that proposed |
| `safety_class` | See §5 — **assigned only via gate/deny_lists helpers** |

No proposal when alias target is non-unique / missing, or role pattern/backfill does not fire.

## `safety_class` — source of truth (edit locked)

`safety_class` exists so precision A1 can filter **dangerous-class** decisions without reconstructing gate behavior from loosely coupled files. It is a **label for measurement**, not a second policy engine.

### Allowed values

`plant_closed` | `animalish` | `allergen_adjacent` | `dual_origin` | `umbrella` | `role_only`

### Assignment mechanism (mandatory)

Induction assigns `safety_class` by calling the **same** predicates `decide_promote` already uses — imported from existing modules — **not** by reimplementing keyword/flag checks inside `induction/`:

| Predicate | Import from | Maps to `safety_class` |
|-----------|-------------|------------------------|
| `is_allergen_adjacent(flags)` | `coverage_os.deny_lists` | `allergen_adjacent` |
| `is_animalish(flags)` | `coverage_os.deny_lists` | `animalish` |
| `has_dual_origin_collision(candidate_name, ontology)` | `coverage_os.hybrid_gate` | `dual_origin` |
| `is_umbrella_term(candidate_name, flags)` | `coverage_os.hybrid_gate` | `umbrella` |
| `flags.get("plant_origin") and not flags.get("animal_origin")` | same closed-form plant condition as `decide_promote` | `plant_closed` |
| none of the above | — | `role_only` (residual; includes role proposals and other fail-closed candidates that are not plant-closed) |

**Priority order must match `decide_promote`** (excluding the non-promotable short-circuit, which rejects rather than classifies):

1. `allergen_adjacent`
2. `animalish`
3. `dual_origin`
4. `umbrella`
5. `plant_closed`
6. else → `role_only`

**Forbidden:** local frozensets, parallel “animal-derived” string lists, miss_class→safety_class heuristic maps, or any induction-only classifier that could disagree with the gate on the same `(name, flags, ontology)` inputs.

**Flags / name inputs:**

- **Alias proposals:** evaluate predicates on the **resolved unique target** row’s flags (and that target’s name for collision/umbrella), not on free-text OCR junk from the unknown log alone.
- **Role proposals:** evaluate on the **existing ontology row** being role-filled (canonical name + that row’s flags).

**A1 dangerous-class set** (precision filter): exactly  
`{animalish, allergen_adjacent, dual_origin, umbrella}` — i.e. the four human-routing predicates above `plant_closed` in the gate. `plant_closed` and `role_only` are **out** of A1’s denominator.

**Consistency invariant:** For a given `(candidate_name, flags, ontology)`, the dangerous/plant/residual bucket implied by `safety_class` must match which branch `decide_promote` would take for those same inputs (modulo force-human overriding `auto_promote` → still human submit). Unit tests must assert this alignment on fixtures covering each bucket.

## Propose rules

### Alias

Normalize/fold + unique existing resolved target (ontology / alias / head residual that already resolves). Else **no proposal**.

### Role — pattern-fill

Multi-word forms matching neutralize adjacency; propose missing token `role` from the closed Phase 2a enum only (`plant_mod` | `dairy_head` | `process_keep` | `culinary_keep`).

### Role — backfill

Existing ontology row, empty `role`, tear/matrix evidence implicates missing role → propose that role.

`safety_class` is assigned **after** a proposal exists (so target/row identity is known), using §5 only.

## Testing & exit criteria

Must all pass to close 2b v1:

1. **Round-trip:** induce alias + induce role → force-human → ledger → writer → demote; provenance intact.
2. **Safety:** matrix/smoke vs `backend/tests/ike2/coverage_os/fixtures/phase2a_matrix_baseline.json` — **no new false Safes**.
3. **Precision A:** first **50** distinct induced human decisions → **≥70%** accepted.
4. **Precision A1:** among dangerous-class decisions (`safety_class` ∈ A1 set), **≥90%** accepted, with **≥10** such decisions in the window (wait if needed).
5. **Precision A2:** **zero** accepted-then-demoted-for-safety-reason in the sample window.
6. **Structural:** no code path where induction can `auto=True`; facets still no writer.
7. **Classifier alignment:** tests prove `safety_class` assignment uses only deny_lists/hybrid_gate helpers and matches `decide_promote` branch for the same inputs (see §5).

**Operational residual (not exit):** A3-style cap on dangerous-class volume in the reviewer queue — optional later.

## Risks & residuals

| Item | Disposition |
|------|-------------|
| Facets no write_kind | **Named residual / future phase** |
| Induced auto aliases | Follow-up after precision bar |
| A3 volume cap | Operational residual |
| Label-decomposer derived_from | Already named (2a) |
| Single-writer ledger | Phase 1 operational residual |
| Noisy unknown-log OCR junk | Clustering + no-proposal; volume-spike guards |
| Drift if `safety_class` reimplemented locally | **Closed by §5** — helpers only; alignment tests |

## Spec self-review notes

- No TBD/TODO placeholders left for `safety_class` assignment.
- Force-human remains structural in `submit`, not a CLI convention.
- Mining remains hybrid co-equal (not matrix-primary).
- Scope stays aliases + roles; facets explicitly deferred.
