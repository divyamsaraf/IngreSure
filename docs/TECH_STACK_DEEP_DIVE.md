# Technology Stack & Deep Dive Analysis

> **Note**: This document provides a granular analysis of every tool, service, model, and file in the IngreSure project.

## 1. Services & Tools Overview

### Backend Core
| tool/Service | Purpose | Usage in Project |
| :--- | :--- | :--- |
| **FastAPI** | Web Framework | The backbone of the `backend/` service. Handles all HTTP requests, routing (`/chat`, `/scan`), and async processing. Selected for its speed and native async support for AI streams. |
| **Uvicorn** | ASGI Server | Runs the FastAPI application. |
| **Python 3.10+** | Runtime | Language for all AI/Backend logic. |

### AI & Machine Learning
| Model/Tool | Type | Detailed Role |
| :--- | :--- | :--- |
| **Ollama** | LLM Runner | Local inference server that hosts the LLMs. Eliminates cloud costs and ensures privacy. |
| **Llama 3.2:3b** | LLM | The "Brain" of the system. Standardized across all services (`safety_analyst`, `rag_service`, `llm_normalizer`, `verification_service`). Fast, light, and optimized for local run. |
| **PaddleOCR** | OCR Engine | **Optical Character Recognition**. Extracts raw text from images uploaded to `/scan`. Used because it handles table structures (nutrition labels) better than Tesseract. |
| **all-MiniLM-L6-v2** | Embedding Model | Runs locally via `sentence-transformers`. Converts text (menu items, queries) into 384-dimensional vectors for semantic search. |

### Database & Storage
| Service | Function | Details |
| :--- | :--- | :--- |
| **Supabase (PostgreSQL)** | Relational DB | Hosted locally via Docker. Stores User Profiles (`user_profiles`), Restaurant Metadata (`restaurants`). |
| **pgvector** | Vector Extension | Enables vector similarity search in Postgres. Stores embeddings in the `menu_items` table. |
| **Docker** | Containerization | Orchestrates the local Supabase stack (Studio, Auth, DB, etc.) to ensure a reproducible environment. |

### Frontend
| Library/Framework | Purpose | Role |
| :--- | :--- | :--- |
| **Next.js 14+** | App Framework | React framework using the App Router for file-based routing. Handles Server-Side Rendering (SSR) and API proxying. |
| **TailwindCSS** | Styling | Utility-first CSS framework for rapid, responsive UI development. |
| **ShadCN UI** | UI Components | Provides accessible, pre-styled components (in `src/components/ui`) like Dialogs, Buttons, and Inputs. |
| **Lucide React** | Icons | Icon library used throughout the UI. |

---

## 2. Codebase Deep Analysis: "File by File"

### Directory: `/backend` (The Intelligence Layer)
This directory contains the Python-based backend that powers all intelligent features.

**Core Application**
- **`app.py`**: The central nervous system.
    - **What it does**: Initializes FastAPI, loads all engines (OCR, RAG, Rules), and defines API routes (`/scan`, `/chat/grocery`, `/chat/restaurant`).
    - **Key Detail**: Uses global variables for engines to load models only once at startup, preventing lag on each request.

**Services (The "Engines")**
- **`safety_analyst.py`**: The **Grocery Safety Engine**.
    - **What it does**: Implements the logic for "Can I eat this?".
    - **How**: It first parses the user's natural language profile (e.g., "I'm vegan") into a structured session. Then, it runs a **Deterministic Rule Check** (fast path) against `ingredient_ontology.py`. If that fails/is ambiguous, it calls the LLM (slow path) to explain.
- **`rag_service.py`**: The **Restaurant Search Engine**.
    - **What it does**: Retrieve-and-Generate system for menus.
    - **How**:
        1. `retrieve(query)`: Converts query to vector -> searches Supabase.
        2. `generate_answer_stream()`: Feeds retrieved items to LLM to create a waiter-like response.
- **`ocr_engine.py`**: The **Vision System**.
    - **What it does**: Wraps `PaddleOCR` to extract text from images.
    - **How**: Converts raw bytes to valid image arrays, runs detection+recognition, and returns a single concatenated string.
- **`verification_service.py`**: The **Auditor**.
    - **What it does**: Checks if a menu item is lying.
    - **How**: Compares "Vegan Burger" (Name) + "Beef" (Ingredient) using LLM reasoning to flag inconsistencies.
- **`onboarding_service.py`**: The **Data Ingestor**.
    - **What it does**: Processes raw JSON menus from restaurants, generates embeddings for every item (using `rag_service`), and inserts them into Supabase.

**Helpers & Data**
- **`ingredient_ontology.py`**: The **Source of Truth**.
    - **What it does**: A massive dictionary mapping thousands of ingredients to their properties (Source: Plant/Animal, Allergens: Peanuts/Dairy).
    - **Why**: Allows O(1) instant lookup for 90% of queries without needing an LLM.
- **`dietary_rules.py`**: The **Lawyer**.
    - **What it does**: Defines the strict rules for diets (e.g., "Vegan = No Animal"). Also handles NLU (extracting "vegan" keyword from "Show me vegan food").
- **`llm_normalizer.py`**: The **Janitor**.
    - **What it does**: Cleans up dirty text. OCR often outputs garbage like "sugr,; wht flur". This module uses a small LLM call to fix it to "sugar, wheat flour".

### Directory: `/frontend` (The Experience Layer)

**App Router (`src/app`)**
- **`page.tsx`**: The Landing Page.
- **`chat/page.tsx`**: The **Grocery Assistant** view. Initializes the chat window with `mode="grocery"`.
- **`restaurant/chat/page.tsx`**: The **Restaurant Assistant** view. Initializes chat with `mode="restaurant"`.
- **`api/chat/route.ts`**: The **Proxy**.
    - **What it does**: Hides the Python backend from the public internet. The frontend calls this Next.js API route, which internally forwards the request to `localhost:8000`.

**Components (`src/components`)**
- **`chat/ChatInterface.tsx`**: The **Reusable Chat UI**.
    - **Complexity**: High. Handles:
        - Streaming text rendering (reading `ReadableStream` chunks).
        - Auto-scrolling.
        - Rendering Markdown responses.
        - "Thinking" states.
- **`scan/SingleItemForm.tsx`**: The **Upload Interface**.
    - **What it does**: Handles drag-and-drop image uploads, previews the image, and displays the structured analysis result (Scorecard).

## 3. Data Flow Architecture

### Grocery Scanning Flow
1. **User** uploads image in Frontend.
2. **Frontend** POSTs to `/api/scan` (Next.js) -> Proxies to `/scan` (Python).
3. **Backend**:
   - `ocr_engine` extracts text.
   - `llm_normalizer` cleans text.
   - `dietary_rules` classifies ingredients against the `ingredient_ontology`.
4. **Result**: JSON with "Safe"/"Unsafe" flags returns to UI.

### Restaurant RAG Flow
1. **User** asks "Any vegan pasta?"
2. **Backend**:
   - `rag_service` creates vector `[0.1, -0.5, ...]`.
   - **Supabase** performs cosine similarity search on `embeddings` column.
   - Top 5 matches returned (e.g., "Spinach Ravioli").
   - **LLM** receives context: "User asked: Vegan pasta? Context: Spinach Ravioli (Ingredients: ...). Answer as waiter."
3. **Response**: Streamed text "Yes, we have Spinach Ravioli..."
