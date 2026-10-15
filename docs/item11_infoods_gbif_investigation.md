# Item 11 — INFOODS investigation + GBIF role (report only)

**Date:** 2026-10-03 (investigation); build started 2026-10-04  
**Method:** Live FAO AnFooD2.0 workbook + repo registry/transforms/resolver.  
**Status:** Investigation approved; **AnFooD2.0 build in progress** (adapter + layer1 + dry-run). BioFoodComp still not in scope. GBIF parked outside this pipeline.

---

## A. INFOODS

### A.1 What “INFOODS” means here

INFOODS is a FAO programme that publishes **several** Excel composition databases, not one dump. The two closest to a bulk-inject candidate:

| Product | Role | Scale (published) |
|---------|------|-------------------|
| **AnFooD2.0** (Analytical Food Composition Database, 2017) | Scrutinized analytical values only (no imputed nutrients) | Workbook downloaded for this report: **1,947** food rows with English names across group sheets |
| **BioFoodComp** (Food Composition Database for Biodiversity) | Biodiversity / cultivar-heavy sibling | Docs cite ~7.9k entries in v3.0 — **not** parsed here |

**Recommendation for a first slice:** AnFooD2.0 only. Do not fold BioFoodComp into the same first inject; it is a second investigation.

Source file used: `https://www.fao.org/fileadmin/templates/food_composition/documents/AnFooD2.0.xlsx` (HTTP 200, ~1.2 MB, 2026-10-03).

### A.2 Data shape (AnFooD2.0)

Sheets are **food-group partitions**, not a flat USDA-style table:

| Sheet | Rows with English name |
|-------|------------------------|
| 09 Fish & Shellfish | 983 |
| 03 Legumes | 511 |
| 05 Vegetables | 267 |
| 01 Cereals | 111 |
| 02 Starchy Roots & Tubers | 53 |
| 06 Fruits | 11 |
| 04 Nuts & Seeds | 2 |
| 07 Meat | 2 |
| 08 Eggs | 1 |
| 12 Miscellaneous | 6 |
| 10 Milk / 11 Herbs | 0 usable English rows in this file |

Columns (typical): Food Item ID, Country/region, local name, **Foodname in English**, Processing, **Scientific name**, plus nutrient component columns. Fish sheet adds Subgroup / ISSCAAP / Type (farmed vs wild).

This is the **same family of work as IFCT/USDA transforms**: composition → Layer-1 records with **inferred** origin flags from group/text, plus `uncertainty_flags` (IFCT uses `ifct2017_inferred`; USDA uses `usda_fdc_bulk_inferred`). It is **not** the produce/animal curated-seed protocol (tiny CC0 JSON + `SourceAdapter` + license gate), though a new adapter *could* be written that way once license is checked in.

Nutrient values are irrelevant to IKE-2 compliance; English name, scientific name, local name, country, and sheet/group are the usable fields.

### A.3 Licensing

FAO’s **Statistical Database Terms of Use** list **FAO/INFOODS Food Composition Databases** under corporate statistical databases and state that, unless metadata says otherwise, those datasets are **CC BY 4.0**.

Repo gate: `license_allowlist.json` already allows global `CC-BY-4.0`. A new `SourceAdapter` still needs an explicit `source_licenses.infoods` (or `infoods_anfood`) entry before `emit_layer1_records` will emit — same discipline as produce/animal. Grandfathered `transform_*_bulk.py` paths do not call `license_check`; prefer the adapter+allowlist path for INFOODS so the gate is real.

Attribution to FAO is required under CC BY. Commercial product use is in scope of CC BY 4.0; still confirm the specific AnFooD download page/metadata at implement time (fail closed if that file’s notice conflicts).

### A.4 Coverage beyond IFCT / FSSAI / USDA / ontology

Measured against normalized names in `ontology.json` + `layer1_ifct.json` + `layer1_fssai.json` + `layer1_usda_fdc.json`:

| Metric | Count |
|--------|------:|
| AnFooD rows with English name | 1,947 |
| Unique normalized full English strings | 1,339 |
| Unique head commodities (strip processing words / parentheticals) | 613 |
| Head commodities already in existing name∪alias set | 133 |
| Head commodities **not** in that set | **480** |
| Of those new heads with ≤3 tokens (label-like) | **466** |
| Unique scientific names | 645 |
| Scientific names already present as name/alias | 96 |

**Skew:** ~986 animalish rows (almost all fish/shellfish) vs ~955 plantish rows. Meat/milk/egg/fruit coverage in AnFooD2.0 is negligible. So the “new” set is largely **fish species and regional legumes/vegetables**, not another USDA pantry duplicate.

**Caveat:** Full English strings are analytical-sample descriptions (`african catfish farmed skinless boneless fillet boiled`). Resolver hit rate will be poor unless the transform emits **head commodities + scientific names + local names** as aliases (IFCT already puts Latin names in aliases, e.g. `Sesbania grandiflora`).

Exact full-string overlap with existing dumps is tiny (~14); that number is misleading. Head-commodity overlap (**133**) is the honest reuse figure; **~480** new heads is the honest gap.

### A.5 Trust-tier recommendation (reasoned, not inherited)

