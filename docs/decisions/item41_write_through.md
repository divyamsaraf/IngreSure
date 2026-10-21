# Item 41 — L2/L3 dual-store authority

**Decision:** reviewed write-through. True-only, evidence-classified patches
to `data/ontology.json`. No blind read-time OR of L3 onto L2.

## Authority

Production resolve order is L1 (truth anchor) → L2 (`ontology.json`) → L3
(Supabase). An L2 hit is final for that name. L3 is consulted only after L1
and L2 both miss.

When live/replayed L3 holds a verdict-relevant **true** that L2 lacks for the
same normalized name, the fix is a reviewed patch that writes that true into
`ontology.json` (plus evidence / `asserted_flags` as required). False values
are not written through unless they are on the reviewed-negatives registry.

## Rejected alternatives

- **Blind read-time OR of L3 onto L2.** Would let unreviewed DB drift change
  offline/CI verdicts and hide L2 staleness. Resolver must not merge L3 flags
  into an L2 hit.
- **DB-before-L2.** Fixes runtime drift but makes `ontology.json` a last-resort
  cache; unit tests without Supabase would silently see stale L2.
- **Regenerate L2 from DB after each inject.** Equivalent only if regeneration
  is mandatory in the inject CLI and CI fails when `ontology.json` is stale.
  Write-through is the simpler invariant: reviewed patches are the single
  writer for ontology-named trues.

## Guard

CI fails when any ontology-named row has `live_true && l2_false` on a
verdict-relevant flag. The check is **name-keyed**, not an aggregate count.

Coverage:

- `tests/ike2/test_item41_42_replay_ci.py::test_replay_l2_drift_live_true_l2_false`
  — after dump replay, no ontology-named row may hold a true L2 lacks.
- `tests/ike2/test_item41_write_through.py` — synthetic name-keyed drift helper
  plus resolver tests that an L2 hit never consults or ORs L3.
- `scripts/check_l2_l3_name_drift.py` — standalone name-keyed guard (L2
  self-compare, or `--l3-json` for a live dump).
