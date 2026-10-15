# Item 11 — Regional coverage gap analysis

**Date:** 2026-09-30  
**Method:** Read the source registry and the files it can actually load. Local Postgres is a second check, not the tracker sheet.  
**Not a spec.** No adapters, no tier decisions, no new sources.

Checked directly: `backend/core/knowledge/ike2/etl/sources.py` (`_DEFAULT_STATE`, `_CANONICAL`), `backend/core/knowledge/ike2/etl/reconcile.py` (`_SOURCE_TIER`), `backend/core/knowledge/ike2/etl/adapt.py` (generic record mapper, no per-country branch), `backend/core/knowledge/ike2/etl/adapters/` (only `produce.py` and `animal.py` implement `SourceAdapter`), committed `data/layer1_*.json`, `data/regional_ingredient_names.json`, and the local `ike2_*` tables.

`adapt.py` does not register sources. It maps whatever record it is given and folds a `"Global"` region marker to null.

---

## 1. What the registry actually contains

| Canonical key | `_DEFAULT_STATE` | `_SOURCE_TIER` | Committed Layer-1 rows | Region tag on those rows | `SourceAdapter` class |
|---------------|------------------|----------------|------------------------|--------------------------|------------------------|
| `usda` (`usda_fdc`) | AUTO_CLASSIFIED | 3 | 3,613 (`layer1_usda_fdc.json`) | none | No. `transform_usda_fdc_bulk.py` |
| `fda` (`fda_gras`) | AUTO_CLASSIFIED | 4 | 1,414 (`layer1_fda_gras.json`) | `US` on every row | No. Existing transform path |
| `fssai` | AUTO_CLASSIFIED | 4 | 913 (`layer1_fssai.json`) | `IN` | No. `transform_fssai_bulk.py` |
| `nin` | AUTO_CLASSIFIED | 3 | 82 (`layer1_nin.json`) | `IN` | No. `transform_nin_bulk.py` |
| `ifct` | AUTO_CLASSIFIED | 3 | 540 (`layer1_ifct.json`) | `IN` | No. `transform_ifct_bulk.py` |
| `foodex2` | DISCOVERED | 2 | 1,258 (`layer1_foodex2.json`) | `EU` | No. `transform_foodex2_bulk.py` |
| `e_number_catalog` | LOCKED | 4 | 330 (`layer1_e_numbers.json`) | none | Dedicated generator, not the produce/animal protocol |
| `produce_catalog` | AUTO_CLASSIFIED | 3 | 8 | `Global`, plus `IN` on 7 | **Yes** |
| `animal_catalog` | DISCOVERED | 2 | 7 | `Global`, plus `IN` on 2 | **Yes** |
| `openfoodfacts` | DISCOVERED | 1 | 5,054 taxonomy rows | none | No |
| `ontology` | AUTO_CLASSIFIED | 4 | L2 file, 1,855 ingredients | not a regional dump | No |

Absent from both `_DEFAULT_STATE` and `_SOURCE_TIER`: JECFA, GBIF, INFOODS, FSANZ, a UK composition source, Health Canada, CFIA, and any Middle East key. `license_allowlist.json` names only `produce_catalog` and `animal_catalog`. A new adapter cannot emit until its license is added there.

**Local database (2026-09-30).** `ike2_ingredient_groups.source` is `ontology` on all 1,738 rows. None are stored as `nin`, `ifct`, `usda`, `fssai`, or `foodex2`. Alias regions that are set: `IN` 1,423, `EU` 190, `US` 4, and the literal string `India` 4. So the registry and the Layer-1 files are ahead of this database. Name overlap with `data/ontology.json` (canonical name, then name-or-alias) is the part a resolver can already hit without those source labels:

| Dump | Rows | Canonical name already in ontology | Name or alias in ontology |
|------|------|------------------------------------|---------------------------|
| NIN | 82 | 80 | 82 |
| IFCT | 540 | 214 | 225 |
| FSSAI | 913 | 154 | 220 |
| USDA | 3,613 | 38 | 857 |
| FDA GRAS | 1,414 | 108 | 146 |
| FoodEx2 | 1,258 | 254 | 262 |

---

## 2. Region by region

### USA

Wired: `usda` (tier 3, AUTO_CLASSIFIED, 3,613 Layer-1 rows, **no region tag**) and `fda` (tier 4, AUTO_CLASSIFIED, 1,414 rows, every row `US`). No USA `SourceAdapter`. The live alias table has 4 `US` rows. Most of the USDA dump is not a canonical name in `ontology.json` (38 of 3,613). The old "USA solid" line matches the presence of USDA and FDA dumps, not a database full of `source=usda` groups.

### India

Wired: `fssai` (tier 4), `nin` (tier 3), `ifct` (tier 3). All three have committed JSON, all tagged `IN`. That is more than an empty registry.

