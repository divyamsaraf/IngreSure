# System State Audit

**Point-in-time snapshot (2026-08-06).** Later gap analyses diff against this file; do not rewrite it to match today. Several things it names have since been removed: the Redis resolve cache, `lifecycle.py`, `compliance_engine.py`, and `IKE2_MODE`.

**Date:** 2026-08-06  
**Scope:** Read-only investigation of repository structure, schema, entities, ingestion, IKE-2/legacy paths, API surface, tests, gaps, and named specs.  
**Method:** Migration SQL as schema source of truth; live Supabase at `127.0.0.1:54321` was not reachable (connection refused), so row counts are unavailable.

---

## 1. REPO STRUCTURE

```
IngreSure/
├── backend/                    # ACTIVE — FastAPI app, IKE-2, legacy engine, ETL, tests
│   ├── app.py
│   ├── core/
│   │   ├── api/v1/             # ACTIVE — public /api/v1 routes
│   │   ├── cache/              # ACTIVE — Redis resolution helpers
│   │   ├── enrichment/         # ACTIVE — unknown log / dynamic ontology
│   │   ├── evaluation/         # ACTIVE — legacy ComplianceEngine
│   │   ├── external_apis/      # ACTIVE — live enrichment fetchers
│   │   ├── knowledge/          # ACTIVE — registry, DB, ike2/, lifecycle
│   │   ├── models/
│   │   ├── normalization/
│   │   ├── ontology/           # ACTIVE — legacy ontology schema/registry
│   │   ├── parsing/
│   │   ├── restrictions/       # ACTIVE — legacy restriction JSON engine
│   │   ├── security/
│   │   ├── bridge.py           # ACTIVE — chat → IKE-2 + shadow scheduling
│   │   └── …
│   ├── data/                   # ACTIVE — local USDA/OFF/India catalogs for scripts
│   ├── docs/                   # docs (backend-local)
│   ├── scripts/                # ACTIVE — ETL/verify CLIs (manual)
│   ├── tests/                  # ACTIVE — pytest suite
│   └── worker/                 # ACTIVE code, NO cron schedule wired
├── frontend/                   # ACTIVE — Next.js app
│   ├── src/app/                # pages + BFF API routes
│   ├── src/components/
│   │   ├── home/               # ACTIVE homepage
│   │   └── home/legacy/        # UNUSED/DEPRECATED landing components (kept, not primary)
│   ├── src/{hooks,lib,types,theme,constants,context}/
│   └── public/
├── supabase/
│   ├── migrations/             # ACTIVE — schema source of truth (16 SQL files)
│   ├── functions/              # EMPTY — no edge functions
│   ├── seed.sql
│   └── config.toml
├── data/                       # ACTIVE — ontology.json, layer1_*.json, staging, catalogs
│   ├── layer1_*.json           # 12 Layer-1 dumps
│   ├── ontology.json (+ .bak / truncated backups)
│   ├── e_number_catalog.json, *_staging.json, …
│   ├── commodity_seed_lists/
│   ├── coverage_os/
│   └── raw/
├── scripts/                    # ACTIVE — download_*.sh, dev-local, e2e
├── docs/                       # ACTIVE docs + historical analysis reports
│   └── superpowers/{plans,specs}/  # design/plan history (not runtime)
├── database/                   # POINTER ONLY — README → supabase/migrations
├── deploy/                     # Caddyfile.example only
├── design-system/ingresure/    # Design artifacts (MASTER.md, pages/) — not runtime
├── .github/workflows/ci.yml    # ACTIVE CI
├── docker-compose.yml
├── .agents/, .cursor/, .claude/  # Tooling/skills — not product runtime
├── README.md, QUICKSTART.md, PHASES.md, PROJECT_DETAILS.md, DEPLOY.md, …
└── vercel.json
```

