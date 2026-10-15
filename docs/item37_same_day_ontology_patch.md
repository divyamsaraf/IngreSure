# Item 37 — Same-day ontology.json false-SAFE patches

animal_origin live_true/l2_false drifts were only caviar + cuttlefish (already in the seafood patch list). oyster/mussel/scallop already NOT_SAFE via L1_truth_anchor before the file patch; L2 hygiene still applied.

## Production probes (before → after)

| Name | Restriction | Before | After | Before layer | After layer |
|------|-------------|--------|-------|--------------|-------------|
| `oyster` | `shellfish_allergy` | NOT_SAFE | NOT_SAFE | L1_truth_anchor | L1_truth_anchor |
| `mussel` | `shellfish_allergy` | NOT_SAFE | NOT_SAFE | L1_truth_anchor | L1_truth_anchor |
| `scallop` | `shellfish_allergy` | NOT_SAFE | NOT_SAFE | L1_truth_anchor | L1_truth_anchor |
| `cuttlefish` | `shellfish_allergy` | SAFE | NOT_SAFE ** | L2_local_ontology | L2_local_ontology |
| `cuttlefish` | `vegan` | SAFE | NOT_SAFE ** | L2_local_ontology | L2_local_ontology |
| `caviar` | `fish_allergy` | SAFE | NOT_SAFE ** | L2_local_ontology | L2_local_ontology |
| `caviar` | `vegan` | SAFE | NOT_SAFE ** | L2_local_ontology | L2_local_ontology |
| `dulce de leche` | `egg_free` | SAFE | NOT_SAFE ** | L2_local_ontology | L2_local_ontology |
| `dulce de leche` | `dairy_free` | NOT_SAFE | NOT_SAFE | L2_local_ontology | L2_local_ontology |
| `halloumi` | `dairy_free` | SAFE | NOT_SAFE ** | L2_local_ontology | L2_local_ontology |
| `filmjölk` | `dairy_free` | SAFE | NOT_SAFE ** | L2_local_ontology | L2_local_ontology |
| `viili` | `dairy_free` | SAFE | NOT_SAFE ** | L2_local_ontology | L2_local_ontology |
| `goat milk fat` | `dairy_free` | SAFE | NOT_SAFE ** | L2_local_ontology | L2_local_ontology |
| `locust` | `vegan` | UNCERTAIN | NOT_SAFE ** | L3_db_alias | L2_local_ontology |
| `locust` | `no_insect_derived` | UNCERTAIN | NOT_SAFE ** | L3_db_alias | L2_local_ontology |

## All 44 verdict-relevant drifts (before patch)

By flag × direction:

- `animal_species:species_mismatch`: 37
- `shellfish_source:live_true_l2_false`: 4
- `animal_origin:live_true_l2_false`: 2
- `gluten_source:live_false_l2_true`: 2
- `egg_source:live_true_l2_false`: 1
- `fish_source:live_true_l2_false`: 1

### Named rows

- `ari fish` — animal_species (species_mismatch: live='' l2='fish')
- `black snapper` — animal_species (species_mismatch: live='' l2='fish')
- `bombay duck` — animal_species (species_mismatch: live='' l2='fish')
- `canned anchovies` — animal_species (species_mismatch: live='' l2='fish')
- `canned salmon` — animal_species (species_mismatch: live='' l2='fish')
- `canned/jarred fish` — animal_species (species_mismatch: live='' l2='fish')
- `cat fish` — animal_species (species_mismatch: live='' l2='fish')
- `catla` — animal_species (species_mismatch: live='' l2='fish')
- `caviar` — animal_origin (live_true_l2_false: live=True l2=False); fish_source (live_true_l2_false: live=True l2=False)
- `crustaceans` — animal_species (species_mismatch: live='fish' l2='crustacean')
- `cuttlefish` — animal_origin (live_true_l2_false: live=True l2=False); shellfish_source (live_true_l2_false: live=True l2=False)
- `dried fish` — animal_species (species_mismatch: live='' l2='fish')
- `dulce de leche` — egg_source (live_true_l2_false: live=True l2=False)
- `fish as feed` — animal_species (species_mismatch: live='' l2='fish')
- `freshwater eel` — animal_species (species_mismatch: live='' l2='fish')
- `gold fish` — animal_species (species_mismatch: live='' l2='fish')
- `guitar fish` — animal_species (species_mismatch: live='' l2='fish')
- `hilsa` — animal_species (species_mismatch: live='' l2='fish')
- `kite fish` — animal_species (species_mismatch: live='' l2='fish')
- `l-cysteine` — animal_species (species_mismatch: live='' l2='chicken')
- `maize gluten feed` — gluten_source (live_false_l2_true: live=False l2=True)
- `milk fish` — animal_species (species_mismatch: live='' l2='fish')
- `mollusks` — animal_species (species_mismatch: live='fish' l2='mollusk')
- `moon fish` — animal_species (species_mismatch: live='' l2='fish')
- `mullet` — animal_species (species_mismatch: live='' l2='fish')
- `mussel` — shellfish_source (live_true_l2_false: live=True l2=False)
- `oyster` — shellfish_source (live_true_l2_false: live=True l2=False); animal_species (species_mismatch: live='shellfish' l2='')
- `pangas` — animal_species (species_mismatch: live='' l2='fish')
- `parrot fish` — animal_species (species_mismatch: live='' l2='fish')
- `queen fish` — animal_species (species_mismatch: live='' l2='fish')
- `raai fish` — animal_species (species_mismatch: live='' l2='fish')
- `red snapper` — animal_species (species_mismatch: live='' l2='fish')
- `rohu` — animal_species (species_mismatch: live='' l2='fish')
- `salt preserved fish` — animal_species (species_mismatch: live='' l2='fish')
- `salted cod` — animal_species (species_mismatch: live='' l2='fish')
- `scallop` — shellfish_source (live_true_l2_false: live=True l2=False)
- `shark` — animal_species (species_mismatch: live='' l2='fish')
- `silk fish` — animal_species (species_mismatch: live='' l2='fish')
- `silver carp` — animal_species (species_mismatch: live='' l2='fish')
- `smoked fish` — animal_species (species_mismatch: live='' l2='fish')
- `sole fish` — animal_species (species_mismatch: live='' l2='fish')
- `sorghum gluten feed` — gluten_source (live_false_l2_true: live=False l2=True)
- `stingray` — animal_species (species_mismatch: live='' l2='fish')
- `whale shark` — animal_species (species_mismatch: live='' l2='fish')

## Why 44 ≠ 8 flag-level drifts

The pre-patch “44” counts **names** with any verdict-relevant diff. By flag × direction that is mostly `animal_species` mismatch (37) — typically live empty vs L2 `fish` / kind string — plus the eight boolean live-true/L2-false allergen/origin bits (`shellfish`×4, `animal_origin`×2, `fish`×1, `egg`×1) and two `gluten_source` live-false/L2-true rows. The eight false-SAFE patches target the boolean live-true/L2-false (and dairy oat-shape / locust) cases; species-string hygiene is separate.

## Remaining verdict-relevant drifts after patch: **46**

After patch, L2 is ahead of live for the new dairy/egg/insect trues (expected until inject write-through / Item 41). Species mismatches remain. CI drift (Item 41) should treat `live_true && l2_false` as the fail condition; L2-ahead is the desired direction for these patches.

Artifact: `docs/item37_same_day_ontology_patch.json`.
