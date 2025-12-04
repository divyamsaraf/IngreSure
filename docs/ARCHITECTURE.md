# System Architecture

## Overview

IngreSure follows a hybrid architecture with a Next.js frontend/backend and a Python-based AI service (conceptually, though currently integrated via API calls to Ollama).

## High-Level Design

```mermaid
graph TD
    User[User / Restaurant Owner] -->|Browser| Frontend[Next.js Frontend]
    
    subgraph "Frontend Layer"
        Frontend -->|API Routes| API[Next.js API]
        Frontend -->|Direct DB| Supabase[Supabase]
    end
    
    subgraph "Logic Layer"
        API -->|Chat/Recs| SafetyEngine[Safety Engine (TS)]
        API -->|Verification| AIService[AI Service (Python/Ollama)]
    end
    
    subgraph "Data Layer"
        Supabase -->|Auth/Data| DB[(PostgreSQL)]
        SafetyEngine -->|Query| DB
    end
    
    subgraph "AI Layer"
        AIService -->|Prompt| Ollama[Ollama (Mistral 7B)]
        API -->|Prompt| Ollama
    end
```

## Components

### 1. Frontend (Next.js)
- **App Router**: Handles routing for `/dashboard`, `/chat`, `/recommendations`.
- **Components**: Reusable UI elements (Tailwind CSS).
- **State**: React Query for data fetching.

### 2. Safety Engine (`frontend/src/lib/safety_engine.ts`)
- **Role**: The "Guardrails" of the system.
- **Function**:
    - Takes user constraints (e.g., "Peanut Allergy").
    - Queries Supabase for items.
    - Filters items based on `item_ingredients` and `tag_history`.
    - Returns ONLY safe items to the LLM context.

### 3. AI Service
- **Verification**: `ai/verification_service.py` (Offline/Batch).
- **Chat**: `frontend/src/lib/llm.ts` (Real-time).
- **Model**: Mistral 7B via Ollama.

### 4. Database (Supabase)
- **Tables**:
    - `menu_items`: Core item data.
    - `item_ingredients`: Many-to-many link.
    - `verification_logs`: AI results.
