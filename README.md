# IngreSure

**Eat with Confidence. Know What's Inside.**

IngreSure is an AI-powered food safety platform that helps consumers and restaurant owners verify menu ingredients, detect allergens, and ensure dietary compliance.

## Features

- **AI Verification**: Uses Mistral 7B to cross-reference menu descriptions with ingredients.
- **Safety Engine**: Rule-based system for factual allergen and diet checks.
- **Consumer Chat**: Real-time assistant to answer questions like "Is this vegan?".
- **Recommendations**: Smart suggestions based on dietary needs and ingredient similarity.
- **Restaurant Dashboard**: Analytics and review tools for owners.

## Tech Stack

- **Frontend**: Next.js 14, Tailwind CSS, Lucide React
- **Backend**: Next.js API Routes
- **Database**: Supabase (PostgreSQL + pgvector)
- **AI**: Ollama (Mistral 7B), LangChain (conceptually)

## Getting Started

### Prerequisites

1.  **Node.js** (v18+)
2.  **Python 3.9+** (for AI service)
3.  **Ollama** (running locally)
    ```bash
    ollama serve
    ollama pull mistral
    ```
4.  **Supabase Account**

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/divyamsaraf/IngreSure.git
    cd IngreSure
    ```

2.  Install Frontend Dependencies:
    ```bash
    cd frontend
    npm install
    ```

3.  Install AI Dependencies:
    ```bash
    cd ../ai
    pip install -r requirements.txt
    ```

4.  Set up Environment Variables:
    Create `.env.local` in `frontend/`:
    ```env
    NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
    NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_key
    ```

### Running the App

1.  Start the AI Service (if running separately, otherwise Next.js calls Ollama directly):
    ```bash
    # Ensure Ollama is running
    ```

2.  Start the Frontend:
    ```bash
    cd frontend
    npm run dev
    ```

3.  Open [http://localhost:3000](http://localhost:3000).

## Project Structure

- `frontend/`: Next.js application (App Router).
- `ai/`: Python scripts for verification logic.
- `database/`: SQL schema and migrations.
- `docs/`: Architecture and API documentation.

## License

MIT
