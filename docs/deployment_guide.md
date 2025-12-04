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

## Backend (Supabase)

1.  **Database Migration:**
    - Go to Supabase Dashboard -> SQL Editor.
    - Run the contents of `database/schema.sql` (Phase 1/2).
    - Run `database/phase3_schema.sql`.
    - Run `database/phase5_schema.sql`.

2.  **Edge Functions:**
    - Install Supabase CLI locally: `brew install supabase/tap/supabase`
    - Login: `supabase login`
    - Link Project: `supabase link --project-ref <your-project-ref>`
    - Deploy Functions:
        ```bash
        supabase functions deploy tagging-engine
        supabase functions deploy upload-menu-item
        supabase functions deploy global-search
        ```
    - Set Secrets:
        ```bash
        supabase secrets set SUPABASE_URL=<your-url>
        supabase secrets set SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
        ```

## Verification
- Visit the Vercel deployment URL.
- Test the "Upload" flow (check Supabase tables for data).
- Test the "Search" flow (check Edge Function logs).