| Area | Status |
|------|--------|
| `backend/core/knowledge/ike2/` | Active primary compliance path for chat |
| `backend/core/evaluation/`, `ontology/`, `restrictions/` | Still active (legacy engine; used by shadow + `/api/v1` evaluate) |
| `frontend/src/components/home/legacy/` | Looks unused relative to current homepage |
| Menu/restaurant tables | Dropped in migrations (see §2) |
| `supabase/functions/` | Empty |
| `database/` | Docs only |
| Root `docs/*ANALYSIS*`, `VERIFICATION_*` | Historical reports, not specs for current build |

---

## 2. DATABASE SCHEMA

Source: `supabase/migrations/` applied in chronological order.  
**Live row counts:** not available — local Supabase (`SUPABASE_URL=http://127.0.0.1:54321`) refused connections at audit time.

**Extensions:** `vector`, `pg_trgm`  
**Enum:** `ike2_knowledge_state` = `UNCLASSIFIED | DISCOVERED | AUTO_CLASSIFIED | VERIFIED | LOCKED | DEPRECATED`  
**View:** `public.ike2_v_alias_resolution` (aliases → active ingredients → non-DEPRECATED groups)  
**Dropped (migration `20260306100000`):** `embeddings`, `tag_history`, `verification_logs`, `item_ingredients`, `menu_items`, `verified_items`, `restaurant_submissions`

### 2.1 `public.users`

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | FK → `auth.users` |
| `name` | text | |
| `email` | text UNIQUE | |
| `allergies` | jsonb DEFAULT `'[]'` | |
| `diet_type` | text | |
| `preferences` | jsonb DEFAULT `'{}'` | |
| `created_at` | timestamptz DEFAULT utc now | |

RLS: `users_select_own`, `users_update_own`.

### 2.2 `public.ingredient_groups` (legacy knowledge)

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK DEFAULT `gen_random_uuid()` | |
| `canonical_name` | text NOT NULL | partial unique where `superseded_by IS NULL` |
| `origin_type` | text | CHECK plant/animal/synthetic/microbial/fungal/insect/unknown |
| `animal_species` | text | |
| `animal_origin`, `plant_origin`, `synthetic`, `fungal`, `insect_derived` | boolean DEFAULT false | |
| `egg_source`, `dairy_source`, `gluten_source`, `soy_source`, `sesame_source` | boolean DEFAULT false | |
| `nut_source` | text | |
| `alcohol_content` | double precision | |
| `root_vegetable`, `onion_source`, `garlic_source`, `fermented` | boolean DEFAULT false | |
| `knowledge_state` | text NOT NULL DEFAULT `'UNKNOWN'` | CHECK UNKNOWN/DISCOVERED/AUTO_CLASSIFIED/VERIFIED/LOCKED |
| `version` | integer NOT NULL DEFAULT 1 | |
| `superseded_by` | uuid FK → `ingredient_groups(id)` | |
| `uncertainty_flags`, `derived_from`, `contains`, `may_contain`, `regions` | jsonb DEFAULT `'[]'` | |
| `created_at`, `updated_at` | timestamptz | |

Indexes: `idx_ingredient_groups_canonical_active`, `idx_ingredient_groups_state`, `idx_ingredient_groups_origin`. RLS ON, no policies.

### 2.3 `public.ingredients` (legacy)

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `name` | text NOT NULL | |
| `normalized_name` | text NOT NULL | partial unique where active |
| `group_id` | uuid NOT NULL FK → `ingredient_groups` | |
| `source` | text NOT NULL | CHECK includes ontology/usda_fdc/open_food_facts/fao/ifct/indb/pubchem/chebi/wikidata/dbpedia/foodb/fda_gras/foodex2/fssai/nin/uniprot/admin/system |
| `confidence` | text NOT NULL DEFAULT `'high'` | high/medium/low |
| `version` | integer NOT NULL DEFAULT 1 | |
| `superseded_by` | uuid FK → `ingredients` | |
| `created_at` | timestamptz | |

Indexes: `idx_ingredients_normalized_active`, `idx_ingredients_group_id`, `idx_ingredients_source`.

