# IngreSure - Quick Start Guide

> **Prerequisites**:
> - Docker Desktop (Must be running)
> - Python 3.10+
> - Node.js 18+
> - Supabase CLI
> - Ollama (running `llama3.2:3b`)

## Step 1: Start Infrastructure (Critical)
1.  **Open Docker Desktop**: Ensure the Docker Engine is running.
2.  **Start Supabase**:
    ```bash
    supabase start
    ```
    *Note: This spins up the local database (ingredient knowledge, optional users).*

## Step 2: Start Backend (Python)
1.  **Navigate to backend**:
    ```bash
    cd /path/to/IngreSure/backend
    ```
2.  **Run FastAPI**:
    ```bash
    python3 -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
    ```
    *Server will start on `http://localhost:8000`.*

## Step 3: Start Frontend (Next.js)
1.  **Navigate to frontend**:
    ```bash
    cd frontend
    ```
2.  **Run Development Server**:
    ```bash
    npm run dev
    ```
    *App will start on `http://localhost:3000`.*

## Step 4: Access the App
- **Grocery Assistant**: [http://localhost:3000/chat](http://localhost:3000/chat)
- **Scan**: [http://localhost:3000/scan](http://localhost:3000/scan)

## Trouble? 
- **DB Connection Error?** Check if `supabase start` finished successfully.
- **Frontend Error?** Make sure you ran `npm install` in `/frontend` first.
