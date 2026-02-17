# IngreSure

**Eat with Confidence. Know What's Inside.**

IngreSure is an AI-powered food safety platform that helps consumers verify ingredients, detect allergens, and ensure dietary compliance. It uses a hybrid architecture: deterministic compliance rules for safety-critical decisions, and a local LLM for natural conversation.

## System Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Next.js     │────▶│  FastAPI      │────▶│  Ollama      │
│  Frontend    │◀────│  Backend      │◀────│  LLM         │
│  :3000       │     │  :8000        │     │  :11434      │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Ontology │ │ USDA API │ │ Open Food│
        │ (local)  │ │ (remote) │ │ Facts    │
        └──────────┘ └──────────┘ └──────────┘
```

**Data Flow:**
1. User sends message → Next.js frontend → FastAPI backend
2. Rule-based intent detector parses query (fast, ~2ms)
3. If rules can't parse → LLM fallback extracts intent (~3s)
4. Compliance engine evaluates ingredients deterministically (never LLM)
5. LLM composes natural response from structured verdict (fallback: templates)

## Prerequisites

| Service | Version | Purpose |
|---------|---------|---------|
| **Python** | 3.10+ | Backend runtime |
| **Node.js** | 18+ | Frontend runtime |
| **Ollama** | Latest | Local LLM server |
| **Supabase CLI** | Latest | Database (optional for dev) |

## Quick Start (Development)

### Step 1: Start Ollama (LLM Server)

```bash
# Install Ollama (macOS)
brew install ollama

# Start the server
ollama serve

# In another terminal, pull the model (one-time)
ollama pull llama3.2:3b
```

Verify it's running:
```bash
curl http://localhost:11434/api/tags
# Should show llama3.2:3b in the list
```

### Step 2: Start the Backend

```bash
cd backend

# Create virtual environment (one-time)
python3 -m venv venv
source venv/bin/activate

# Install dependencies (one-time)
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env and add your API keys (see Environment Variables below)

# Start the backend server
USE_NEW_ENGINE=true uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The backend runs at **http://localhost:8000**.

Verify:
```bash
curl http://localhost:8000/health
```

### Step 3: Start the Frontend

```bash
cd frontend

# Install dependencies (one-time)
npm install

# Start dev server
npm run dev
```

The frontend runs at **http://localhost:3000**.

### Step 4 (Optional): Start Supabase

Only needed if using the RAG/restaurant features:

```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Start local Supabase
supabase start
```

## Environment Variables

### Backend (`backend/.env`)

```bash
# Compliance engine (required)
USE_NEW_ENGINE=true

# Shadow mode: run legacy engine alongside for comparison logging
SHADOW_MODE=false

# USDA FoodData Central API key (free: https://fdc.nal.usda.gov/api-key-signup)
# Enables external ingredient lookup for unknown ingredients
USDA_FDC_API_KEY=your_key_here

# Open Food Facts API (no key needed; set false to disable)
OPEN_FOOD_FACTS_ENABLED=true

# Ollama LLM (defaults shown — only override if non-standard)
# OLLAMA_API_URL=http://localhost:11434/api/generate
# OLLAMA_MODEL=llama3.2:3b

# Supabase (optional — for RAG/restaurant features)
# SUPABASE_URL=http://127.0.0.1:54321
# SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### Frontend (`frontend/.env.local`)

```bash
# Backend URL (defaults to http://127.0.0.1:8000 if not set)
BACKEND_URL=http://127.0.0.1:8000

# Supabase (optional)
# NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
# NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

## Running with Docker

```bash
# Build and start all services
docker compose up --build

# Or in detached mode
docker compose up --build -d
```

This starts:
- **Backend** on port 8000
- **Frontend** on port 3000
- Both connect to host Ollama via `host.docker.internal:11434`

> Note: Ollama must be running on the host machine. Supabase is run separately via `supabase start`.

## Running Tests

```bash
cd backend

# Run all tests
python3 -m pytest tests/ -v

# Run specific test suites
python3 -m pytest tests/test_intent_detector.py -v        # Intent detection + NLU
python3 -m pytest tests/test_restrictions_comprehensive.py -v  # All dietary restrictions
python3 -m pytest tests/test_compliance_engine.py -v       # Core compliance engine
python3 -m pytest tests/test_external_apis.py -v           # USDA/OFF API connectors
```

## API Endpoints

### Chat (Grocery Safety)

```bash
# Check ingredients with user profile
curl -X POST http://localhost:8000/chat/grocery \
  -H "Content-Type: application/json" \
  -d '{
    "query": "can jain eat onion?",
    "user_id": "user123"
  }'

# Check with inline profile (no persistence)
curl -X POST http://localhost:8000/chat/grocery \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Is gelatin halal?",
    "userProfile": {"diet": "Halal"}
  }'
```