### 2.4 `public.ingredient_aliases` (legacy)

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `alias` | text NOT NULL | |
| `normalized_alias` | text NOT NULL UNIQUE (`idx_aliases_normalized_unique`) | |
| `ingredient_id` | uuid NOT NULL FK → `ingredients` ON DELETE CASCADE | |
| `alias_type` | text NOT NULL DEFAULT `'synonym'` | CHECK canonical/synonym/e_number/brand_name/regional/misspelling/abbreviation/scientific |
| `language` | text NOT NULL DEFAULT `'en'` | |
| `region` | text | added in `20260305000000` |
| `created_at` | timestamptz | |

### 2.5 `public.unknown_ingredients` (legacy queue; still used by enrichment)

| Column | Type |
|--------|------|
| `id` | uuid PK |
| `normalized_key` | text NOT NULL UNIQUE |
| `raw_inputs` | jsonb DEFAULT `'[]'` |
| `frequency` | integer NOT NULL DEFAULT 1 |
| `first_seen`, `last_seen` | timestamptz |
| `resolved` | boolean NOT NULL DEFAULT false |
| `resolved_group_id` | uuid FK → `ingredient_groups` |
| `resolution_source` | text |
| `resolution_attempts` | integer NOT NULL DEFAULT 0 |
| `last_attempt_at` | timestamptz |
| `restriction_ids_sample` | jsonb DEFAULT `'[]'` |
| `profile_context_sample` | jsonb |

Index: `idx_unknown_pending` on `(resolved, resolution_attempts, frequency DESC) WHERE resolved = false`.

### 2.6 `public.enrichment_metrics`

| Column | Type |
|--------|------|
| `id` | uuid PK |
| `date` | date NOT NULL UNIQUE |
| `total_queries`, `resolved_static`, `resolved_cache`, `resolved_db`, `resolved_api`, `unresolved` | integer DEFAULT 0 |
| `avg_resolution_time_ms`, `coverage_percent` | double precision |
| `new_groups_created`, `new_aliases_added` | integer DEFAULT 0 |
| `created_at` | timestamptz |

### 2.7 `public.request_history`

| Column | Type |
|--------|------|
| `id` | uuid PK |
| `created_at` | timestamptz DEFAULT now |
| `started_at` | timestamptz NOT NULL |
| `completed_at` | timestamptz |
| `duration_ms` | integer |
| `user_id` | text |
| `route` | text NOT NULL |
| `status` | integer NOT NULL |
| `error_code` | text |
| `user_input`, `output_text` | text |
| `metadata`, `profile_update` | jsonb |

Indexes on `started_at`, `completed_at`, `(user_id, started_at)`, `(route, started_at)`. RLS ON, no policies.

### 2.8 `public.ike2_ingredient_groups`

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `canonical_name` | text NOT NULL UNIQUE | |
| `slug` | text | |
| Origin/allergen bools (NOT NULL DEFAULT false) | `animal_origin`, `plant_origin`, `synthetic`, `fungal`, `insect_derived`, `bee_product` (added `20260720000000`), `egg_source`, `dairy_source`, `gluten_source`, `soy_source`, `sesame_source`, `peanut_source`, `tree_nut_source`, `fish_source`, `shellfish_source`, `mustard_source`, `celery_source`, `lupin_source`, `sulphite_source`, `root_vegetable`, `onion_source`, `garlic_source`, `fermented` | |
| `animal_species` | text | |
| `alcohol_content` | numeric | |
| `alcohol_role` | text NOT NULL DEFAULT `'none'` | CHECK none/ingredient/fermentation_trace |
| `knowledge_state` | `ike2_knowledge_state` NOT NULL DEFAULT `'UNCLASSIFIED'` | |
| `classification_method`, `verdict_cap`, `primary_source_url` | text | |
| `uncertainty_flags` | text[] NOT NULL DEFAULT `'{}'` | |
| `superseded_by` | uuid FK → self | |
| `created_at`, `updated_at` | timestamptz | |
| `version` | integer NOT NULL DEFAULT 1 | |

