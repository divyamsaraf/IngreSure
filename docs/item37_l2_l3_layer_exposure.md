# Item 37 — L2 vs L3 layer exposure (report)

Production resolve order: **L1 truth_anchor → L2 local_ontology (`ontology.json`) → L3 Supabase**. For ontology-named ingredients, live DB merges do not answer.

## 1. Layer exposure (live `source=ontology` vs `ontology.json`)

- Live ontology-sourced rows: **1738**
- Names with verdict-relevant drift: **44**
- Missing from ontology.json: **0**

### Per-flag: live true, L2 false (invisible at runtime if L2 serves)

| Flag | Count |
|------|------:|
| `synthetic` | 77 |
| `root_vegetable` | 6 |
| `shellfish_source` | 4 |
| `plant_origin` | 3 |
| `animal_origin` | 2 |
| `fermented` | 1 |
| `egg_source` | 1 |
| `fish_source` | 1 |

### Top verdict-relevant drift (name)

- `caviar` — animal_origin:live=True/l2=False, fish_source:live=True/l2=False
- `cuttlefish` — animal_origin:live=True/l2=False, shellfish_source:live=True/l2=False
- `oyster` — shellfish_source:live=True/l2=False, animal_species:live='shellfish'/l2=''
- `ari fish` — animal_species:live=''/l2='fish'
- `black snapper` — animal_species:live=''/l2='fish'
- `bombay duck` — animal_species:live=''/l2='fish'
- `canned anchovies` — animal_species:live=''/l2='fish'
- `canned salmon` — animal_species:live=''/l2='fish'
- `canned/jarred fish` — animal_species:live=''/l2='fish'
- `cat fish` — animal_species:live=''/l2='fish'
- `catla` — animal_species:live=''/l2='fish'
- `crustaceans` — animal_species:live='fish'/l2='crustacean'
- `dried fish` — animal_species:live=''/l2='fish'
- `dulce de leche` — egg_source:live=True/l2=False
- `fish as feed` — animal_species:live=''/l2='fish'
- `freshwater eel` — animal_species:live=''/l2='fish'
- `gold fish` — animal_species:live=''/l2='fish'
- `guitar fish` — animal_species:live=''/l2='fish'
- `hilsa` — animal_species:live=''/l2='fish'
- `kite fish` — animal_species:live=''/l2='fish'
- `l-cysteine` — animal_species:live=''/l2='chicken'
- `maize gluten feed` — gluten_source:live=False/l2=True
- `milk fish` — animal_species:live=''/l2='fish'
- `mollusks` — animal_species:live='fish'/l2='mollusk'
- `moon fish` — animal_species:live=''/l2='fish'

## 2. Production re-verify (no layer bypass)

- Findings (expected vs actual): **32** (all current findings are fish_flips_71 → UNCERTAIN via `usda_fdc_bulk_inferred`, not SAFE misses)
- Phase-1 demotions served by L1: **74**
- Phase-1 demotions served by L2: **11**
- Phase-1 demotions served by L3: **0** (zero ⇒ no Phase-1 demotion reached a production verdict)

Cohort layer mixes:

- **stem_triage_dump** (n=92): {'L2_local_ontology': 69, 'L1_truth_anchor': 23}
- **regional_infoods_flipped** (n=13): {'L2_local_ontology': 13}
- **regional_ifct_flipped** (n=27): {'L2_local_ontology': 27}
- **fish_flips_71** (n=71): {'L2_local_ontology': 39, 'L3_db_alias': 32}
- **e220_e228** (n=15): {'L1_truth_anchor': 15}
- **dairy_trio** (n=3): {'L2_local_ontology': 3}
- **phase1_demotions** (n=85): {'L1_truth_anchor': 74, 'L2_local_ontology': 11}
- **same_day_examples** (n=11): {'L1_truth_anchor': 10, 'L2_local_ontology': 1}

### Findings (sample)

