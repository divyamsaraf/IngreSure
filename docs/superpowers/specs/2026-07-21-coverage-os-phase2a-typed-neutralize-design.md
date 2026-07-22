# Coverage OS Phase 2a — Typed Neutralize Policy Engine

**Date:** 2026-07-21  
**Status:** Design approved (brainstorming locks)  
**Scope:** Phase **2a only** (typed neutralize). Phase **2b** (induction of roles/aliases into the same gate and ledger) is a separate design pass after 2a exit criteria are met.  
**Depends on:** Coverage OS Phase 1 (`docs/superpowers/specs/2026-07-21-coverage-os-phase1-design.md`) — ledger, hybrid_gate, promote_writer, profile_matrix.

## Problem

Compound tear today is owned by private frozensets in `backend/core/compound_expansion.py` (`_PLANT_MODIFIERS`, `_KEEP_WHOLE_SUFFIXES`, `_KEEP_AND_EXTRACT_WORDS`), while facet/head in `backend/core/knowledge/ike2/commodity_head.py` keeps a **parallel** keep-strip set. That drift class produces false Avoid/Depends (dairy torn from plant yogurt; wine torn from vinegar; soy torn from lecithin) and leaves no proven write path for **role-as-data** that Phase 2b induction needs.

Hand-editing frozensets does not scale, and “behavior looks right in memory” is not enough: 2b needs role assignments that can be promoted, versioned, demoted, and audited the same way ingredient facts already are.

## Locked decisions

1. **Sequencing = C.** Phase **2a = typed neutralize** first; **2b = induction** later (separate design after 2a exits). Reason: live compound-classification correctness first; cleaner signal for induction; neutralize must land on a real write path so 2b has clean ground.

2. **Wiring = C.** One shared policy surface consumed by **both** `compound_expansion` and resolve/facet (`commodity_head`). No private frozenset remnants alongside the new API.

3. **Authorship = C.** Ontology rows carry `role` as data; policy **types** are a **closed enum** (code or tiny locked JSON next to Phase 1 deny_lists). Free-form role strings at promote time are forbidden.

4. **Approach = 2.** `neutralize.apply_policies(...)` is the **only** place plant-mod / dairy-head / process-keep / culinary-keep behavior lives. `compound_expansion` and `commodity_head` are thin callers. Same shape as Phase 1 deny_lists / umbrella-detection reuse.

5. **Plant-mod emission = C.** When plant-mod applies: emit **whole phrase + plant token**; never emit bare dairy/meat from that pair. Whole-phrase identity and independent allergen significance are both required.

6. **Exit criteria = C.** Golden bugs + matrix smoke **+** seeded-head role assignments flow through Phase 1 ledger / writer / gate (not hand-edits alone).

7. **Dual-emit audit presentation.** Both atoms are **evaluated** independently. User-facing audit shows **one** top-level card for the user-typed phrase; derived plant restriction hits attach to that card. Relatedness uses a single field — see §4.

8. **Role-only gate = human_fail_closed.** No new auto shortcut for role payloads in 2a. See §7.

9. **Tier-1 keep-whole = explicit fallback** inside the same keep decision (roles first, then `truth_anchor.lookup`, then tear). See §6.

## Non-goals

- Induction / miss-log mining (Phase **2b**).
- Runtime L4 fuzzy or LLM at verdict time.
- Unifying enrichment `_PLANT_OVERRIDE_*` phrase lists (named residual; out of 2a).
- New Coverage OS infrastructure (reuse promote_writer, promote_ledger, hybrid_gate, profile_matrix).

## Architecture

```text
data/ontology.json (role on rows)
        │
        ▼
 role_index ──► PolicyType closed enum
        │              │
        └──────┬───────┘
               ▼
    neutralize.apply_policies(...)     ← single behavior surface
               │
     ┌─────────┴─────────┐
     ▼                   ▼
 compound_expansion   commodity_head / facet
 (thin wrap; no       (shared keep; no
  private frozensets)  parallel frozenset)
               │
               ▼
    expand → display_map + derived_from
               │
               ▼
    compliance evaluate (both atoms)
               │
               ▼
    audit UI: one card per user phrase;
    derived hits fold into source card

 Coverage OS write path (exit C):
   hybrid_gate → promote_writer (ontology_row + role)
              → promote_ledger → ontology.json
```

**Module home:** `backend/core/knowledge/ike2/coverage_os/neutralize.py` (policy types colocated or locked JSON beside Phase 1 deny_lists). Runtime chat imports the same API as the offline harness.

**Single API:** `apply_policies(phrase | tokens, *, role_index) -> PolicyResult`

`PolicyResult` carries:

