# Item 41 — L2 / L3 dual-store authority (P0)

**Status:** opened 2026-10-13 (report-backed; no code yet)  
**Priority:** P0  
**Companion:** [`item37_l2_l3_layer_exposure.md`](item37_l2_l3_layer_exposure.md) · [`item37_same_day_ontology_patch.md`](item37_same_day_ontology_patch.md) · Item **33** (dual resolve engines) · Item **12** (observability) · Item **42** (inferred-positive trust gate) · tracker row **41**

> **ID note:** Spreadsheet Item 38 is allergen-family triage (closed). An earlier draft of this doc incorrectly claimed “Item 38.” This is **Item 41**.

## Problem

Production resolve is **L1 → L2 (`data/ontology.json`) → L3 (Supabase)**. Injects and triage flips write the live `ike2_ingredient_groups` row. For any name present in `ontology.json`, **L2 answers** and the live row is invisible. Item 37’s fish flips on ontology-named seafood were a hard proof: eight live flips did not move verdicts until `ontology.json` was patched.

Deeper framing: L2’s unasserted false defaults **override** an asserted live true. Reconcile never drops a positive on write; the read path does. That is the `asserted_flags` trap at layer level.

This is the Item **33** lesson again: two stores that can disagree need one declared runtime authority and a test that catches drift.

## Evidence (Item 37 layer-exposure report)

See `docs/item37_l2_l3_layer_exposure.json` §1–4 and `docs/item37_same_day_ontology_patch.md` (same-day false-SAFE patches).

| Signal | Count |
|--------|------:|
| Live `source=ontology` rows | 1738 |
| Names with verdict-relevant L2↔live drift (pre-patch) | 44 |
| Live-true / L2-false `synthetic` (Phase-1 residue) | 77 |
| Dump↔ontology overlaps | IFCT 216 + FSSAI 157 + USDA 38 + INFOODS 99 = **510** |
| Of those, dump adds a verdict-relevant flag L2 lacked | **6** unique names (patched same-day) |
| Phase-1 demotions served by L3 at production resolve | **0** (74 L1 + 11 L2) |

## Options (weigh before coding)

| Option | What it does | Offline / CI | Deploy risk |
|--------|--------------|--------------|-------------|
| **A. Inject writes through to `ontology.json`** | Single writer: merge onto an ontology name also updates the file committed with the app | Unit tests without DB stay production-shaped | **Weak alone:** L2 ships from the repo. An inject on another machine that does not commit + deploy the file reopens drift |
| **B. L2 regenerated from DB after each inject** | Export step mandatory; CI fails if file stale | Same as A if export lands in the repo | Same deploy coupling as A |
| **C. DB before L2** | Live row answers for ontology names | Splits offline tests from production unless every suite uses a seeded DB | Removes file-deploy lag; tests become DB-shaped |
| **D. Read-time positive-OR (L2 ∨ L3)** | Keep L1→L2→L3 order for identity; for boolean hazard flags, OR true from the L2 fact and the L3 row when both exist for the same canonical | Offline tests still use L2; production gains live positives without reordering layers | **Does not require a deploy to pick up a live true.** Does not fix L2-only false-SAFEs when L3 is absent or also false. Not a full authority story — a read-path heal for the asserted-true trap |

### Recommendation (updated)

1. **Short term (already used for seafood / same-day patches):** patch `ontology.json` when a user-visible false-SAFE is on an ontology name.  
2. **Guard (required, not optional):** a **CI drift test against a seeded database** — not an audit “either way.” Fail the build on `live_true && l2_false` for verdict-relevant flags **by name**. Write-through without this guard is not enough under multi-machine inject + repo-shipped L2.  
3. **Weigh D seriously for the asserted-true trap:** read-time positive-OR is not layer reordering. It closes the case where reconcile kept a live true and L2’s default false still answered. Pair with the CI drift test so OR does not hide permanent divergence.  
4. **Option C offline objection is closed for the guard itself:** `tests/ike2/test_item41_42_replay_ci.py` seeds an in-memory FakeWriter from ontology + allergen-heavy dumps (no Supabase) and fails on (a) true hazard → SAFE and (b) `live_true && l2_false` by name. That is the seeded fixture Item 42’s invariant and Item 41’s drift test share. Choosing C for *production resolve order* still needs a broader offline strategy; choosing C is no longer required just to get the CI guards.

Write-through (A) remains useful for keeping the committed file honest and for names with no L3 row; it is **not** sufficient as the only control.

## Done means

1. Declared authority documented (identity: L1→L2→L3; hazard positives: either write-through+CI, or read-time OR+CI — pick one in implementation).  
2. **CI test** (seeded DB fixture): for every live `source=ontology` row and every live row whose `canonical_name` is in `ontology.json`, diff verdict-relevant true flags (allergen, species, `animal_origin`); **fail** on `live_true && l2_false` by name.  
3. If choosing write-through: inject updates `ontology.json` in the same operation (or blocked export).  
4. If choosing read-time OR: document which flags OR, that identity/layer attribution still comes from the winning layer, and that CI still fails on persistent drift.  
5. Regression: a live asserted true on an ontology name without a matching L2 true must fail CI (and must not be user-visible SAFE under the chosen read policy).

## Out of scope for this item

- Re-ordering resolve layers as a sole fix.  
- Softening / standing of `*_inferred` on L3 allergy FAIL → **Item 42**.  
- Expanding FINDING rules beyond the same-day patches already landed.

## Stage log

| Date | Note |
|------|------|
| 2026-10-13 | Opened from Item 37 L2-shadow report (was mis-numbered 38). Write-through + CI guard + read-time OR option. No code. |
| 2026-10-13 | Same-day ontology patches for false-SAFEs (seafood/dairy/egg/locust). |
| 2026-10-13 | Live `animal_species` on `crustaceans` / `mollusks` corrected (`fish` → crustacean/mollusk) before any read-time OR. |
| 2026-10-13 | CI: `test_item41_42_replay_ci.py` wired in `.github/workflows/ci.yml` (in-memory replay harness = shared seeded fixture for Item 41 drift + Item 42 invariant). |
