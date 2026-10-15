# Item 11 — INFOODS AnFooD2.0 dry-run report

**Date:** 2026-10-04  
**Slice:** AnFooD2.0 only (BioFoodComp not included)  
**Status:** **live inject done 2026-10-05** — matched post-repair replay exactly (521/100/0/0). See § Live write.

## Build shipped

- `InfoodsAnfoodAdapter` + license allowlist `infoods: CC-BY-4.0`
- Registry: `AUTO_CLASSIFIED` / tier **3** (`sources.py`, `reconcile._SOURCE_TIER`)
- Transform/CLI: `backend/scripts/transform_infoods_anfood.py`
- Dump: `data/layer1_infoods_anfood.json` (**621** groups)
- Canonical form (designed in day one): **head commodity** as `canonical_name`; full analytical English string, scientific name, local name, and `INFOODS:{id}` as aliases

## Ontology-seeded dry-run (same proof pattern as Phase 1)

Seeded `data/ontology.json`, then `inject(..., "infoods")` in memory:

| Metric | Count |
|--------|------:|
| inserted | 526 |
| updated (overlap) | 95 |
| rejected | **0** |
| needs_review | **0** |
| plain false→true demotions | **0** |
| asserted-flip demotions | **0** |

Empty CLI `--dry-run` alone is not the proof (insert-only within the dump). This seeded replay is.

## Hygiene checks

- Dual animal+plant origin rows: **0**
- Canonical names with remaining prep tokens (`raw`/`boiled`/`fillet`/…): **0**

## Live preflight (2026-10-05) — inject not run

Before write, replayed the same dump against a seed of the **live** `ike2_ingredient_groups` table (not ontology.json). Numbers do **not** match the ontology dry-run. Per the injection standard, **no live write**.

### Before counts (live DB)

| source | groups |
|--------|-------:|
| usda | 3439 |
| ontology | 1738 |
| fssai | 755 |
| ifct | 324 |
| **total** | **6256** |
| AUTO_CLASSIFIED | 6167 |
| DISCOVERED | 89 |

### Predicted live inject vs ontology dry-run

| Metric | Ontology dry-run | Live-DB replay | Match? |
|--------|-----------------:|---------------:|--------|
| inserted | 526 | 521 | **no** (−5; already present via Phase 1 sources) |
| updated | 95 | 100 | **no** (+5) |
| rejected | 0 | 0 | yes |
| needs_review | 0 | **11** | **no** |
| plain false→true demotions | 0 | 0 | yes |
| asserted-flip demotions | 0 | **11** | **no** |

### Why the 11 demotions appear on live but not on the file dry-run

`data/ontology.json` true-only backfill is clean (0 rows assert a false). Live ontology-sourced rows carry a **full boolean name list** in `asserted_flags`, including flags whose stored value is still `false` — e.g. `bombay duck` has `fish_source: false` but `fish_source` listed in `asserted_flags`. INFOODS correctly adds `fish_source: true`; reconcile treats that as overriding a verified negative and demotes.

That live `asserted_flags` pollution is **outside** this inject’s dump quality. It is a separate data bug (asserted falses that the Item 11 design explicitly forbade backfilling). Fixing it or accepting those 11 demotions as intentional review is a decision before any live INFOODS write.

The 11 names (all `source=ontology`): `bombay duck`, `cat fish`, `catla`, `caviar`, `cuttlefish`, `mullet`, `rohu`, `salted cod`, `shark`, `silver carp`, `squid`.

## Live write (2026-10-05) — matched post-repair replay

After true-only `asserted_flags` repair (`item11_asserted_flags_live_repair.md`), live inject of `data/layer1_infoods_anfood.json`:

### Before → after (`ike2_ingredient_groups` by source)

| source | before | after |
|--------|-------:|------:|
| usda | 3439 | 3439 |
| ontology | 1738 | 1738 |
| fssai | 755 | 755 |
| ifct | 324 | 324 |
| **infoods** | **0** | **521** |
| **total** | **6256** | **6777** |

Knowledge state: AUTO_CLASSIFIED 6167 → 6688 (+521); DISCOVERED stayed **89** (no demotions).

### Inject stats vs post-repair replay

| Metric | Replay | Live | Match? |
|--------|-------:|-----:|--------|
| inserted | 521 | 521 | yes |
| updated | 100 | 100 | yes |
| rejected | 0 | 0 | yes |
| needs_review | 0 | 0 | yes |

**Done.** Alias upsert count (9627) is below the in-memory replay’s 9899 because many alias keys already existed on live from Phase 1 — not a group-level divergence.