| Field | Meaning |
|-------|---------|
| `atoms` | Ordered list of atoms to emit |
| `policy_fired` | Which `PolicyType`(s) applied (audit / tests) |
| `derived_from` | Per derived atom: parent phrase key (see §4) |
| `uncertainty` / `verdict_cap` hints | When process/culinary-keep leaves source ambiguous |

## Policy types (closed enum) and behaviors

| PolicyType | Trigger | Atom emission | Verdict / certainty |
|------------|---------|---------------|---------------------|
| `plant_mod` | Plant-role token adjacent to dairy/meat token (**both token orders**) | Keep phrase **+** emit plant token; never emit bare dairy/meat from that pair | Phrase resolves as plant product; plant atom carries allergen signal |
| `dairy_head` | Dairy-role head with species/mod token (**both orders**: `yogurt goat` / `goat yogurt`) | Keep dairy head intact; species as attached signal (flag / structured attachment — not a second competing dairy tear) | Head remains the evaluate atom |
| `process_keep` | Process/prep roles (mechanically, dried, …) | Keep whole phrase **and** extract restricted base keywords (today’s keep-and-extract) | Whole may carry `uncertainty` / `verdict_cap=WARN` when process/source opaque |
| `culinary_keep` | Culinary heads (vinegar, lecithin, sauce, …) | Keep whole; do not tear to nested restricted keywords | Keep-whole ≠ Safe: malt vinegar gluten, unspecified lecithin, opaque sauces still WARN/Depends as appropriate |

**Token-order rule:** Adjacency for `plant_mod` and `dairy_head` is order-independent. Goldens cover both orders for each seeded pair class.

**Conflict rule:** If both `plant_mod` and `dairy_head` could apply, **`plant_mod` wins** when a plant-role token is present (e.g. plant yogurt is not dairy).

### Dual-emit relatedness (one mechanism)

When `plant_mod` (or process keep-and-extract) emits a derived atom alongside a phrase atom:

- **`derived_from`** is the **only** relatedness field on emitted atoms. The derived atom’s `derived_from` is the source phrase key (normalized). There is **no** separate `emission_group_id` — that name is not used. Parent pointer is sufficient for multi-child groups (several extracts from one phrase all share the same `derived_from`).
- **`display_map`** remains the existing label-remap contract: every emitted eval atom key maps to the **user-typed** phrase for card labeling. It does not replace `derived_from`; it answers “what label to show,” while `derived_from` answers “this atom was emitted because of that phrase.”

**Evaluation:** both (or all) atoms are evaluated independently.

**Audit UI:** one top-level card for the user-typed phrase. Restriction hits from atoms with `derived_from=<that phrase>` attach to that card (or a nested “also checked” line) — not a second sibling top-level ingredient row. A two-item paste (`almond yogurt, sugar`) shows **two** cards, not three.

## Data model — roles as ontology data

- Ontology rows may carry a single field: `role` (string). Allowed values are **exactly** the closed `PolicyType` strings: `plant_mod`, `dairy_head`, `process_keep`, `culinary_keep`. No parallel role vocabulary; no free-form strings at promote time.
- **No `roles: []` list in 2a.** One `role` per row.
- Policy **types** live in code / tiny locked JSON — not invented at promote time.
- ETL / Tier-2: `adapt.map_record` and `local_ontology._NON_FLAG_ROW_KEYS` must pass `role` through (must not land inside `TruthAnchorFact.flags`).
- `coverage_os_managed` still gates overwrite/retract for Coverage OS–written rows.

**How triggers resolve:**

| PolicyType | Role-bearing token | Partner / condition |
|------------|--------------------|---------------------|
| `plant_mod` | Token with `role=plant_mod` | Adjacent token is dairy/meat: either has `role=dairy_head` **or** is in the closed dairy/meat keyword set owned by the policy engine (migrated from today’s restricted dairy/meat singles — not a second private list in `compound_expansion`) |
| `dairy_head` | Token with `role=dairy_head` | Adjacent species/mod token (both orders) |
| `process_keep` | Token with `role=process_keep` | Multi-word phrase containing that token |
| `culinary_keep` | Token with `role=culinary_keep` (typically the head/suffix) | Multi-word phrase ending with / containing that head |

**Seed set (minimal for exit):** roles that replace today’s frozensets — plant modifiers (`plant_mod`), dairy heads (`dairy_head`), culinary-keep suffixes (`culinary_keep`), process-keep words (`process_keep`) — promoted via writer (exit C path).

## Consumers

1. **`compound_expansion`** — After migration ordering (§ Migration) is satisfied, delete private frozensets. `expand_compounds` / `find_sub_ingredients` call `apply_policies` only. Populate `display_map` for all emitted atoms and propagate `derived_from` into the audit/compliance handoff so composers can fold derived hits.

