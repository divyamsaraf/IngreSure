# IngreSure Backend

FastAPI-powered backend with a hybrid rule + LLM architecture for food safety compliance.

## Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

## Running

The frontend chat page proxies to this backend. For the **premium ingredient audit UI** (summary pills, grouped cards, “Read more” explanation), the backend must be running so it can emit `<<<INGREDIENT_AUDIT>>>` JSON in the stream.

```bash
# Development (with hot reload)
USE_NEW_ENGINE=true uvicorn app:app --reload --host 0.0.0.0 --port 8000

# With shadow mode (compares legacy vs new engine)
USE_NEW_ENGINE=true SHADOW_MODE=true uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## Architecture

```
User Query
    ↓
Rule-based Intent Detector (2ms)
    ↓ fallback if ambiguous
LLM Intent Extractor (~3s, via Ollama)
    ↓
Deterministic Compliance Engine (never LLM)
    ↓
LLM Response Composer (fallback: templates)
```

### Key Modules

| Module | File | Purpose |
|--------|------|---------|
| Intent Detector | `core/intent_detector.py` | Rule-based NLU for query parsing |
| LLM Intent | `core/llm_intent.py` | Ollama-powered fallback for ambiguous queries |
| LLM Response | `core/llm_response.py` | Natural language response generation |
| Templates | `core/response_composer.py` | Deterministic template responses (fallback) |
| Compliance | `core/evaluation/compliance_engine.py` | Safety evaluation against restrictions |
| Ontology | `core/ontology/ingredient_registry.py` | Ingredient lookup + external API enrichment |
| Restrictions | `core/restrictions/restriction_registry.py` | Dietary rule evaluation |
| Profile | `core/profile_storage.py` | Persistent user profile storage |
| USDA API | `core/external_apis/usda_fdc.py` | USDA FoodData Central connector |
| OFF API | `core/external_apis/open_food_facts.py` | Open Food Facts connector |
| PubChem/ChEBI | `core/external_apis/pubchem.py`, `chebi.py` | Scientific/chemical ingredient lookup |
| Wikidata | `core/external_apis/wikidata_api.py` | Synonym and regional name resolution |
| Knowledge DB | `core/knowledge/ingredient_db.py` | Canonical groups, aliases, unknown_ingredients |
| Merge | `core/knowledge/merge.py` | Group-merge and alias consolidation |
| Ingest | `core/knowledge/ingest.py` | Layer 1 curated ingestion (USDA, OFF, FAO, IFCT) |

### Hybrid ingredient knowledge (global coverage)

- **Migration**: `supabase/migrations/20260305000000_ingredient_knowledge_extend.sql` extends `ingredients.source` (fao, ifct, indb, chebi, dbpedia, foodb, uniprot) and adds `ingredient_aliases.region`. Apply with `supabase db reset` (local) or `supabase db push` / SQL Editor (remote).
- **Unknowns → DB**: When Supabase is configured, unknown ingredients are written to `unknown_ingredients`; the worker enriches them via USDA → OFF → PubChem → ChEBI → Wikidata.
- **Seed**: `python seed_ingredient_knowledge.py` (from backend) seeds from `data/ontology.json`. Requires `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in `.env`. For **local Supabase**, get keys with `supabase status -o json` (use `API_URL` and `SERVICE_ROLE_KEY`).
- **Verify**: `python scripts/verify_knowledge_flow.py` checks normalizer, parser, resolver, and unknown→DB.
- **Enrich unknowns (no Celery)**: `python scripts/run_enrich_unknown_once.py [limit]` runs one batch of enrichment (read `unknown_ingredients`, call APIs, upsert groups/ingredients/aliases, mark resolved). Default limit 10.
- **Worker**: Celery task `enrich_unknown_batch` (or script `scripts/run_enrich_unknown_once.py` without Redis) reads `unknown_ingredients`, enriches via USDA→OFF→PubChem→ChEBI→Wikidata, upserts groups/ingredients/aliases; optional LLM classification for medium-confidence results. Task `process_product_ingredients_batch(ingredient_strings)` flattens product labels and resolves or enqueues tokens.
- **Merge**: Use `core.knowledge.merge.merge_groups(client, keeper_group_id, [mergee_id, ...])` and `add_aliases_to_group(...)` to consolidate same substance from multiple sources.

