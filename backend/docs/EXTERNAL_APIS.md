# External APIs and URLs

All endpoints used by the backend for verification and optional enrichment.

## Unknown ingredient → external API lookup (is it working?)

**Yes.** When an ingredient is not in the static or dynamic ontology:

1. **Compliance engine** (`core/evaluation/compliance_engine.py`) calls `resolve_with_fallback(raw, try_api=True, ...)` for each unknown.
2. **CanonicalResolver** (`core/knowledge/canonicalizer.py`) tries the knowledge DB (if enabled), then delegates to **IngredientRegistry.resolve_with_fallback**.
3. **IngredientRegistry** (`core/ontology/ingredient_registry.py`) calls **enrich_unknown_ingredient** from the fetcher when `try_api=True`.
4. **Fetcher** (`core/external_apis/fetcher.py`) runs **fetch_ingredient_from_apis** in order: **USDA FDC** → **Open Food Facts** → **PubChem** → **ChEBI** → **Wikidata**. The first good result is returned; on high confidence the ingredient is added to the dynamic ontology for future requests. **Cache**: only successful resolutions are cached (in-memory); "no result" is never cached, so unknown ingredients always trigger an external API search and you get the best/correct results.

Chat and scan both use `use_api_fallback=True`, so unknowns are looked up in real time. If all APIs fail or timeout, the ingredient is marked **UNCERTAIN** (not SAFE). To verify: use an ingredient that is not in the ontology (e.g. a regional name or chemical) and check logs for `ENRICHMENT usda_fdc`, `ENRICHMENT open_food_facts`, etc., or run `python scripts/check_external_apis.py`.

## Regional / multi-language ingredient names (auto-expansion)

USDA and Open Food Facts are English-centric. To support **any region or language** without manually maintaining a huge list:

1. **Static mappings** – `data/regional_ingredient_names.json` holds a curated list (e.g. bajra → pearl millet, jowar → sorghum). Used first.
2. **Learned mappings** – When a user search is resolved (e.g. via Wikidata or any API), the pair (regional name → canonical English name) is stored in `data/learned_regional_mappings.json` and in memory. Future requests for the same name use the learned mapping so USDA/OFF get the English term without another online call.
3. **Online resolve** – If there is no static or learned mapping, the fetcher calls **Wikidata** with multiple languages (en, hi, es, fr, zh, de, ar, pt, ja, ko, …) to find an entity and its **English label**, then tries USDA/OFF with that label. If Wikidata finds nothing, an optional **LLM** (Ollama) prompt asks for the English name; the result is learned and used for USDA/OFF.
4. **Persistence** – Successful API results (any source) are used to learn: `set_learned_english(regional_key, canonical_name)` so the database grows from user searches and handles all scenarios over time.

So you do **not** need to add every regional name by hand: the first time someone searches e.g. “bajra”, the system resolves it (Wikidata or LLM), queries USDA with “pearl millet”, and saves “bajra” → “pearl millet” for next time. With Supabase knowledge DB enabled, the worker also stores the alias in `ingredient_aliases`, so resolution can happen from the DB without hitting external APIs again.

## Configuration (env)

| Env var | Default | Purpose |
|---------|---------|---------|
| `OLLAMA_API_URL` | `http://localhost:11434/api/generate` | Local LLM (greetings, intent fallback, response compose) |
| `USDA_FDC_API_KEY` | (none) | USDA FoodData Central; optional, [sign up](https://fdc.nal.usda.gov/api-key-signup) |
| `OPEN_FOOD_FACTS_ENABLED` | `true` | Enable/disable Open Food Facts |
| `SUPABASE_URL` | (none) | Supabase project URL (RAG, knowledge DB, unknowns) |
| `SUPABASE_SERVICE_ROLE_KEY` | (none) | Supabase service role key |
| `RUNNING_IN_DOCKER` | (none) | Set to `1` in Docker so `SUPABASE_URL` localhost/127.0.0.1 → `host.docker.internal` |

## URLs (code)

| Service | URL | Module | Notes |
|---------|-----|--------|--------|
| **Ollama** | From `OLLAMA_API_URL` | `core/config.py` | LLM generate; Docker: use `http://host.docker.internal:11434/api/generate` |
| **USDA FDC** | `https://api.nal.usda.gov/fdc/v1/foods/search` | `core/external_apis/usda_fdc.py` | Requires `USDA_FDC_API_KEY` |
| **Open Food Facts** | `https://world.openfoodfacts.org/cgi/search.pl` | `core/external_apis/open_food_facts.py` | No key; can disable with `OPEN_FOOD_FACTS_ENABLED=false` |
| **PubChem** | `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/...` | `core/external_apis/pubchem.py` | No key; used in fetcher fallback chain |
| **ChEBI** | `https://www.ebi.ac.uk/chebi/backend/api/public/...` | `core/external_apis/chebi.py` | No key; used in fetcher fallback chain |
| **Wikidata** | `https://www.wikidata.org/w/api.php` | `core/external_apis/wikidata_api.py` | No key; used in fetcher fallback chain |
| **Supabase** | From `SUPABASE_URL` | `core/knowledge/ingredient_db.py`, `rag_service.py` | For RAG and ingredient knowledge; in Docker use `RUNNING_IN_DOCKER=1` and keep URL as `http://127.0.0.1:54321` so it is rewritten to `host.docker.internal` |

## Docker

- **Ollama**: Compose sets `OLLAMA_API_URL=http://host.docker.internal:11434/api/generate`.
- **Supabase (local)**: Set `SUPABASE_URL=http://127.0.0.1:54321` in `backend/.env`. Compose sets `RUNNING_IN_DOCKER=1` for backend and worker so the URL is rewritten to `http://host.docker.internal:54321` and "Name or service not known" is avoided.
- **USDA / OFF / PubChem / ChEBI / Wikidata**: Outbound HTTPS from the container; no host rewrite needed.

## Verify

```bash
# All-in-one: backend health, external APIs, Supabase, Redis, regional resolution, chat (from repo root or backend)
python backend/scripts/verify_all_health.py

# External APIs only (from backend dir)
python scripts/check_external_apis.py

# Supabase only
python scripts/verify_supabase.py
```