NIN is a small curated list and almost all of it is already in the ontology (80 of 82 canonical names). IFCT is the larger composition file: 540 rows, 214 canonical names already in the ontology, so about 326 canonical names exist only in the IFCT dump. FSSAI is 913 additive rows and 154 canonical names already in the ontology. None of those three sources appear as `ike2_ingredient_groups.source` locally.

A separate name map, `data/regional_ingredient_names.json`, has 48 mappings / 106 regional strings (bajra, jowar, and the rest). That is what `bajra` resolves through. It is not the IFCT table. `data/learned_regional_mappings.json` is loaded by `core/external_apis/regional_names.py` and currently holds junk ("cached_query_xyz", "these_ingredients_for_gluten", and similar). That file is live code, not an archive.

India is past "nothing registered." It is not past "the composition dump is what the resolver serves."

### EU

Wired: `e_number_catalog` (LOCKED, tier 4, 330 rows, no region field) and `foodex2` (DISCOVERED, tier 2, 1,258 rows, every row `region=EU`, uncertainty flag `foodex2_inferred`). FoodEx2 is a classification dump, not a national composition table. Live aliases include 190 `EU` rows. Uneven is still a fair word: additives and a taxonomy, not a member-state composition set.

### UK

No UK composition adapter, no `cofid` / McCance key, no Layer-1 file tagged `UK`.

The FoodEx2 transform comment says its optional raw CSV is "an AgroPortal export of the UK FSA FoodEx2 register." The emitted records are `source=foodex2` and `region=EU`. That is the EU taxonomy path above, not a UK food-table adapter. UK composition is still unbuilt.

### Canada

No source key, no transform, no Layer-1 file, no adapter, no `CA` alias region in the local table.

### Middle East

No source key, no transform, no Layer-1 file, no adapter. No Middle East region value on the local alias table.

---

## 3. New sources that would each need a `SourceAdapter`

The only classes that follow the produce/animal protocol today are `ProduceCatalogAdapter` and `AnimalCatalogAdapter`. Everything below is absent from `_DEFAULT_STATE`, `_SOURCE_TIER`, and `license_allowlist.json`. Each would need its own license check-in before `emit_layer1_records` will emit anything.

Each also needs its own trust-tier and knowledge-state decision. Copying produce's AUTO_CLASSIFIED / tier 3, or animal's DISCOVERED / tier 2, is the same kind of silent choice Item 1.2 refused for animals.

| Source | Why it does not inherit an existing tier |
|--------|------------------------------------------|
| JECFA | Additive specifications. Closest existing path is `e_number_catalog` (LOCKED, tier 4), which is a generated catalog, not this protocol. Own call. |
| GBIF | Species occurrence, not a food-composition or additive table. No sibling in the registry. Own call. |
| INFOODS | Multi-country composition tables. Shape is closer to IFCT/USDA than to produce, and those two are not the same tier as each other in practice (both AUTO / tier 3 on paper; USDA rows are mostly not in the ontology). Own call. |
| FSANZ | Australia/New Zealand composition and standards. Not one of the six regions above. Regulatory, not a produce seed. Own call. |
| UK FSA composition | Not the FoodEx2 file already in the repo. A CoFID-style table would be a new source. Own call. |
| Health Canada / CFIA | Regulatory, nearer FDA (tier 4) or FSSAI (tier 4) than produce. Own call anyway: FDA and FSSAI were registered separately, and animal was not allowed to copy produce. |

---

## 4. `ike2_alias_disambiguation`

The table, the resolver read (`stores/db.py` `disambiguate()`), and row-level security exist. No migration inserts a row. The local table has **0** rows. Tests insert a row and delete it. Item 2 Prompt 8 already deferred operator seeding. The mechanism is real. The cross-region content is not.

---

## Phase 1 inject (2026-10-01)

Answers used for this run, not a spec: a source counts only when a live group carries it (Q6). Inject the already-registered dumps first (Q1). FoodEx2 stays EU and was not injected (Q2). New-source tiers stay deferred (Q3). Region token is `IN` (Q4).

Dry-run (`bulk_inject --dry-run`, empty in-memory writer, so it does not see existing groups):

| Source | Rows | Passed | Rejected | Reject reason |
|--------|------|--------|----------|----------------|
| IFCT | 540 | 540 | 0 | |
| FSSAI | 913 | 913 | 0 | 2 canonical names collided inside the file |
| USDA | 3,613 | 3,477 | 136 | `dairy_implies_animal` (`dairy_source` true, `animal_origin` false). Yogurt and cheese dishes the dump marked plant-only. Quarantined, not written. |