### Local development (ingredient knowledge)

1. **Start Supabase**: `supabase start` (from repo root).
2. **Env**: In `backend/.env` set `SUPABASE_URL=http://127.0.0.1:54321`, `SUPABASE_SERVICE_ROLE_KEY=<from supabase status -o json>`, and `USE_KNOWLEDGE_DB=true`.
3. **Seed**: `cd backend && python seed_ingredient_knowledge.py`.
4. **Verify**: `python scripts/verify_knowledge_flow.py`. To check Supabase connectivity only: `python scripts/verify_supabase.py`.
5. **Enrich unknowns (no worker)**: `python scripts/run_enrich_unknown_once.py [limit]`.
6. **Add test unknowns + enrich**: `python scripts/add_test_unknowns_and_enrich.py` (adds pitaya, tahini, etc., then runs one batch).
7. **With Celery**: Start Redis + worker (`docker-compose up -d redis && docker-compose run --rm worker`), then run `python scripts/trigger_enrich_batch.py 20` with `REDIS_URL=redis://localhost:6379/0` to send the task; without REDIS_URL it runs one batch inline.
8. **Local .env**: From repo root with Supabase running, `python backend/scripts/setup_local_supabase_env.py` appends local SUPABASE_URL and SERVICE_ROLE_KEY to backend/.env if missing.
9. **Merge duplicate groups**: `python scripts/merge_groups_example.py --dry-run chickpea chana "garbanzo bean"` to preview; omit `--dry-run` to merge those groups into the keeper (chickpea).

## Testing

```bash
# All tests (409+)
python3 -m pytest tests/ -v

# Specific suites
python3 -m pytest tests/test_intent_detector.py -v
python3 -m pytest tests/test_restrictions_comprehensive.py -v
python3 -m pytest tests/test_compliance_engine.py -v
python3 -m pytest tests/test_external_apis.py -v
```

## Verify all APIs and services (one script)

From repo root or backend directory:

```bash
python backend/scripts/verify_all_health.py
```

This checks: backend /health, external APIs (USDA/OFF/PubChem/ChEBI/Wikidata), Supabase, Redis, regional resolution (bajra → pearl millet), and POST /chat/grocery with "bajra". Exit 0 = all passed.

## Verify Supabase (is it working?)

From the backend directory:

```bash
python scripts/verify_supabase.py
```

- **OK**: Supabase is reachable; knowledge DB and unknown_ingredients will work.
- **FAIL (Name or service not known)** when the backend runs in Docker:
  1. Start Supabase on the **host**: `supabase start` (from repo root).
  2. In `backend/.env`: `SUPABASE_URL=http://127.0.0.1:54321` and `SUPABASE_SERVICE_ROLE_KEY=<from supabase status -o json>`.
  3. Compose sets `RUNNING_IN_DOCKER=1` so the URL is rewritten to `host.docker.internal:54321` inside the container.
  4. Ensure `docker-compose.yml` has `extra_hosts: [host.docker.internal:host-gateway]` for the backend (and worker) service.

If you don't use Supabase, leave `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` unset; the app runs without the knowledge DB (unknowns are logged to JSON only).

## Dependencies

- **Ollama** (llama3.2:3b) — local LLM for intent extraction and response generation
- **USDA FDC API** (optional) — external ingredient lookup
- **Open Food Facts** (optional) — additional ingredient data source
- **Supabase** (optional) — for ingredient knowledge DB and other features

## Production readiness (ingredient knowledge)

- **Tests**: Full suite (413 tests) passes. Schema, resolution, parser, APIs, and worker paths are covered.
- **Known limits**: (1) External APIs (USDA, OFF, PubChem, ChEBI, Wikidata) have rate limits; use caching and batch jobs. (2) LLM classification in the worker requires Ollama; if unavailable, enrichment still runs without classification. (3) Apply migration `20260305000000_ingredient_knowledge_extend.sql` before using extended `ingredients.source` values. (4) For production DB, run migrations in order and seed/ingest as needed; set `USE_KNOWLEDGE_DB=true` only when the knowledge tables are populated.