CHECKs include implication constraints (`insect_implies_animal`, `egg_implies_animal`, `dairy_implies_animal`, `fish_implies_animal`, `shellfish_implies_animal`, `bee_product_implies_animal`, `bee_product_not_insect_derived`, `verified_requires_source`, `dual_origin_requires_uncertainty`).

### 2.9 `public.ike2_ingredients`

| Column | Type |
|--------|------|
| `id` | uuid PK |
| `group_id` | uuid NOT NULL FK → `ike2_ingredient_groups` ON DELETE CASCADE |
| `normalized_name` | text NOT NULL |
| `source` | text |
| `superseded_by` | uuid FK → self |
| `created_at` | timestamptz |

Indexes: `ike2_ingredients_group_idx`, `ike2_ingredients_norm_idx`.

### 2.10 `public.ike2_aliases`

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `normalized_alias` | text NOT NULL | |
| `ingredient_id` | uuid NOT NULL FK → `ike2_ingredients` ON DELETE CASCADE | |
| `alias_type` | text NOT NULL DEFAULT `'common'` | CHECK common/brand/regional/misspelling/e_number/cas_number/fda_number/iupac_name |
| `language`, `region`, `source` | text | |
| `match_confidence` | text NOT NULL DEFAULT `'high'` | CHECK exact/high/possible |
| `created_at` | timestamptz | |

Unique indexes: `ike2_aliases_global_code_uidx`, `ike2_aliases_region_uidx`.

### 2.11 `public.ike2_alias_disambiguation`

| Column | Type |
|--------|------|
| `id` | uuid PK |
| `normalized_alias` | text NOT NULL |
| `context_region` | text |
| `ingredient_id` | uuid NOT NULL FK → `ike2_ingredients` ON DELETE CASCADE |
| `priority` | integer NOT NULL DEFAULT 0 |
| `notes` | text |

Index: `ike2_alias_disambig_idx`.

### 2.12 `public.ike2_restriction_rules`

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid PK | |
| `category` | text NOT NULL | |
| `field` | text NOT NULL | |
| `operator` | text NOT NULL DEFAULT `'eq'` | |
| `value` | text | |
| `action` | text NOT NULL | CHECK FAIL/WARN |
| `min_knowledge_state` | `ike2_knowledge_state` NOT NULL DEFAULT `'AUTO_CLASSIFIED'` | |
| `region` | text | |
| `version` | integer NOT NULL DEFAULT 1 | |

Unique: `ike2_restriction_rules_uidx` on `(category, field, coalesce(region,'GLOBAL'))`.

### 2.13 `public.ike2_resolution_cache`

| Column | Type |
|--------|------|
| `id` | uuid PK |
| `normalized_key` | text NOT NULL |
| `region` | text |
| `resolved` | jsonb |
| `created_at` | timestamptz |

No unique constraint beyond PK. Hot path uses in-process cache, not this table for reads.

### 2.14 `public.ike2_unknown_queue`

| Column | Type |
|--------|------|
| `id` | uuid PK |
| `normalized_key` | text NOT NULL UNIQUE |
| `frequency` | integer NOT NULL DEFAULT 1 |
| `enrichment` | jsonb |
| `classification_decision` | text |
| `status` | text NOT NULL DEFAULT `'pending'` |
| `created_at`, `updated_at` | timestamptz |

### 2.15 `public.ike2_shadow_diffs`

| Column | Type |
|--------|------|
| `id` | uuid PK |
| `raw_input` | text |
| `legacy_verdict` | text |
| `ike2_verdict` | text |
| `match` | boolean |
| `false_safe_regression` | boolean NOT NULL DEFAULT false |
| `detail` | jsonb |
| `created_at` | timestamptz |

### 2.16 `public.ike2_group_merges`

| Column | Type |
|--------|------|
| `id` | uuid PK |
| `from_group_id`, `into_group_id` | uuid (no FK) |
| `rollback_snapshot` | jsonb |
| `created_at` | timestamptz |

### 2.17 `ike2_staging.ingredient_groups`