Live inject. New groups are `AUTO_CLASSIFIED`. Rows that already existed stayed `source=ontology`; the pipeline merged flags onto them instead of retagging the source.

| Source | Before | After |
|--------|--------|-------|
| ontology | 1,738 | 1,738 |
| ifct | 0 | 324 |
| fssai | 0 | 755 |
| usda | 0 | 3,439 |

Live overlap (updated, source unchanged): IFCT 216, FSSAI 158, USDA 38. One IFCT merge, 77 FSSAI merges, and 4 USDA merges set `needs_review`. Ontology `AUTO_CLASSIFIED` went from 1,730 to 1,649 and `DISCOVERED` from 8 to 89. That is the existing reconcile rule: a newly set safety flag demotes a non-protected group.

`ike2_aliases.region = 'India'` was 4 rows (`titanium dioxide`, `e171`, `ci 77891`, `tio2`), each also present as `US` and none as `IN`. Those 4 are now `IN`. `India` is gone. `IN` aliases went from 1,423 to 6,564 after the inject.

`data/learned_regional_mappings.json` had 118 keys. IKE-2 resolve uses only the static map, so those keys did not change chat or evaluate. The enrichment fetcher calls `get_canonical_queries`, which does apply learned keys that the static map does not already cover. 4 keys (`bajra`, `makka`, `ragi`, `suran`) were already static and stayed correct. About 114 others would have redirected a real USDA/OFF lookup, including `gluten` → "Bread, gluten free", `tartaric_acid` → "Steak tartare", `shellac`, `carmine`, `bone_phosphate`, `disodium_inosinate`, `coriander`, and `cumin`. The mappings object was cleared. Static names are unchanged.

## Decisions recorded for this run (2026-10-01)

1. Inject registered dumps before any new adapter.
2. FoodEx2 stays an EU taxonomy. UK composition is still unbuilt. Not injected here.
3. Tier calls for JECFA, GBIF, INFOODS, FSANZ, UK composition, and Health Canada/CFIA wait until each source is actually being built.
4. Region token is `IN`.
5. Learned mappings were on the enrichment lookup path and were cleared. See above.
6. A source is done only when a live group row carries that `source`.

## Demotion vs review (2026-10-01, report only)

`reconcile()` sets `needs_review` only when a stored flag goes from false to true. It then sets `knowledge_state` to `DISCOVERED`. A dump value of false against an ontology true is not a demotion: the ontology true is kept and that flag does not set `needs_review`.

Of the rows now `source=ontology` and `DISCOVERED` (89), replay against `ontology.json` plus the three dumps:

| Class | Rows | What happened |
|-------|------|----------------|
| Added positive, no other disagreement | 10 | The only change is false → true. Examples: `canthaxanthin` and `polyglycerol esters of fatty acids` gained FSSAI `synthetic`; `potato pancakes` gained USDA `root_vegetable`; `dulce de leche` gained USDA `egg_source`. Ontology had recorded those flags as false, not omitted the key. |
| Added positive, and a separate disagreement the merge ignored | 72 | Demotion still comes from the new true, almost always FSSAI `synthetic`. On another flag the ontology was true and the dump was false, and the true was kept. Example: `acetic acid` stays `plant_origin` and `fermented`, gains `synthetic`, drops to `DISCOVERED` because of `synthetic`. `agar` is the same pattern (`plant_origin` kept, `synthetic` added). |
| Disagreement only | 2 | `ascorbic acid`, `citric acid`. FSSAI says not `plant_origin`. That did not flip `needs_review`. These sit with the pre-existing `DISCOVERED` set. |
| No flag change from these dumps | 5 | `oat`, `parsnip`, `pepsin`, `rennet`, `mono and diglycerides`. Pre-existing `DISCOVERED`, not this inject. |

The 82 `needs_review` counts from the inject (IFCT 1, FSSAI 77, USDA 4) are the 10 + 72 addition rows. Ontology `AUTO_CLASSIFIED` fell by 81, so one of those 82 was already `DISCOVERED`. None of the 81 new demotions were caused by a true-versus-false conflict. Every one was an added positive. The ignored conflicts (mostly `plant_origin`, 58 of them) did not demote anyone.

`needs_review` is not a column. `run_induction.py` builds candidates from the unknown log and ontology roles. It does not read these groups. There is no CLI list of the 82, so there is no pass to time. Item 5's y/N prompt never sees them.

The listing a person can read without a CLI is `docs/item11_phase1_flag_changes.md` (10 added-only rows, 72 added plus an ignored disagreement). `false` in `ontology.json` is not a verified negative: `Ingredient` defaults every boolean to false, `to_dict()` always writes them, and no field records who asserted the value. `canthaxanthin` has `synthetic: false` and `uncertainty_flags: ["may_be_synthetic_or_animal_derived"]` on the same row.
