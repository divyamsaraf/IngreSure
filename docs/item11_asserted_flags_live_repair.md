# Item 11 — Live `asserted_flags` pollution repair

**Date:** 2026-10-05  
**Status:** repaired on local live DB; INFOODS live inject still pending go-ahead with post-repair baseline

## Scope (before repair)

| | Count |
|--|------:|
| Total `ike2_ingredient_groups` | 6256 |
| Empty `asserted_flags` | 4556 |
| Clean true-only | 2 |
| **Polluted** (at least one asserted name whose stored value is not `true`) | **1698** |

### By source

| source | total | polluted | clean true-only | empty |
|--------|------:|---------:|----------------:|------:|
| ontology | 1738 | **1698** | 2 | 38 |
| usda | 3439 | 0 | 0 | 3439 |
| fssai | 755 | 0 | 0 | 755 |
| ifct | 324 | 0 | 0 | 324 |

Pollution is **ontology-only**. Phase 1 inject sources (usda/fssai/ifct) never received `asserted_flags` contents.

### Signature

Almost all polluted rows share one shape: a **13–17 name full boolean block** (same Ingredient-style flag list), including names whose values are still `false`. Top falsely asserted names: `garlic_source`, `insect_derived`, `onion_source`, `sesame_source`, `fermented`, … — the same default-false set the design forbade backfilling.

**Trace:** one bad pass on ontology-sourced rows (not several independent migrations). Distinct pollution signatures: 16 minor variants of the same full-block pattern. Not produced by INFOODS (never written). Opposite of the true-only `ontology.json` file backfill (file has **0** rows asserting a false).

The 11 INFOODS demotion names were a subset of this 1698, not a separate problem.

## Repair

For every live row with non-empty `asserted_flags`: keep only names whose stored boolean is **`true`**; drop the rest. No new asserts invented.

| | Count |
|--|------:|
| Rows updated | **1698** (all `source=ontology`) |
| Polluted after | **0** |
| Clean true-only after | 1650 |
| Empty after | 4606 (includes ~50 former polluted rows that had no true flags at all) |

### Item 34/35 reviewed exceptions (untouched intent)

Repair only stripped fabricated falses. Deliberate true asserts remain:

| canonical | after `asserted_flags` | `animal_origin` still asserted |
|-----------|------------------------|--------------------------------|
| bone phosphate | `['animal_origin']` | yes |
| disodium inosinate | `['animal_origin']` | yes |
| l-cysteine | `['animal_origin']` | yes |

`bombay duck` after: `fish_source: false` **not** in `asserted_flags`; `asserted_flags: ['animal_origin']`.

## Live-DB-seeded INFOODS replay (after repair)

| Metric | Ontology dry-run | Live replay after repair |
|--------|-----------------:|-------------------------:|
| inserted | 526 | 521 |
| updated | 95 | 100 |
| rejected | 0 | **0** |
| needs_review / demotions (either kind) | 0 | **0** |

**Demotion bar: pass.** Insert/update still 521/100 because five INFOODS heads already exist under Phase 1 sources on live — expected, not pollution.

INFOODS live write completed 2026-10-05 and matched this baseline exactly (521/100/0/0). See `item11_infoods_dry_run.md` § Live write.
