# Database

**Source of truth:** `supabase/migrations/`. Use `supabase start`, `supabase db reset`, or `supabase db push` to apply.

- **Tech:** Supabase (PostgreSQL)

## Hosted Supabase (cloud project)

Local `supabase db reset` does **not** update your remote project. After adding a new migration (for example `20260409120000_request_history.sql` for API request history), apply it to the hosted database:

1. **Supabase Dashboard** → your project → **SQL Editor** → paste the migration file contents → Run, or  
2. **CLI:** `supabase link` (one-time) then `supabase db push`.

Until `public.request_history` exists, the backend logs a one-time warning; the app still runs. Set `REQUEST_HISTORY_ENABLED=false` in `backend/.env` if you want to disable writes until the table exists.