| Column | Type |
|--------|------|
| `id` | uuid PK |
| `source` | text |
| `raw` | jsonb |
| `created_at` | timestamptz |

RLS not enabled in migrations.

### 2.18 `ike2_staging.stg_rejects`

| Column | Type |
|--------|------|
| `id` | uuid PK |
| `source` | text |
| `raw` | jsonb |
| `violated_constraint` | text |
| `created_at` | timestamptz |

**Living table count:** 15 `public` + 2 `ike2_staging` = **17**.

---

## 3. CORE ENTITIES

None of the six PascalCase names exist as Python/TypeScript classes. Actual definitions:

### 3.1 IngredientGroup

**Closest (IKE-2 canonical):** table `ike2_ingredient_groups` — columns listed in §2.8.  
**Legacy:** table `ingredient_groups` — §2.2.  
**Python:** no `IngredientGroup` class; ETL uses `_GROUP_COLUMNS` in `backend/core/knowledge/ike2/etl/bulk_inject.py`; runtime often `TruthAnchorFact` / `SimpleNamespace` (`GroupRow` alias in `stores/db.py`).

### 3.2 Ingredient

**Python dataclass** `Ingredient` in `backend/core/ontology/ingredient_schema.py`:

| Field | Type |
|-------|------|
| `id` | `str` |
| `canonical_name` | `str` |
| `aliases` | `list[str]` |
| `derived_from`, `contains`, `may_contain` | `list[str]` |
| `animal_origin`, `plant_origin`, `synthetic`, `fungal`, `insect_derived`, `bee_product` | `bool` |
| `animal_species` | `Optional[str]` |
| `egg_source`, `dairy_source`, `gluten_source`, `soy_source`, `sesame_source` | `bool` |
| `nut_source` | `Optional[str]` |
| `alcohol_content` | `Optional[float]` |
| `root_vegetable`, `onion_source`, `garlic_source`, `fermented` | `bool` |
| `uncertainty_flags`, `regions` | `list[str]` |
| Properties | `meat_fish_derived`, `meat_land_derived` |

**IKE-2 SQL:** `ike2_ingredients` — `id`, `group_id`, `normalized_name`, `source`, `superseded_by`, `created_at` (§2.9).  
**Legacy SQL:** `ingredients` — §2.3.  
**IKE-2 compliance fact:** `TruthAnchorFact(canonical_name, flags, knowledge_state)` in `truth_anchor.py`.

### 3.3 Alias

**No class named `Alias`.**  
**IKE-2:** `ike2_aliases` — §2.10 (+ `ike2_alias_disambiguation` §2.11).  
**Legacy:** `ingredient_aliases` — §2.4.

### 3.4 RestrictionRule

**No class named `RestrictionRule`.**  
**SQL:** `ike2_restriction_rules` — §2.12.  
**Python:** `RULE_SEED` dicts + `_to_rule()` → `SimpleNamespace` with fields `restriction`, `kind`, `trigger_flag`, `match_value`, `action`, `min_knowledge_state` (`backend/core/knowledge/ike2/rules.py`).  
No legacy `restriction_rules` table (legacy uses `data/restrictions.json` + `core/restrictions/`).

### 3.5 ResolutionCache

**No class named `ResolutionCache`.**  
**Hot path:** module-level `_CACHE: dict[str, ResolvedIngredient]` in `backend/core/knowledge/ike2/resolution_cache.py`.  
**`ResolvedIngredient` dataclass:** `group`, `source`, `confidence_band`, `trusted`, `resolution_layer`, `status` (`Literal["resolved","uncertain"]`), `miss_class: Optional[str]`.  
**SQL audit table:** `ike2_resolution_cache` — §2.13 (write-oriented; not used for hot-path reads).  
**Legacy Redis:** `backend/core/cache/redis_resolution.py` (`resolution_cache_get` / `resolution_cache_set`).

### 3.6 UnknownIngredientQueue

