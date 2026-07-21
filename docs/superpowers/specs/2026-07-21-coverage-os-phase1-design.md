# Coverage OS Phase 1 — Evidence Graph, Hybrid Promote Gate, Multi-Profile Matrix

**Date:** 2026-07-21  
**Status:** Design approved (brainstorming locks)  
**Scope:** Phase 1 only. Phase 2 (induction + ontology-role neutralize policies) is a separate design pass after Phase 1 exit criteria are met.

## Problem

Long grocery pastes and cross-profile checks surface many “similar” bugs that are not per-diet rule failures. They are shared resolution gaps (word-order, prep forms, missing meat/organ aliases, compound over-split, true unknowns). Coverage today grows largely by hand-editing closed allowlists (`variant_aliases`, plant modifiers, facet sets). That does not scale, and online APIs must not mint Safe at verdict time without a concrete evidentiary chain.

## Locked decisions

1. **Verdict bar = evidentiary chain**, not category aggressiveness.  
   - Concrete chain → Safe is earned (any profile category).  
   - Must assume away an unknown (unspecified species, unspecified process) → Depends (any category).  
   - **Avoid fail-closed is identical** across allergy, medical, lifestyle, and religious.  
   - Lifestyle “broader” means more ways to **earn** Safe with evidence — **not** a lowered confidence threshold. Allergens clear the bar less often because animal-origin evidence is harder, not because the bar is softer.

2. **Hybrid promote (C):** evidence kind drives automation, not a global comfort level.  
   - **Auto-promote:** plant-only, single-origin, closed-form evidence, no allergen-adjacent overlap, no dual-origin naming collision.  
   - **Human-approval:** any animal origin, any allergen relevance, any compound/dual-origin ambiguity — no “looks obviously fine” exceptions.  
   - Auto promotions are versioned, reversible, rule-logged; auto-lane is sample-audited; volume spikes alert.

3. **Approach 1+2 hybrid, phased.**  
   - Phase 1: evidence graph, hybrid gate, ledger, matrix, writer — candidates from corpus/manual, **not** induction.  
   - Phase 2 (later): induction of aliases/facets/typed neutralize policies into the **same** gate and ledger.

## Architecture

### Runtime (unchanged)

IKE-2 chat path: **L1 truth anchor → L2 local ontology → L3 Supabase → L5 unknown (Depends)**.  
No embeddings/LLM at resolve. External APIs enrich **offline only**.

### Coverage OS (Phase 1, offline)

```text
Miss / unknown / break-test corpus
        │
        ▼
 Candidate ──► hybrid_gate (checks promote_ledger for
               confirmed_non_promotable first)
                    │
     ┌──────────────┴──────────────┐
     ▼                             ▼
 Auto-promote lane          Human-approval lane
     │                             │
     └──────────────┬──────────────┘
                    ▼
         promote_ledger (versioned;
         promote / demote / non_promotable)
                    ▼
         promote_writer apply | retract
                    ▼
    data/ontology.json + variant_aliases.json
    (+ L3 inject as derived mirror only)
                    │
                    ▼
         profile_matrix (detector + chains)
```

## Store unification

| Store | Role |
|-------|------|
| `data/ontology.json` | **Canonical L2.** Coverage OS writes here; IKE-2 `local_ontology` and legacy registry read the same file. Growth of Coverage OS = strengthening of Supabase-outage safety net. |
| `data/commodity_seed_lists/variant_aliases.json` | **Canonical synonymy.** Resolver synonymy ladder and promote writer share this file. |
| Supabase L3 | **Derived mirror only.** Inject after file promote from ledger; never a silent second source of truth in Phase 1. L3 inject failure must not leave L2 inconsistent; log drift warning and keep L2 authoritative. |

## Evidence graph (attested chain)

Every matrix cell and ledger-backed resolution records:

| Field | Meaning |
|-------|---------|
| `atom` / `canonical` | Input and resolved name (if any) |
| `source` | `truth_anchor` \| `ontology` \| `variant_alias` \| `facet` \| `db` \| `unknown` |
| `flags` | Identity flags used |
| `rule_ids` | Compliance rules that fired (empty on clean Safe) |
| `verdict` | Safe / Avoid / Depends |
| `evidence_class` | `closed_form_plant` \| `animal` \| `allergen` \| `dual_or_compound` \| `insufficient` |
| `miss_class` | When Depends (M1–M8 observability tags) |

Safe requires a concrete chain. Depends when the chain would require assuming away an unknown.

## Hybrid gate predicates

### Auto-promote — all must hold

1. Single origin: `plant_origin` and not `animal_origin`.  
2. No animal / egg / fish / shellfish / insect / bee / dairy flags.  
3. Not allergen-adjacent (closed deny list):  
   peanut, tree nut, sesame, soy, gluten/wheat, mustard, celery, lupin, fish, shellfish, **sulfite**, **mollusc**.  
4. No dual-origin name collision (name not also keyed to an animal/allergen row).  
5. Not compound/process umbrella (`verdict_cap=WARN`, dish regex, E-number, flavors/spices umbrellas).  
6. Evidence `rule_id` is one of the closed-form plant rules (logged on the ledger entry).

Otherwise → human-approval queue.

### Ledger short-circuit (required)

