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

## Dependencies

- **Ollama** (llama3.2:3b) — local LLM for intent extraction and response generation
- **USDA FDC API** (optional) — external ingredient lookup
- **Open Food Facts** (optional) — additional ingredient data source
- **Supabase** (optional) — for RAG/restaurant features