**No type named `UnknownIngredientQueue`.**  
**IKE-2 SQL:** `ike2_unknown_queue` — §2.14.  
**Legacy (actively used by worker/enrichment):** `unknown_ingredients` — §2.5.  
**Python JSON log:** `UnknownIngredientsLog` in `backend/core/enrichment/unknown_log.py`.

---

## 4. DATA SOURCES / INGESTION

**Pattern:** No single ABC/Protocol for all sources. Shared pieces:

- String registries: `backend/core/knowledge/ike2/etl/sources.py`, `reconcile._SOURCE_TIER`
- Generic Layer-1 adapter: `ike2/etl/adapt.py` (`map_record`)
- E-number adapter: `ike2/etl/adapt_e_number.py`
- Live enrich shared type: `EnrichmentResult` in `external_apis/base.py`
- Celery: `worker/tasks.py` has `enrich_unknown_batch`, `process_product_ingredients_batch` — **no `beat_schedule` / cron**

### Wired sources

| Source | Code locations | Pattern | Trigger |
|--------|----------------|---------|---------|
| **USDA FDC** | `scripts/download_tier1_data.sh`; `transform_usda_fdc_bulk.py`; `parse_usda_bulk.py`; `external_apis/usda_fdc.py` | Bespoke transform + EnrichmentResult live; Layer-1 → `adapt.map_record` | Manual shell/CLI; live on resolve/Celery |
| **Open Food Facts** | `download_tier1_data.sh`; `transform_off_taxonomy.py`; `parse_off_taxonomy.py`; `open_food_facts.py` | Same hybrid | Manual; live enrich |
| **Wikidata** | `download_sources_3_4.sh`; `fetch_wikidata_batch.py`; `transform_wikidata_batch.py`; `fetch_wikidata_ingredients.py`; `wikidata_api.py` / `wikidata_sparql.py` | Bespoke + shared adapters | Manual; live enrich |
| **ChEBI** | `download_sources_3_4.sh`; `transform_chebi_bulk.py`; `chebi.py` | Bespoke bulk; EnrichmentResult live | Manual; live enrich |
| **E-number catalog** | `data/e_number_catalog.json`; `ike2/e_number_catalog.py`; `generate_ike2_e_numbers.py`; `adapt_e_number.py`; `merge_all_sources.py` / `scripts/merge_e_numbers_to_ontology.py` | **Only dedicated IKE-2 adapter** | Manual CLI (`bulk_inject --source e_number_catalog`, generate, merge) |
| **India catalog** | `backend/data/india_ingredients_catalog.json` via `merge_all_sources.py` only | Bespoke curated JSON → ontology | Manual `merge_all_sources.py` |
| **FDA GRAS** | `download_sources_5_6.sh`; `fda_fdcc.py`; `transform_fda_gras_bulk.py`; `data/fda_gras_manual_us.json` | Bespoke; no live per-ingredient API | Manual shell/CLI |
| **FoodEx2** | `download_sources_5_6.sh`; `transform_foodex2_bulk.py` | Fully bespoke | Manual |
| **PubChem** | `download_sources_7.sh`; `pubchem_batch.py`; `fetch_pubchem_batch.py`; `transform_pubchem_batch.py`; `pubchem.py` | Bespoke batch + live EnrichmentResult | Manual; live enrich |
| **FSSAI** | `download_sources_8_9_10.sh`; `fssai_regulations.py`; `extract_fssai_additives.py`; `transform_fssai_bulk.py` | Bespoke PDF extract | Manual |
| **NIN** | curated `data/nin_indian_ingredients.json`; `transform_nin_bulk.py` | Bespoke curated | Manual |
| **IFCT 2017** | `download_sources_8_9_10.sh`; `transform_ifct_bulk.py` | Bespoke | Manual |
| **Ontology seed** | `data/ontology.json`; `ike2/etl/load_ontology.py`; `seed_ike2_ontology.py` | High-trust seed path | Manual seed/inject |

**Live enrichment order** (`external_apis/fetcher.py`): USDA → Open Food Facts → PubChem → ChEBI → Wikidata.