### Profile Updates (via chat)

Users can update their profile through natural language:
- `"I am Jain"` → sets dietary preference
- `"I'm allergic to peanuts and milk"` → adds allergens
- `"remove milk from my allergens"` → removes allergen
- `"I avoid alcohol"` → adds lifestyle preference
- `"is onion jain?"` → sets diet to Jain AND checks onion

### Scan (Image Upload)

```bash
curl -X POST http://localhost:8000/scan \
  -F "image=@label_photo.jpg" \
  -F 'userProfile={"diet":"Vegan"}'
```

## Project Structure

```
IngreSure/
├── backend/
│   ├── app.py                     # FastAPI orchestrator (5-layer architecture)
│   ├── core/
│   │   ├── config.py              # Centralized config (Ollama, APIs, paths)
│   │   ├── intent_detector.py     # Rule-based intent detection
│   │   ├── llm_intent.py          # LLM fallback for intent extraction
│   │   ├── llm_response.py        # LLM-powered response composition
│   │   ├── response_composer.py   # Template-based response fallback
│   │   ├── evaluation/
│   │   │   └── compliance_engine.py  # Deterministic safety evaluation
│   │   ├── models/
│   │   │   ├── user_profile.py    # User profile model
│   │   │   └── verdict.py         # Compliance verdict model
│   │   ├── normalization/
│   │   │   └── normalizer.py      # Ingredient name normalization
│   │   ├── ontology/
│   │   │   ├── ingredient_registry.py  # Ingredient lookup + API fallback
│   │   │   └── ingredient_schema.py    # Ingredient data model
│   │   ├── restrictions/
│   │   │   └── restriction_registry.py # Dietary restriction rules
│   │   ├── external_apis/
│   │   │   ├── usda_fdc.py        # USDA FoodData Central connector
│   │   │   ├── open_food_facts.py # Open Food Facts connector
│   │   │   ├── fetcher.py         # Multi-source API orchestrator
│   │   │   └── http_retry.py      # Retry with exponential backoff
│   │   ├── profile_storage.py     # Persistent profile storage
│   │   ├── bridge.py              # Profile → restriction ID mapping
│   │   └── parsing/
│   │       └── ingredient_parser.py   # Ingredient list parsing
│   ├── tests/                     # 409+ tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   └── api/               # Next.js API routes (proxy to backend)
│   │   ├── components/
│   │   │   └── chat/              # Chat UI components
│   │   └── types/
│   │       └── userProfile.ts     # Frontend profile types
│   └── package.json
├── data/
│   ├── ontology.json              # Static ingredient knowledge base
│   ├── restrictions.json          # Dietary restriction rules
│   ├── dynamic_ontology.json      # Self-evolving ingredient cache
│   └── profiles.json              # Persistent user profiles
└── docker-compose.yml
```

## Supported Dietary Restrictions

| Category | Supported |
|----------|-----------|
| **Religious** | Halal, Kosher, Jain, Hindu Vegetarian, Hindu Non-Vegetarian, Buddhist, Seventh Day Adventist |
| **Dietary** | Vegan, Vegetarian, Lacto-Vegetarian, Ovo-Vegetarian, Pescatarian |
| **Medical** | Gluten-Free, Dairy-Free, Egg-Free, Peanut Allergy, Tree-Nut Allergy, Soy Allergy, Shellfish Allergy, Fish Allergy, Sesame Allergy, Onion Allergy, Garlic Allergy |
| **Lifestyle** | No Alcohol, No Onion, No Garlic, No Palm Oil, No Seed Oils, No GMOs, No Artificial Colors |

## Troubleshooting

### Backend won't start
```bash
# Check Python version (need 3.10+)
python3 --version

# Check if port 8000 is in use
lsof -i :8000
```

### LLM responses are slow or missing
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# If not running
ollama serve

# Pull the model if missing
ollama pull llama3.2:3b
```

> The system works without Ollama — it falls back to template-based responses. LLM adds natural conversation but is not required for safety compliance.

### External API lookups failing
```bash
# Test USDA API key
curl "https://api.nal.usda.gov/fdc/v1/foods/search?api_key=YOUR_KEY&query=onion&pageSize=1"

# Test Open Food Facts
curl "https://world.openfoodfacts.org/cgi/search.pl?search_terms=onion&json=1&page_size=1"
```

### Frontend can't reach backend
```bash
# Ensure backend is running on port 8000
curl http://localhost:8000/health

# Check frontend env
# BACKEND_URL should be http://127.0.0.1:8000 (or unset for default)
```

## License

MIT