`hybrid_gate` **depends on `promote_ledger`**. Before predicates:

1. Look up candidate pattern in ledger for `confirmed_non_promotable`.  
2. If found → short-circuit to **rejected** without re-running predicates (no re-proposal loop).

## Promote ledger

Entry kinds:

| Kind | Required fields |
|------|-----------------|
| `promoted` (auto) | `rule_id`, `source`, `version`, reversible payload |
| `promoted` (human) | same + **`reviewer_id`** + **`approval_rationale`** |
| `demoted` | prior version pointer; triggers writer **retract** |
| `confirmed_non_promotable` | `rule_id`, `source`, reason; blocks re-queue |

Human-approval accountability must be **equal or stronger** than the auto lane (highest-stakes cases).

## Components (Phase 1)

| Unit | Responsibility |
|------|----------------|
| `evidence_chain` | Build/serialize attested chain for resolve + evaluate |
| `hybrid_gate` | Non-promotable short-circuit + auto vs human vs reject predicates (incl. sulfite/mollusc deny); **depends on promote_ledger** |
| `promote_ledger` | Versioned promote / demote / confirmed_non_promotable; human reviewer fields |
| `promote_writer` | **Apply** approved entries → `ontology.json` + `variant_aliases.json`; **retract** on demote (symmetric reverse on same files); optional L3 mirror inject after apply |
| `profile_matrix` | One paste × all IKE-2 `SUPPORTED_RESTRICTIONS`; report Safe/Avoid/Depends + chains |
| `auto_lane_guards` | Sample-audit selector + volume-spike log/alert stub |

## Data flow

1. Matrix run → Depends/miss telemetry.  
2. Human or corpus picks candidate.  
3. Gate checks ledger for `confirmed_non_promotable` on this pattern → short-circuit reject if present.  
4. Else gate predicates → auto or human queue.  
5. Auto → ledger `promoted` + writer **apply** to L2 files (+ L3 mirror).  
6. Human approve → ledger with `reviewer_id` + `approval_rationale` + writer **apply**.  
7. Human reject → ledger `confirmed_non_promotable`.  
8. Demote → ledger `demoted` + writer **retract** from same L2 files.  
9. Re-run matrix to verify.

## Error handling

- Gate uncertainty → human queue (never auto).  
- Writer apply/retract failure → no partial silent trust; ledger stays pending / prior state.  
- L3 inject failure → L2 remains authoritative; log drift warning.

## Multi-profile matrix

- **Input:** one paste (comma list or label).  
- **Profiles:** every IKE-2 supported restriction, evaluated one at a time.  
- **Output:** CSV/report with verdict + attested chain.  
- **Role in Phase 1:** detector; does not auto-promote. Feeds hand/corpus candidates into the gate.  
- **CI:** curated golden subset (extend audit/golden matrices). Full paste remains analyst CLI.

## Testing (Phase 1)

- Gate unit tests: plant auto; animal human; sulfite deny; mollusc deny; dual-name deny; **non_promotable short-circuit**.  
- Ledger round-trip: promote → **demote (writer retract)** → non_promotable blocks re-queue; human entries require reviewer fields.  
- Matrix golden subset + Avoid parity across categories.  
- Store unification: promote lands in paths L2 resolver reads; demote removes trust from those paths.  
- **Auto-lane guards:** sample-audit selector returns a non-empty sample on a fixture batch of N promotions; volume-spike stub logs when promotions in a fixture window exceed the threshold.

## Phase 1 exit criteria

Phase 1 is done only when:

1. Evidence chain is emitted on matrix and promote paths; no Safe without a concrete chain.  
2. Hybrid gate enforces auto vs human predicates (incl. sulfite/mollusc) and non_promotable short-circuit.  
3. Ledger is versioned/reversible; demote triggers writer retract; human approvals log reviewer + rationale.  
4. Matrix: one paste → all supported profiles with chains; covers break-test / R–Z-style corpus.  
5. Avoid fail-closed identical across allergy/medical/lifestyle/religious (regression tests).  
6. Auto-lane sample-audit + volume-spike hooks wired **and** covered by the smoke tests above.  
7. **No Phase 2 creep:** induction and ontology-derived typed neutralize policies are out of scope; Phase 2 is a separate design pass after these criteria pass.

Phase 1 **fails exit** if coverage still only grows by hand-editing class lists **and** there is no path for Phase 2 induction to feed the same gate/ledger.

## Explicitly out of Phase 1 (Phase 2 entry)

- Induction: derive candidate aliases/facets from miss-log / unknown-log clusters.  
- Typed neutralize policies (dairy-head, plant-mod, process-keep, culinary-keep) derived from ontology roles, replacing one-off compound rows.  
- Runtime L4 (fuzzy / LLM at verdict) — rejected for this program.

## Relation to existing code

Builds on, does not replace:

- `backend/core/knowledge/ike2/resolver.py` (L1–L5, synonymy ladder)  
- `backend/core/knowledge/ike2/commodity_head.py`, `variant_aliases.py`  
- `backend/scripts/promote_commodity_coverage.py` (scrub + merge into `ontology.json`)  
- Golden matrices / variant recall / must-never-be-safe gates  

Morphology and aliases remain the thin runtime engine; Coverage OS is how coverage grows under the evidentiary bar.
