# G2 completeness audit

**Date:** 2026-10-22  
**Repo HEAD audited:** `76f1f47` (`origin/main`, includes PR #18 `fix/parse-and-backtrack`)  
**Live DB:** local `docker exec supabase_db_ingresure psql -U postgres -d postgres` (`127.0.0.1:54322`) — **SELECT only**  
**Code/files:** `data/ontology.json`, `backend/core/knowledge/ike2/truth_anchor.py` + `truth_anchor_e_numbers.json`, `supabase/migrations/`  
**Not done:** ingest, production mutations, parser/verdict edits, `resolver.resolve()` (L5 would write `ike2_unknown_queue`)

Fill-rate convention:

- Boolean `NOT NULL DEFAULT false` columns: **% TRUE** (non-null is always 100% unless noted).
- Nullable scalars: **% non-null**.
- Arrays: **% nonempty**.
- L1 truth-anchor flags are a **sparse dict**; “present” means the key exists on that canonical’s `flags`.

---

## Findings (severity)

### Critical

| ID | Finding |
|----|---------|
| C1 | Live `ike2_ingredient_groups` has **0** `primary_source_url` and **0** `VERIFIED`/`LOCKED` rows. All **6,913** groups are `AUTO_CLASSIFIED`. E-number catalog (330 entries / 1,244 L1 keys) is **not** in L3 except **7** sulphite `e_number` aliases. |
| C2 | `data/ontology.json` has **8** exact duplicate `canonical_name` rows (`anchovy`, `citric acid`, `ascorbic acid`, `xanthan gum`, `mono- and diglycerides`, `natural flavor`, `artificial flavor`, `l-cysteine`). L2 `setdefault` keeps the first row. |
| C3 | **39** L2 rows lack origin/allergen keys entirely (Coverage-OS-style process tokens plus `soy`, `macadamia`, `flax`, `hemp`, `shea`, `plant`). `map_record` fills missing bools as **false**, so L2 can index them as empty-identity. |
| C4 | Live DB `asserted_flags` is **not** true-only: **233 / 6,913 (3.37%)** rows list a flag whose stored bool is false (mostly USDA dairy with asserted `egg_source`). |

### Warning

| ID | Finding |
|----|---------|
| W1 | `ike2_aliases.language` is **100% NULL** (column exists; no writer sets it). `region` is NULL on **15,609 / 28,474 (54.8%)** aliases — that is the GLOBAL convention, but the “every alias has language/region” rule fails as written. |
| W2 | After `normalize_ingredient_key` (regional remap), **95** L2 names collide (`chana`/`chole`/`chickpeas` → `chickpea`). Distinct stored strings; first canonical wins at L2. |
| W3 | L1 hand rows vs generated E-number catalog share **10** canonicals (`gelatin`, `carmine`, `l-cysteine`, …) with sparse vs full flag dicts and mixed `LOCKED`/`AUTO_CLASSIFIED`. `lookup()` prefers hand keys. |
| W4 | L2 allergen columns are sparse: `peanut_source` present on 6/1857 rows, `fish_source` 467/1857, `bee_product` 1/1857, enzyme flags **0**. Missing key ≠ null; adapters treat missing as false. |
| W5 | `slug` is never written (0/6913). `enzyme_microbial_source` is 0% TRUE. `ike2_unknown_queue` has **33,390 pending** / 1 resolved. |
| W6 | JP national staples: **UNVERIFIED** (no citable Japan list in repo). AE/UAE: **`verified=false`** (no UAE pack). CoFID / Canadian Nutrient File are license-allowlisted but **not ingested**. |
| W7 | Restriction rules: **58** rows, all `region` NULL (GLOBAL). Matches `rules.py` seed; no per-region rule packs. |

Implication checks (`dairy`/`egg`/`fish`/`shellfish` ⇒ `animal_origin`) are **0 violations** in L1, L2, and live L3 (DB CHECKs hold). Boolean flags are **0 NULL** in live L3. Alias unique indexes have **0 duplicate keys**.

---

## 1. Data dictionary (schema + writers)

Migrations: create `20260616000000_ike2_schema.sql`; later alters cited per column. There is **no** `user_profiles` table. There is **no** dedicated e-number table.

Writer keys used below:

| Key | Path |
|-----|------|
| etl | `etl/adapt.py` `map_record`, `etl/adapt_e_number.py`, `etl/bulk_inject.py` `SupabaseWriter` |
| seed | `scripts/seed_ike2_ontology.py` (ontology → etl), `scripts/ci_seed_ike2_min.py` |
| worker | `backend/worker/tasks.py` `enrich_unknown_batch` (etl spine, source `enrichment_api`) |
| resolver | `unknown_queue.record_miss` from L5 only |
| decay | `scripts/ike2_decay_knowledge.py` (`trust_refreshed_at`, `knowledge_state`) |
| sql-seed | restriction-rule `INSERT`s in ike2 migrations |
| sql-backfill | group `UPDATE`s in ike2 migrations |
| coverage_os | `coverage_os/promote_writer.py` — **L2 file only**, not live `ike2_*` |
| profile | `core/profile_storage.py`, `backend/seed_user.py` |
| none | column exists; no production writer found |

### 1.1 `ike2_ingredient_groups`

Created: `20260616000000_ike2_schema.sql`. Live constraints also include later CHECKs.

| Column | Type | Null | Default | Constraints | Writer |
|--------|------|------|---------|-------------|--------|
| `id` | uuid | NO | `gen_random_uuid()` | PK | DB on insert |
| `canonical_name` | text | NO | — | UNIQUE | etl / seed / worker |
| `slug` | text | YES | — | — | **none** |
| `animal_origin` | bool | NO | false | dual-origin CHECK | etl `BOOL_FLAGS` + implication force; sql-backfill honey |
| `plant_origin` | bool | NO | false | dual-origin CHECK | etl |
| `synthetic` | bool | NO | false | — | etl (unreliable FSSAI inference; true-only assert) |
| `fungal` | bool | NO | false | — | etl + `flag_derive` |
| `insect_derived` | bool | NO | false | `insect_implies_animal`; `bee_product_not_insect_derived` (`20260720150000`) | etl; sql-backfill honey clears it |
| `egg_source` | bool | NO | false | `egg_implies_animal` | etl + `flag_derive` |
| `dairy_source` | bool | NO | false | `dairy_implies_animal` | etl + `flag_derive` |
| `gluten_source` | bool | NO | false | — | etl + `flag_derive` |
| `soy_source` | bool | NO | false | — | etl |
| `sesame_source` | bool | NO | false | — | etl |
| `peanut_source` | bool | NO | false | — | etl `_map_nut_source` + `flag_derive` |
| `tree_nut_source` | bool | NO | false | — | etl `_map_nut_source` + `flag_derive` |
| `fish_source` | bool | NO | false | `fish_implies_animal` | etl + `flag_derive` |
| `shellfish_source` | bool | NO | false | `shellfish_implies_animal` | etl + `flag_derive` |
| `mustard_source` | bool | NO | false | — | etl |
| `celery_source` | bool | NO | false | — | etl |
| `lupin_source` | bool | NO | false | — | etl |
| `sulphite_source` | bool | NO | false | — | etl / e-number adapter |
| `animal_species` | text | YES | — | — | etl; `flag_derive` if empty |
| `root_vegetable` | bool | NO | false | — | etl |
| `onion_source` | bool | NO | false | — | etl |
| `garlic_source` | bool | NO | false | — | etl |
| `fermented` | bool | NO | false | — | etl; drives `alcohol_role` |
| `alcohol_content` | numeric | YES | — | — | etl |
| `alcohol_role` | text | NO | `'none'` | `none\|ingredient\|fermentation_trace` | etl `_alcohol_role` |
| `knowledge_state` | `ike2_knowledge_state` | NO | `UNCLASSIFIED` | enum; `verified_requires_source` | etl `sources.default_knowledge_state`; reconcile; decay; `20260720140000` allergen bump |
| `classification_method` | text | YES | — | — | etl `bulk:<source>` |
| `verdict_cap` | text | YES | — | — | etl if dump has it; e-number tier B → `WARN` |
| `primary_source_url` | text | YES | — | required when `VERIFIED`/`LOCKED` | etl `primary_source_url`/`source_url`; e-number adapter sets catalog URL (**not present in this DB**) |
| `uncertainty_flags` | text[] | NO | `{}` | dual-origin requires nonempty | etl |
| `superseded_by` | uuid | YES | — | FK self | `merge_groups.py` protocol (no live Supabase merge writer) |
| `created_at` | timestamptz | NO | `now()` | — | DB |
| `updated_at` | timestamptz | NO | `now()` | — | DB default; **not reliably bumped** on reconcile |
| `version` | int | NO | 1 | — | **none** (never incremented) |
| `bee_product` | bool | NO | false | `bee_product_implies_animal` (`20260720000000`); not insect (`20260720150000`) | etl `BOOL_FLAGS`; sql-backfill honey |
| `trust_refreshed_at` | timestamptz | NO | `now()` | added `20260918000000` | etl `update_group`; decay; sql-backfill from `updated_at` |
| `enzyme_animal_source` | bool | NO | false | `enzyme_animal_implies_animal`; not both (`20260918010000`) | etl `BOOL_FLAGS`; L1 hand (`rennet`, `pepsin`) |
| `enzyme_microbial_source` | bool | NO | false | `enzyme_origin_not_both` | etl `BOOL_FLAGS` (live 0% TRUE) |
| `source` | text | YES | — | added `20260919000000` | etl; sql-backfill from `bulk:%` |
| `asserted_flags` | text[] | NO | `{}` | added `20261003000000`; Python validate true-only / reviewed-negatives | etl (trues, or curated list); reconcile union |

Enum `ike2_knowledge_state`: `UNCLASSIFIED | DISCOVERED | AUTO_CLASSIFIED | VERIFIED | LOCKED | DEPRECATED` (`20260616000000`).

View `ike2_v_alias_resolution` recreated in `20261014000000_ike2_alias_view_include_source.sql` so `g.*` includes `source`.

### 1.2 `ike2_aliases`

Created: `20260616000000_ike2_schema.sql`.

| Column | Type | Null | Default | Constraints | Writer |
|--------|------|------|---------|-------------|--------|
| `id` | uuid | NO | `gen_random_uuid()` | PK | DB |
| `normalized_alias` | text | NO | — | unique with type/region indexes below | etl `upsert_alias`; seed |
| `ingredient_id` | uuid | NO | — | FK `ike2_ingredients(id)` ON DELETE CASCADE | etl |
| `alias_type` | text | NO | `'common'` | `common\|brand\|regional\|misspelling\|e_number\|cas_number\|fda_number\|iupac_name` | etl (`e_number` from e-number adapter) |
| `language` | text | YES | — | — | **none** |
| `region` | text | YES | — | NULL = GLOBAL | etl from dump `regions` (`Global` → NULL) |
| `match_confidence` | text | NO | `'high'` | `exact\|high\|possible` | **none** (DB default) |
| `source` | text | YES | — | — | etl canonical source |
| `created_at` | timestamptz | NO | `now()` | — | DB |

Indexes: `ike2_aliases_global_code_uidx` unique on `normalized_alias` where type is a code; `ike2_aliases_region_uidx` unique on `(normalized_alias, coalesce(region,'GLOBAL'))` otherwise.

### 1.3 `ike2_unknown_queue`

Created: `20260616000000_ike2_schema.sql`.

| Column | Type | Null | Default | Constraints | Writer |
|--------|------|------|---------|-------------|--------|
| `id` | uuid | NO | `gen_random_uuid()` | PK | DB |
| `normalized_key` | text | NO | — | UNIQUE | resolver `enqueue_unknown`; migrate script |
| `frequency` | int | NO | 1 | — | resolver bump; migrate `max(existing, legacy)` |
| `enrichment` | jsonb | YES | — | — | resolver raw_inputs; worker attempts/API; migrate legacy fields |
| `classification_decision` | text | YES | — | — | worker `enrichment_api:<api>` |
| `status` | text | NO | `'pending'` | — | resolver insert `pending`; worker `resolved\|rejected\|exhausted` |
| `created_at` | timestamptz | NO | `now()` | — | DB |
| `updated_at` | timestamptz | NO | `now()` | — | resolver/worker |

### 1.4 `ike2_restriction_rules`

Created: `20260616000000_ike2_schema.sql`. Unique `(category, field, coalesce(region,'GLOBAL'))` in `20260617000000_ike2_seed_restriction_rules.sql`.

| Column | Type | Null | Default | Constraints | Writer |
|--------|------|------|---------|-------------|--------|
| `id` | uuid | NO | `gen_random_uuid()` | PK | DB |
| `category` | text | NO | — | part of unique | sql-seed |
| `field` | text | NO | — | part of unique | sql-seed |
| `operator` | text | NO | `'eq'` | — | sql-seed |
| `value` | text | YES | — | — | sql-seed |
| `action` | text | NO | — | `FAIL\|WARN` | sql-seed |
| `min_knowledge_state` | `ike2_knowledge_state` | NO | `AUTO_CLASSIFIED` | — | sql-seed |
| `region` | text | YES | — | unique coalesced to GLOBAL | sql-seed (always NULL today) |
| `version` | int | NO | 1 | — | sql-seed default |

SQL writers (in order): `20260617000000` seed; `20260720120000` vegetarian insect; `20260720000000` / `20260720130000` Jain `bee_product` + honey; `20260720150000` kosher shellfish; `20260720160000` pescatarian `meat_land_derived`; `20260918010000` enzyme-animal diet FAILs. Runtime loader: `rules.py` (read-only). **No Python INSERT writer.**

### 1.5 `users` (profile table; no `user_profiles`)

Created: `20240101000000_init.sql`. RLS + own-row policies: `20260306000000_enable_rls.sql`. Optional `USE_PROFILE_DB` maps onto this table (`docs/use-profile-db.md` is stale; code **is** implemented).

| Column | Type | Null | Default | Constraints | Writer |
|--------|------|------|---------|-------------|--------|
| `id` | uuid | NO | — | PK, FK `auth.users(id)` | `seed_user.py`; profile insert of UUID users |
| `name` | text | YES | — | — | `seed_user.py` |
| `email` | text | YES | — | UNIQUE | `seed_user.py` |
| `allergies` | jsonb | YES | `[]` | — | `profile_storage._db_save` ← `UserProfile.allergens` |
| `diet_type` | text | YES | — | — | profile ← `dietary_preference` |
| `preferences` | jsonb | YES | `{}` | — | profile nested `lifestyle` |
| `created_at` | timestamptz | NO | `timezone('utc', now())` | — | DB |

Non-UUID / org-namespaced profiles stay on `data/profiles.json`. Live DB: **1** row.

### 1.6 E-number (no table)

E-numbers are **not** a relation. Surfaces:

| Surface | Role | Writer |
|---------|------|--------|
| `data/e_number_catalog.json` | 330 curated entries | generate/verify scripts; `e_number_catalog.entry_to_ike2_row` |
| `data/layer1_e_numbers.json` | bulk-shaped dump of the catalog | `adapt_e_number` |
| `backend/core/knowledge/ike2/truth_anchor_e_numbers.json` | 1,244 L1 alias keys | generate script; loaded by `truth_anchor._load_e_number_anchors` |
| `ike2_aliases.alias_type='e_number'` | L3 routing | etl e-number adapter (**7 live aliases**: E220–E228 sulphites, group `source=fssai`) |

Live L3 is missing almost all of the catalog. L1 still resolves E-codes from the bundled JSON (no DB).

---

## 2. Fill rates and integrity

### 2.1 `data/ontology.json` (L2 file) — 1,857 ingredients

Field presence (selected; of 1,857):

| Field | Present | Present % | TRUE / nonempty | Notes |
|-------|---------|-----------|-----------------|-------|
| `canonical_name`, `id`, `asserted_flags` | 1857 | 100 | asserted nonempty 1768 (95.2%) | |
| `aliases` | 1856 | 99.95 | nonempty 1092 (58.8%) | **string list**, not `{language,region}` objects |
| `animal_origin` / `plant_origin` | 1818 | 97.9 | 352 / 1203 TRUE | **39 rows omit both** (C3) |
| Core diet flags (`dairy`, `egg`, `gluten`, `soy`, `sesame`, `onion`, `garlic`, `fungal`, `fermented`, `synthetic`, `root_vegetable`, `insect_derived`) | ~1815 | 97.7 | see TRUE counts in audit JSON | |
| `fish_source` | 467 | 25.2 | 145 TRUE | sparse |
| `shellfish_source` | 45 | 2.4 | 26 TRUE | sparse |
| `tree_nut_source` | 31 | 1.7 | 27 TRUE | sparse |
| `peanut_source` | 6 | 0.32 | 6 TRUE | sparse |
| `bee_product` | 1 | 0.05 | honey | |
| `enzyme_animal_source` / `enzyme_microbial_source` | 0 | 0 | — | not in file |
| `regions` | 1815 | 97.7 | nonempty **407 (21.9%)** | empty on 1,450 rows |
| `knowledge_state` | 1376 | 74.1 | all `AUTO_CLASSIFIED` | 481 unset |
| `alcohol_content` | 1815 | 97.7 | 6 nonempty; **1809 JSON null** | |
| `nut_source` | 1815 | 97.7 | 26 nonempty; 1789 null | legacy free text |

L2 region tags (row.regions): **IN 221, EU 185, US 1, India 1**, empty 1,450.

Integrity:

| Check | Severity | Result |
|-------|----------|--------|
| dairy/egg/fish/shellfish ⇒ animal_origin | critical | **0** |
| flags JSON-null on present bool keys | critical | **0** |
| asserted_flags true-only | warning | **16** rows assert a false (false-friends: `crab`/`fish_source`, plant milks/`dairy_source`, …). **0 illegal** vs `data/ike2_reviewed_negatives.json` |
| unique stored `canonical_name` | critical | **8 names, 16 rows** (C2) |
| unique after `normalize_ingredient_key` | warning | **95** remapped collisions (W2) |
| alias language/region columns | n/a | aliases are strings; ingredient `regions` empty on 78% of rows (W1 analog) |

C3 incomplete rows (no `animal_origin` key):  
`flax`, `hemp`, `macadamia`, `plant`, `shea`, `soy`, `extract`, `juice`, `paste`, `powder`, `puree`, `purée`, `sauce`, `syrup`, `base`, `broth`, `chopped`, `concentrated`, `cooked`, `cured`, `deboned`, `diced`, `dried`, `extracted`, `fresh`, `frozen`, `ground`, `hydrolyzed`, `isolated`, `mechanically`, `minced`, `raw`, `rendered`, `roasted`, `separated`, `sliced`, `smoked`, `stock`, `textured`.

### 2.2 L1 truth anchor — 1,555 alias keys, 482 canonicals (1,244 E-number keys)

Knowledge state of unique canonicals: **LOCKED 400, AUTO_CLASSIFIED 53, VERIFIED 29** (compounds use `VERIFIED` + `verdict_cap=WARN`).

TRUE rate among 482 canonicals (sparse flags; missing treated as not-true):

| Flag | TRUE | TRUE % | In flags dict % |
|------|------|--------|-----------------|
| `animal_origin` | 68 | 14.1 | 84.0 |
| `plant_origin` | 116 | 24.1 | 74.1 |
| `synthetic` | 181 | 37.6 | 68.3 |
| `fungal` | 17 | 3.5 | 67.4 |
| `insect_derived` | 3 | 0.6 | 66.8 |
| `bee_product` | 1 | 0.2 | 67.0 |
| `egg_source` | 7 | 1.5 | 68.1 |
| `dairy_source` | 16 | 3.3 | 69.9 |
| `gluten_source` | 8 | 1.7 | 68.5 |
| `soy_source` | 10 | 2.1 | 68.1 |
| `sesame_source` | 3 | 0.6 | 67.4 |
| `peanut_source` | 1 | 0.2 | 67.0 |
| `tree_nut_source` | 9 | 1.9 | 68.7 |
| `fish_source` | 12 | 2.5 | 69.1 |
| `shellfish_source` | 14 | 2.9 | 69.7 |
| `mustard_source` / `celery_source` / `lupin_source` / `garlic_source` | 1 each | 0.2 | ~67 |
| `sulphite_source` | 3 | 0.6 | 67.0 |
| `root_vegetable` | 7 | 1.5 | 68.3 |
| `onion_source` | 4 | 0.8 | 67.6 |
| `fermented` | 5 | 1.0 | 66.8 |
| `enzyme_animal_source` | 2 | 0.4 | 67.2 |
| `enzyme_microbial_source` | 0 | 0 | — |
| `verdict_cap` nonempty | 87 | 18.1 | 18.1 |
| `uncertainty_flags` nonempty | 57 | 11.8 | 11.8 |
| `alcohol_role` present | 334 | — | 69.3 (catalog rows) |

Integrity:

| Check | Severity | Result |
|-------|----------|--------|
| dairy/egg/fish/shellfish ⇒ animal_origin | critical | **0** |
| flags null | critical | **0** |
| asserted_flags true-only | n/a | L1 has no `asserted_flags` column; hand `_f()` is true-only plus caps/uncertainty |
| unique alias key | pass | dict keys unique |
| canonical flag-set conflict | warning | **10** canonicals differ between hand sparse dict and generated catalog full dict (W3): `carmine`, `gelatin`, `bone phosphate`, `disodium inosinate`, `beeswax`, `shellac`, `l-cysteine`, `lanolin`, `lactitol`, `lysozyme` |
| alias language/region | n/a | not modeled |

### 2.3 Live `ike2_ingredient_groups` — 6,913 rows

Sources: `usda` 3575, `ontology` 1738, `fssai` 755, `infoods` 521, `ifct` 324. All `classification_method` = `bulk:<source>`. All `knowledge_state` = `AUTO_CLASSIFIED`.

| Field | Fill | Rate |
|-------|------|------|
| `canonical_name` | 6913 non-null | 100% |
| `slug` | 0 | 0% |
| `animal_origin` TRUE | 1951 | 28.22% |
| `plant_origin` TRUE | 4077 | 58.98% |
| `synthetic` TRUE | 1037 | 15.00% |
| `fungal` TRUE | 80 | 1.16% |
| `insect_derived` TRUE | 5 | 0.07% |
| `bee_product` TRUE | 1 | 0.01% |
| `egg_source` TRUE | 100 | 1.45% |
| `dairy_source` TRUE | 438 | 6.34% |
| `gluten_source` TRUE | 237 | 3.43% |
| `soy_source` TRUE | 102 | 1.48% |
| `sesame_source` TRUE | 22 | 0.32% |
| `peanut_source` TRUE | 52 | 0.75% |
| `tree_nut_source` TRUE | 86 | 1.24% |
| `fish_source` TRUE | 646 | 9.34% |
| `shellfish_source` TRUE | 165 | 2.39% |
| `mustard_source` TRUE | 11 | 0.16% |
| `celery_source` TRUE | 11 | 0.16% |
| `lupin_source` TRUE | 6 | 0.09% |
| `sulphite_source` TRUE | 26 | 0.38% |
| `root_vegetable` TRUE | 160 | 2.31% |
| `onion_source` TRUE | 33 | 0.48% |
| `garlic_source` TRUE | 6 | 0.09% |
| `fermented` TRUE | 12 | 0.17% |
| `enzyme_animal_source` TRUE | 2 | 0.03% |
| `enzyme_microbial_source` TRUE | 0 | 0% |
| `animal_species` non-null | 622 | 9.00% |
| `alcohol_content` non-null | 52 | 0.75% |
| `alcohol_role` ≠ `none` | 64 | 0.93% |
| `classification_method` | 6913 | 100% |
| `verdict_cap` | 1 | 0.01% |
| `primary_source_url` | 0 | **0%** (C1) |
| `uncertainty_flags` nonempty | 5289 | 76.51% |
| `asserted_flags` nonempty | 6072 | 87.83% |
| `superseded_by` | 0 | 0% |
| `source` | 6913 | 100% |
| `trust_refreshed_at` | 6913 | 100% |
| dual `animal_origin` ∧ `plant_origin` | 174 | all have uncertainty (CHECK holds) |

Integrity:

| Check | Severity | Result |
|-------|----------|--------|
| dairy/egg/fish/shellfish ⇒ animal | critical | **0** (also insect/bee/enzyme-animal) |
| flags NULL | critical | **0** |
| unique `canonical_name` / lower(trim) | critical | **0 dups** (6913 = 6913) |
| asserted_flags true-only | critical | **233 rows**. False flags: `egg_source` 182, `dairy_source` 33, `shellfish_source` 16, `animal_origin` 8, plus 1 each `celery_source`/`fish_source`/`mustard_source`/`plant_origin`. Examples: `cheese cheddar` asserts `{animal_origin,dairy_source,egg_source}` with `egg_source=false`. |

Related counts: `ike2_ingredients` 6,913 (1:1 with groups).

### 2.4 Live `ike2_aliases` — 28,474 rows

| Field | Fill |
|-------|------|
| `normalized_alias` | 100% |
| `language` | **0 / 28474 (W1)** |
| `region` non-null | 12,865 (45.2%); NULL 15,609 (54.8%) |
| `source` | 100% (`infoods` 9627, `ontology` 6985, `usda` 6715, `ifct` 2986, `fssai` 2151, `e_number_catalog` 10) |
| `alias_type` | `common` 28467, `e_number` 7 |
| unique `(normalized_alias, region)` non-code | **0 dups** |

Language/region rule: **every alias missing `language`** (critical-if-literal; recorded as **W1** because NULL region is the GLOBAL design and language was never wired).

### 2.5 Live `ike2_unknown_queue` — 33,391 rows

| Field | Fill |
|-------|------|
| `normalized_key` | 100% unique |
| `status` | pending 33390, resolved 1 |
| `enrichment` | 100% |
| `classification_decision` | 1 (the resolved row) |
| `frequency` > 1 | 17,875 |

### 2.6 Live `ike2_restriction_rules` — 58 rows

All `value` filled; all `region` NULL. Categories cover allergens, medical, vegan/vegetarian variants, Jain, Halal, Kosher, pescatarian, enzyme-animal. No regional variants.

### 2.7 Live `users` — 1 row

`name`/`email`/`diet_type` filled; `allergies` empty array.

---

## 3. Regions and national staples

### 3.1 Counts by region tag

Groups have **no** `region` column. Counts are from `ike2_aliases.region` (NULL = GLOBAL).

| Region tag | Aliases | Distinct groups via those aliases |
|------------|---------|-----------------------------------|
| (null / GLOBAL) | 15609 | 5235 |
| IN | 7500 | 1536 |
| US | 1115 | 91 |
| BR | 916 | 37 |
| IT | 532 | 16 |
| NG | 489 | 21 |
| MW | 488 | 35 |
| CA | 300 | 12 |
| MX | 286 | 11 |
| TZ | 264 | 15 |
| AU | 228 | 7 |
| EU | 190 | 185 |
| FR | 129 | 8 |
| IS | 126 | 7 |
| DE | 122 | 2 |
| UK | 82 | 4 |
| IE | 69 | 2 |
| NZ | 25 | 4 |
| India (unnormalized) | 4 | 1 |
| **JP** | **0** | **0** |
| **AE / UAE** | **0** | **0** |

L2 `ontology.json` `regions`: IN 221, EU 185, US 1, India 1 (most rows untagged).

### 3.2 License-checked lists used (no new ingest)

From `backend/core/knowledge/ike2/etl/license_allowlist.json` **and** files already in repo:

| List | License | Path | Used as staple source |
|------|---------|------|------------------------|
| produce catalog seed | CC0-1.0 | `backend/core/knowledge/ike2/etl/adapters/seeds/produce_catalog_seed.json` (8) | yes (Global + IN tags) |
| animal catalog seed | CC0-1.0 | `.../animal_catalog_seed.json` (7) | yes |
| INFOODS AnFooD | CC-BY-4.0 | `data/layer1_infoods_anfood.json` (621) | yes, filtered by `regions` |
| commodity seed lists | none (in-repo grocery) | `data/commodity_seed_lists/{expanded_grocery,identity_expand,variant_recall}.txt` | yes, Global overlay (user-requested) |
| CoFID | OGL-UK-3.0 | **no dump in repo** | not used |
| Canadian Nutrient File | OGL-Canada-2.0 | **no dump in repo** | not used |

INFOODS region tags on canonicals include Global, US, IN, CA, AU, NZ, plus BR/FR/IT/… — **not JP or AE**.

In-repo but **not** treated as verified staples: `layer1_nin.json` / `layer1_ifct.json` / `layer1_fssai.json` (IN, not on `source_licenses`), `layer1_foodex2.json` (EU tags, not allowlisted), `layer1_fda_gras.json` (US chemicals, not a staple food list).

### 3.3 Resolution method (read-only)

For each staple name, without calling `resolve()`:

1. `normalize_ingredient_key` + synonymy ladder (`variant_aliases` + `commodity_head`) — same candidates as the resolver, **no L5 enqueue**
2. L1 = `truth_anchor.lookup`
3. else L2 = `local_ontology.lookup`
4. else L3 = alias/canonical present in live DB (GLOBAL or matching region tag)

### 3.4 Per-region staple resolution

Staple set = produce/animal seeds (Global) + INFOODS rows tagged with that region or Global + commodity grocery overlay.

| Region | Status | n | L1 | L2 | L3 | Unresolved |
|--------|--------|---|----|----|----|------------|
| IN | checked | 1122 | 125 | 650 | 347 | **0** |
| US | checked | 1179 | 128 | 652 | 399 | **0** |
| CA | checked | 1112 | 125 | 648 | 339 | **0** |
| UK | checked (Global overlay only; **no CoFID pack**) | 1108 | 124 | 648 | 336 | **0** |
| EU | checked (Global overlay only; FoodEx2 not license-checked) | 1106 | 124 | 648 | 334 | **0** |
| AU | checked | 1110 | 124 | 648 | 338 | **0** |
| NZ | checked | 1110 | 124 | 648 | 338 | **0** |
| JP | **UNVERIFIED** | — | — | — | — | no citable Japan staple list in repo; **do not ingest** |
| AE | **`verified=false`** | — | — | — | — | no UAE pack; policy UAE verified=false; **do not ingest** |

Unresolved staples for IN/US/CA/UK/EU/AU/NZ against those cited lists: **none**. Coverage is overwhelmingly L2 local ontology + L3 USDA/INFOODS aliases, not L1.

Caveats:

- Zero unresolved does **not** mean national packs exist. UK/EU are grocery+Global CC0, not CoFID/FoodEx2.
- L3 US group count via US-tagged aliases is only **91**; most US staples hit GLOBAL aliases or L2.
- JP/AE have **zero** alias tags in this DB.

---

## Method notes

- Worktree: `/Users/divyam/.cursor/worktrees/IngreSure/g2-completeness` on `feat/g2-completeness-report` (main checkout was on `fix/parse-and-backtrack`).
- `docs/` is gitignored (`# Markdown / docs (local only — not on GitHub)`). This file is force-added so the report can live on the branch.
- Parser and verdict code were not modified.
- No `git push`. No merge.