- `crustaceans crab dungeness cooked moist heat` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish bass striped cooked dry heat` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish cod atlantic cooked dry heat` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish cod atlantic dried and salted` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish cod pacific cooked` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish herring atlantic cooked dry heat` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish herring atlantic kippered` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish herring atlantic pickled` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish herring pacific cooked dry heat` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish mackerel atlantic cooked dry heat` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish mackerel king cooked dry heat` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish mackerel spanish cooked dry heat` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish mullet striped cooked dry heat` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish oil cod liver` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish oil sardine` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish pike northern cooked dry heat` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish pike northern liver (alaska native)` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish salmon chinook cooked dry heat` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish salmon chinook smoked` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish salmon chinook smoked (lox) regular` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish salmon chum cooked dry heat` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish salmon chum dried (alaska native)` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish salmon chum raw (alaska native)` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish salmon pink canned drained solids` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)
- `fish salmon pink cooked dry heat` [fish_flips_71] expected NOT_SAFE, got UNCERTAIN via L3_db_alias (got UNCERTAIN via L3_db_alias)

## 3. Merge effect (IFCT/FSSAI/USDA/INFOODS → existing ontology names)

- Dump↔ontology overlaps: **{'ifct': 216, 'fssai': 157, 'usda': 38, 'infoods': 99}** (total 510)
- Unique names where dump adds a verdict-relevant flag L2 lacks: **6**
- Live `source=ontology` rows with same invisible pattern: **6**
- By dump (row hits): {'ifct': 1, 'usda': 1, 'infoods': 5}
- By flag: {'shellfish_source': 5, 'egg_source': 1, 'animal_origin': 2, 'fish_source': 1}
- Note: Overlaps (~510) are dump rows whose name exists in ontology.json. Invisible = dump (or live ontology row) has a verdict-relevant true that L2 lacks. Synthetic-only Phase-1 adds are excluded from VERDICT_FLAGS; they demote knowledge_state on the live row but do not appear here.

- `caviar` (infoods) — animal_origin, fish_source
- `cuttlefish` (infoods) — animal_origin, shellfish_source
- `Dulce de Leche` (usda) — egg_source
- `Oyster` (ifct, infoods) — shellfish_source
- `mussel` (infoods) — shellfish_source
- `scallop` (infoods) — shellfish_source

## 4. Decision (not code)

**Recommend: `inject_writes_through_to_ontology_json`** — inject writes through to `ontology.json`.

- Production resolve order is L1 → L2 (ontology.json) → L3 (DB). For any name present in ontology.json, live merges never reach a verdict.
- Write-through keeps the offline/test path (no DB) identical to production for ontology-named ingredients — tests already load ontology.json.
- DB-before-L2 would fix drift but split offline tests from production unless tests always run against a DB fixture.
- L2 regenerated from DB after each inject is equivalent if regeneration is mandatory in the inject CLI and CI fails when ontology.json is stale — write-through is the simpler invariant (inject is the single writer).

Item 12: Add L2-vs-L3 drift check: for every live source=ontology (and every live row whose canonical_name is in ontology.json), diff verdict-relevant true flags; fail or ticket when live_true and l2_false on allergen/species/animal_origin. Diff by name, not aggregate count.

New item: Logged as Item 41 (P0): docs/item41_l2_l3_dual_store_authority.md — dual stores need one declared authority + L2↔L3 drift test (step-1: 1738 live ontology rows, 44 with verdict-relevant drift).

## 5. UNCERTAIN-under-both (128) + no-kind dairy/egg

- Count in exposure file (both UNCERTAIN, non-land-meat): **128**
- Breakdown: {'unresolved_as_typed': 0, 'resolved_no_kind': 0, 'flagged_but_untrusted_or_capped': 128, 'other': 0}
- Uncertainty tokens: {'usda_fdc_bulk_inferred': 128}
- Mechanism: All 128 currently resolve with fish_source or shellfish_source true via L3, but carry uncertainty_flags (typically usda_fdc_bulk_inferred) so trusted=False and allergy rules stay UNCERTAIN (fail-closed). Not unresolved strings; not missing kind flags.

### Ontology no-kind tags

- Dairy-tagged row(s): `coconut milk powder` (plant milk powder mis-tagged; not an oat-shape dairy miss)
- Other-animal (46):

  - `alligator`
  - `animal fat`
  - `blood sausage`
  - `bockwurst`
  - `bone char`
  - `bone phosphate`
  - `calf`
  - `canada goose`
  - `castoreum`
  - `collagen`
  - `disodium inosinate`
  - `dove`
  - `edible casings`
  - `elk`
  - `emu`
  - `filmjölk`
  - `goose`
  - `guanylic acid`
  - `guinea hen`
  - `halloumi`
  - `inosinic acid`
  - `kangaroo`
  - `l-cysteine`
  - `lanolin`
  - `lard`
  - `liverwurst spread`
  - `meatballs`
  - `ostrich`
  - `pepsin`
  - `pheasant`
  - `porchetta`
  - `poultry`
  - `quail`
  - `rabbit`
  - `rennet`
  - `ruffed grouse`
  - `salami`
  - `sausage`
  - `spermaceti wax`
  - `squab`
  - `steak`
  - `stockfish`
  - `suet`
  - `tallow`
  - `viili`
  - `wild boar`

- No-kind dairy SAFE findings (oat-shape under dairy_free): **4** — `viili`, `halloumi`, `filmjölk`, `goat milk fat`
- No-kind egg SAFE findings: **0**
- Insect-named in no-kind: **1** — `locust`

Among the 46 other-animal tags, dairy-shaped names that are also no-kind SAFE under dairy_free include `halloumi`, `filmjölk`, `viili` (and `goat milk fat` from the lexicon scan). `stockfish` is fish-shaped no-kind under fish_allergy — same FINDING class as fish/shellfish.

Artifacts: `docs/item37_l2_l3_layer_exposure.json`, `docs/item37_phase1_layer_serving.json`, `docs/item37_uncertain128_breakdown.json`, `docs/item41_l2_l3_dual_store_authority.md`.