**Allowed in DB CHECK but no ingest scripts found:** `fao`, `indb`, `dbpedia`, `foodb`, `uniprot`.

**Layer-1 load paths:** `bulk_inject` (IKE-2) and `ingest_layer1_json.py` (legacy knowledge DB).

---

## 5. IKE2_MODE AND LEGACY SYSTEM

### `IKE2_MODE`

| Location | Value / status |
|----------|----------------|
| `backend/.env` | `IKE2_MODE=shadow` |
| `backend/core/config.py` | **Not read** |
| `backend/.env.example` | **Absent** |
| Application code | **Never consulted** (only mentioned in `tests/ike2/test_shadow_runner.py` docstring: “No IKE2_MODE check”) |

**Effective runtime:** IKE-2 is always primary for chat (`bridge.run_new_engine_chat` → `_run_ike2_compliance`). On IKE-2 failure, fail-closed to `UNCERTAIN` — no legacy fallback for the user-facing verdict. Docs (`PHASES.md` Phase 7) still describe mode-gated soak/cutover; code has moved past that gate.

### Legacy engine + `ike2_shadow_diffs`

| Component | Role |
|-----------|------|
| `core/evaluation/compliance_engine.py` | Legacy `ComplianceEngine` still present |
| `core/knowledge/ike2/shadow/comparator.py` | `compare(legacy, ike2, raw_input)` → `match`, `false_safe_regression` |
| `core/knowledge/ike2/shadow/runner.py` | `run_legacy_diff` — always runnable; on mismatch inserts into `ike2_shadow_diffs` |
| `bridge._schedule_legacy_diff` | After every chat compliance run, fire-and-forget observational legacy comparison (capped timeout) |
| `scripts/ike2_shadow_soak_report.py` | Manual CLI over `ike2_shadow_diffs` (optional `--fail-on-regression`) |
| `/api/v1/evaluate-compliance`, `/api/v1/evaluate-product` | **Still call legacy `ComplianceEngine` live** |

Table `ike2_shadow_diffs` is present and written on mismatch only; soak report is not wired into GitHub Actions as a DB query (CI uses corpus shadow script separately).

---

## 6. API SURFACE

Router: `app.include_router(v1_router)` from `core.api.v1` (import failure is non-fatal warning).

### App (`backend/app.py`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service status JSON (`status`/`service`) |
| GET | `/health` | Health check including `ingredient_audit_emitter: true` |
| GET | `/config` | Profile options + `max_chat_message_length` for frontend |
| GET | `/anon-session` | Issue anonymous `user_id` (+ optional signed token) |
| GET | `/profile/{user_id}` | Load persisted profile (tenant isolation; default empty profile) |
| POST | `/profile` | Create/update profile (merge-only fields; tenant isolation) |
| POST | `/chat/grocery` | Streaming grocery safety chat (intent → profile → IKE-2 compliance → response/audit) |

### v1 (`backend/core/api/v1/routes.py`, prefix `/api/v1`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/resolve-ingredient` | Resolve one ingredient to canonical facts (no compliance) |
| GET | `/api/v1/ingredient/{name}` | Resolve by name (`try_api` query, default false) |
| POST | `/api/v1/evaluate-compliance` | Evaluate ingredient list vs `restriction_ids` via **legacy** `ComplianceEngine` |
| POST | `/api/v1/evaluate-product` | Parse label text then evaluate via **legacy** `ComplianceEngine` |

*(Frontend Next.js BFF routes under `frontend/src/app/api/*` proxy to the backend; not FastAPI.)*

---

## 7. TESTS

### Backend (`backend/tests`, pytest)

**Inventory (high level):**