| Field | Recommendation | Why |
|-------|----------------|-----|
| Canonical source key | `infoods` (slice id `infoods_anfood` in classification_method / uncertainty if useful) | Not registered today |
| Default `knowledge_state` | **`AUTO_CLASSIFIED`** | Same class as IFCT/USDA composition tables with inferred flags — not crowd (OFF) and not curated LOCKED additives |
| `_SOURCE_TIER` | **`3`** | Align with `usda` / `ifct` / `nin`. Below FDA/FSSAI regulatory (4). Above FoodEx2/taxonomy DISCOVERED (2) and OFF (1) |
| Flag inference | From **sheet membership** (Fish→`animal_origin`+`fish_source`/`shellfish_source`; Cereals/Legumes/Vegetables→`plant_origin`; etc.) + scientific-name assist later | Stronger structure than USDA free-text category sniffing |
| Uncertainty | Always attach e.g. `infoods_anfood_inferred` on inferred bools | Matches IFCT/USDA honesty |
| `asserted_flags` | Only keys the transform deliberately set (present after inference), via `map_record` | Gate already inherited; do not emit full false blocks as asserted |
| Region | Prefer parsed `Country, region` when it maps cleanly to ISO-ish tokens; else omit / Global—**not** a single `IN` stamp | Multi-country by construction |
| Not recommended | Copying `produce_catalog` AUTO/3 without check-in, or `animal_catalog` DISCOVERED/2 by default | Item 1.2 refused silent inheritance; fish-heavy ≠ “treat like animal_catalog seed” |

**Why not DISCOVERED/tier 2?** Animal-catalog DISCOVERED was for a tiny curated seed where firm SAFE must wait for promotion. AnFooD sheet→kingdom mapping is as good as IFCT group inference, which already ships AUTO/3. Positive `fish_source` / `animal_origin` still FAIL vegan (and related) under Item 34 even when KS is modest; the AUTO vs DISCOVERED distinction is mainly firm-SAFE eligibility on clean plant rows.

**Why not tier 4?** This is not a regulatory permission list (FSSAI/FDA). It is analytical composition compiler data.

### A.6 Implementation shape (when building — not now)

1. License allowlist entry for `infoods`.  
2. Transform AnFooD → Layer-1 JSON (grandfather-style) **or** `SourceAdapter` emitting the same records.  
3. Register `_DEFAULT_STATE` / `_SOURCE_TIER` / `_CANONICAL` aliases.  
4. Dry-run inject with ontology-seeded overlap replay (same proof pattern as Phase 1 + asserted_flags).  
5. Live inject only after dry-run demotion/reject report is read.

---

## B. GBIF — role before scoping as a “source”

### B.1 What GBIF actually is

GBIF (Global Biodiversity Information Facility) exposes:

- **Species / checklist APIs** — match a scientific name to a taxon (kingdom, family, accepted name, synonyms). Backbone is moving to Catalogue of Life Extended Release.
- **Occurrence records** — where/when a taxon was observed. Irrelevant to ingredient compliance.
- Dataset licenses vary (**CC0 / CC-BY / CC-BY-NC** per dataset). Taxonomy match responses are tooling over that network, not a food table.

Nothing in the repo implements GBIF today (`rg` over `backend/` / `docs/` only hits the Item 11 “future source” list).

### B.2 What the system already uses for “species”

- Compliance cares about **`animal_species`** strings and bools (`fish_source`, `shellfish_source`, …), not GBIF taxon keys (`rules.py`, truth anchors).
- Resolver “disambiguation” is **`ike2_alias_disambiguation`**: same normalized alias → different ingredients by **region** (`stores/db.py` `disambiguate()`). Local table has **0** rows. That is regional alias conflict, not Latin-name taxonomy.
- Composition dumps already carry Latin names as **aliases** (IFCT) or could (INFOODS `Scientific name` column). Nobody validates them against an external taxonomy service today.

### B.3 Two different integrations

| Integration | Fits SourceAdapter / bulk_inject? | Risk profile | Verdict |
|-------------|-----------------------------------|--------------|---------|
| **A. Bulk ingredient rows from GBIF** | Poorly. GBIF is not a food-composition or additive lexicon; emitting millions of taxa as “ingredients” would flood L3 with non-label names and guessed flags | High noise, wrong abstraction | **Out of sequence.** Do not put GBIF in the INFOODS→JECFA composition/regulatory queue |
| **B. Species-name assist** | No. Side service: given a scientific name from IFCT/INFOODS/USDA aliases, call Species match → confirm Plantae vs Animalia (and maybe family) to validate or fill `plant_origin` / `animal_origin` / `fish_source` | Bounded, enrich-only, fail-closed on miss | **Different workstream** — resolver/enrichment support, not Item 11 bulk source #N |

### B.4 Recommendation

**Do not assign GBIF a trust tier or Layer-1 dump yet.** It is not the same kind of work as INFOODS.

If pursued later, scope it as: *optional taxonomic validation helper for rows that already have a scientific name*, writing only into flag/uncertainty fields (and never inventing a group from a GBIF-only hit). That can sit beside Item 18 enrichment or a small offline synonym table; it does not belong in `emit_layer1_records` next to AnFooD.

---

## C. Sequencing

1. **INFOODS AnFooD2.0** — next build candidate after this report is accepted; tier **AUTO_CLASSIFIED / 3** with explicit registry + license check-in.  
2. **GBIF** — park outside this sequence until someone needs scientific-name validation; then design as assist, not bulk source.  
3. **JECFA** — still its own call (additive specs ↔ nearer `e_number_catalog` than composition tables).

No code changes in this pass.
