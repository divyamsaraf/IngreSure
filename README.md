# IngreSure

**Eat with Confidence. Know What's Inside.**

IngreSure is an AI-powered food safety platform that helps consumers and restaurant owners verify menu ingredients, detect allergens, and ensure dietary compliance using a mix of deterministic rules and LLM reasoning.

## 🚀 Quick Start

1.  **Start Infrastructure** (Supabase + Ollama):
    ```bash
    # Terminal 1
    ollama serve
    ollama pull llama3.2:3b
    
    # Terminal 2
    supabase start
    ```

2.  **Start Backend**:
    ```bash
    cd IngreSure
    python3 backend/app.py
    ```

3.  **Start Frontend**:
    ```bash
    cd frontend
    npm run dev
    ```

Visit [http://localhost:3000](http://localhost:3000).

## 📚 Documentation

We have detailed documentation for every part of the system:

- **[Tech Stack & Deep Dive](docs/TECH_STACK_DEEP_DIVE.md)**: **START HERE**. A complete breakdown of every file, model, and service.
- **[System Architecture](docs/SYSTEM_ARCHITECTURE.md)**: Diagrams and data flow references.
- **[Backend API](docs/BACKEND_API.md)**: API Endpoint reference.
- **[AI Engine Internals](docs/AI_ENGINE.md)**: How the SafetyAnalyst and RAG engines work.
- **[Frontend Guide](docs/FRONTEND_GUIDE.md)**: Next.js structure and components.

## 🏗 Features

- **Grocery Scanner**: Upload an ingredient label -> Get a safe/unsafe verdict.
- **Chat Assistant**: Ask "Is E471 vegan?" and get an instant answer.
- **Restaurant Search**: Find "Safe dishes" at supported restaurants.
- **Menu Verification**: (B2B) Auto-audit menus for mistakes.

## 🛠 Tech Stack

- **AI**: Ollama (Llama 3.2), PaddleOCR, SentenceTransformers.
- **Backend**: FastAPI (Python).
- **Frontend**: Next.js 14, TailwindCSS.
- **Database**: Supabase (PostgreSQL + pgvector).

## License
MIT