| Area | Files / coverage |
|------|------------------|
| Root `tests/test_*.py` (~42 files) | Chat flow, compliance engine, enrichment, external APIs, intent, label parse/OCR/corpus, Redis cache, request history, security/tenancy, restrictions, stress labels, regressions |
| `tests/ike2/` (~70 `test_*.py` incl. coverage_os) | Resolver tiers, compliance, rules, seam, shadow, ETL adapt/inject/reconcile, e-numbers, goldens, audit matrix, schema constraints, stores |
| `tests/ike2/coverage_os/` | Phase 1 promote/hybrid gate/evidence; Phase 2a neutralize/role seed; Phase 2b induction |
| `tests/integration_test.py` | Ollama connection (returns value; pytest warns) |
| `tests/fixtures/`, `ike2/golden/` | Fixtures / golden corpora |

**Run (2026-08-06, full permissions, outside sandbox):**

```
1692 passed, 2530 warnings in 231.72s
```

**0 failed, 0 errors.**  
Note: an earlier sandboxed run showed 7 errors + 1 failure mid-progress (environment restrictions / tdd-guard write to `.claude/tdd-guard/data/test.json`); the clean re-run is authoritative.

### Frontend (Vitest)

| File | Focus |
|------|-------|
| `src/components/chat/ChatInterface.test.tsx` | Chat UI |
| `src/components/chat/FormattedMessage.test.tsx` | Message formatting |
| `src/components/chat/streamChatResponse.test.ts` | Stream protocol client |
| `src/types/userProfile.test.ts` | Profile types |

**Run:** `29 passed` (4 files) in ~1.6s.

---

## 8. KNOWN GAPS / TODOs

No literal `TODO` / `FIXME` / `HACK` markers found in `backend/**/*.py` or `frontend/src/**/*.{ts,tsx}`. Incomplete / stub paths observed:

| Location | Gap |
|----------|-----|
| `IKE2_MODE` in `.env` / `PHASES.md` | Documented mode gate; **code does not read it** |
| `core/profile_storage.py` | `USE_PROFILE_DB` “not implemented yet” (profiles stay on `data/profiles.json`) |
| `core/knowledge/lifecycle.py` | Scaffolding; comment says not wired into confidence engine (IKE-2 uses its own enum/table) |
| `coverage_os/auto_lane_guards.py` | “Phase 1 is log/stub only — no daemon” |
| `coverage_os/promote_writer.py` | `mirror_l3_stub` — “Phase 1 stub: L3 is a derived mirror, never source of truth” |
| `ike2/commodity_head.py` | Comment: geometry “not yet role-seeded (Phase 2a residual)” |
| `worker/celery_app.py` | Enrichment tasks exist; **no Celery Beat cron** for ingestion/enrichment |
| `/api/v1/evaluate-*` | Still on legacy engine while chat is on IKE-2 |
| `ike2_unknown_queue` vs `unknown_ingredients` | Dual queues; enrichment/worker path uses legacy table |
| `ike2_resolution_cache` SQL | Present but hot path is in-process `_CACHE` |
| FoodEx2 / PubChem / NIN / IFCT | In `ALLOWED_INGREDIENT_SOURCES` / Layer-1 dumps but missing or weak in IKE-2 `_SOURCE_TIER` / `_DEFAULT_STATE` |
| `fao`, `indb`, `dbpedia`, `foodb`, `uniprot` | Allowed source labels with no ingest wiring |
| `docs/SUPABASE_TABLES.md` | Outdated (omits `request_history` and all `ike2_*` tables) |
| `supabase/functions/` | Empty |
| Local Supabase | Down at audit time — no live row counts |
| `tests/integration_test.py::test_ollama_connection` | Returns `True` instead of asserting (PytestReturnNotNoneWarning) |

---

## 9. DEVIATION CHECK

**Files checked:**

- `docs/item1_ingestion_spec.md` — **does not exist**
- `docs/item2_entity_resolution_spec.md` — **does not exist**

No divergence list can be produced against those paths. Closest related design docs (not compared as the requested specs): `docs/superpowers/specs/2026-06-16-ike2-design.md`, `docs/superpowers/specs/2026-07-17-ike2-resolution-compliance-fix-design.md`, and ETL/coverage-os specs under `docs/superpowers/specs/`.

---

*End of audit.*
