# IngreSure

**Tagline:** AI-powered deterministic assistant for restaurants and grocery items, ensuring accurate dietary, allergen, and ingredient verification.

## Overview
IngreSure is a platform designed to help restaurants and users verify food items for dietary restrictions and allergens. It leverages AI to analyze ingredients and provide hallucination-free responses.

## Tech Stack
- **Frontend:** Next.js / React + Material UI / Tailwind
- **Backend:** FastAPI (Python) + Supabase client
- **AI:** Mistral 7B quantized 4-bit (local), FAISS (RAG), YOLOv8-nano + Tesseract OCR
- **Database:** Supabase (PostgreSQL)
- **Deployment:** Vercel (Frontend), Supabase Functions/FastAPI host (Backend)

## Collaboration Workflow
- **Main Branch:** `main` (Production-ready code)
- **Feature Branches:**
  - `frontend/`: Frontend related changes
  - `backend/`: Backend related changes
  - `ai/`: AI model and logic changes
- **Pull Requests:** All changes must go through PRs and be reviewed by at least one other developer.

## Setup Instructions
### Prerequisites
- Node.js & npm
- Python 3.10+
- Supabase CLI (optional but recommended)
- Ollama (for running Mistral 7B locally)

### Running Locally
1. **Clone the repository:**
   ```bash
   git clone https://github.com/divyamsaraf/IngreSure.git
   cd IngreSure
   ```

2. **AI Model Setup:**
   - Install Ollama.
   - Pull Mistral 7B: `ollama pull mistral`

3. **Backend Setup:**
   - Navigate to `backend/` (instructions to be added).

4. **Frontend Setup:**
   - Navigate to `frontend/` (instructions to be added).