2. **`commodity_head` / facet** — Align `_FORBIDDEN_STRIP` / head-first behavior with shared culinary/process keep policies so facet cannot strip what keep policies retain. Shared helpers only; no second frozenset.

3. **Resolver** — Does not import expansion. Benefits via facet/head. No resolve↔expansion cycle.

4. **Tier-1 `truth_anchor.lookup` keep-whole — explicit fallback (deterministic order):**  
   Inside the keep decision for a multi-word phrase:  
   (a) `culinary_keep` / `process_keep` from roles → keep (and extract if process_keep);  
   (b) else if `truth_anchor.lookup(full_phrase)` hits → keep whole (do not tear);  
   (c) else tear / extract per remaining policies.  
   This is a fallback **within the same decision**, not a parallel source of truth. Residual for later (not 2a exit): migrate L1-only wholes onto roles so the fallback set shrinks over time.

## Promotion path (exit criterion C)

- Extend `ontology_row` payload with optional `role`. Inverse restores prior role or clears on demote (same commit_promotion / commit_demotion ordering as Phase 1).
- **Gate rule (literal, checkable):** A role-only payload has no flags that satisfy `flags.get("plant_origin") and not flags.get("animal_origin")`, so under the **existing** `decide_promote` logic it always falls through to `human_fail_closed`. Phase 2a adds **no** new hybrid_gate branch that auto-promotes on `role` alone. Role+flags payloads follow existing flag logic unchanged.
- Integration test required: human-approved promote → ontology has `role` → `apply_policies` changes behavior → demote restores.

## Testing and exit criteria

All must pass before 2a is closed:

1. **Golden bugs** — Named regressions go green and stay green, including: plant yogurt (both orders); almond yogurt / similar plant+dairy (phrase + plant emit, no bare dairy); yogurt goat / goat yogurt; wine vinegar; soy lecithin; culinary/process opaque cases (no new false Safes).
2. **Matrix smoke** — Real corpus via `profile_matrix`: compound-tear-attributable false Avoid/Depends drop; no new false Safes on culinary/process side.
3. **Ledger/writer round-trip** — Seeded-head `role` promotions/demotions through hybrid_gate → promote_writer → ledger; runtime policy engine reads the **written** role (not a test-only monkeypatch of frozensets).

Unit tests: `apply_policies` isolated offline (no resolve cycle).

## Migration

Ordering constraint (explicit — no gap where compounds go unhandled):

1. Land `neutralize` + closed enum + `role_index` loader. Empty roles must not silently invent plant_mod; fail closed to current safe keep via Tier-1 lookup where already applicable.
2. Seed roles via Coverage OS promotions (human_fail_closed for role-only) until seeded classes cover today’s frozenset membership for the exit goldens.
3. **Only then** delete frozensets from `compound_expansion` and switch thin wrap fully to `apply_policies`. Frozensets stay until roles are seeded **and** goldens for those classes pass through `apply_policies`.
4. Align `commodity_head` to shared keep policies.
5. Matrix smoke + writer integration green.
6. Document residuals (below).

## Risks and residuals

| Risk / residual | Mitigation / disposition |
|-----------------|--------------------------|
| Dual emit looks like duplicate cards | `derived_from` + one top-level audit card; evaluate both atoms |
| Dual emit double-counts in matrix | Matrix smoke asserts no new false Safes; phrase ≠ dairy |
| Role dropped in ETL | Writer integration + adapt / `_NON_FLAG_ROW_KEYS` passthrough test |
| Facet strips kept wholes | Shared culinary_keep in commodity_head; regression goldens |
| Enrichment `_PLANT_OVERRIDE_*` lists still drift | **Named residual; out of 2a** |
| Tier-1 keep-whole fallback set | **Residual:** shrink over time by migrating L1 wholes to roles |

## Phase 1 residuals unchanged

Operational (not safety): single-writer ledger; O(atoms×restrictions) matrix; promote-script dish-regex drift vs truth_anchor — still operational residuals; 2a does not reopen them except where culinary_keep / shared keep reduces dish-regex need for keep-whole identity.

## Success definition

Phase 2a exits when:

1. Private neutralize frozensets are gone from `compound_expansion`; behavior comes only from `apply_policies` + role_index + Tier-1 fallback as specified.
2. Facet/head cannot diverge on keep-whole for the seeded culinary/process classes.
3. Exit criteria C (goldens + matrix smoke + role ledger/writer round-trip) are met.
4. No Phase 2b induction code has landed in `coverage_os/`.

Then — and only then — open a separate Phase 2b design for induction onto this write path.
