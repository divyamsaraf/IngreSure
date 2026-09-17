# Deployment Guide

## Frontend (Vercel)

1.  **Connect Repository:**
    - Go to [Vercel Dashboard](https://vercel.com/dashboard).
    - Click "Add New..." -> "Project".
    - Import the `IngreSure` repository.

2.  **Configure Project:**
    - **Framework Preset:** Next.js
    - **Root Directory:** `frontend`
    - **Build Command:** `npm run build`
    - **Install Command:** `npm install --legacy-peer-deps` (Important due to React 19 peer dependency issues)

3.  **Environment Variables:**
    - Add the following variables in Vercel Project Settings:
        - `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase Project URL.
        - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase Anon Key.

4.  **Deploy:**
    - Click "Deploy".

## Database (Supabase)

1.  **Schema:** Source of truth is `supabase/migrations/`. For a **new** hosted project:
    - Install Supabase CLI: `brew install supabase/tap/supabase`
    - Login: `supabase login`
    - Link: `supabase link --project-ref <your-project-ref>`
    - Push migrations: `supabase db push`
    - If the remote DB already had an older schema, run `supabase/run_drop_menu_schema_remote.sql` in the Dashboard SQL Editor first (see `docs/SUPABASE_AFTER_RESTAURANT_REMOVAL.md`).
2.  **No Edge Functions** are used by the grocery-only app; skip deploying any Supabase functions.

## Verification
- Visit the Vercel deployment URL.
- Test Grocery Chat and Scan; confirm backend health at `https://your-backend/health`.
