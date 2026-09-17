# Supabase / Database After Restaurant Removal

## Summary

**menu_items, restaurant_id, and all menu/restaurant schema are not required.** The platform is now **grocery-only**: Scan, Grocery Chat, Profile. All menu/restaurant tables have been removed from the schema (via migration), and all frontend/backend code that depended on them has been removed.

---

## What was removed

### Supabase schema (migration `20260306100000_drop_restaurant_submissions.sql`)

- **Tables dropped:** `restaurant_submissions`, `embeddings`, `tag_history`, `verification_logs`, `item_ingredients`, `menu_items`, `verified_items`
- **Function dropped:** `search_menu_items()`
- **RLS policies** on those tables dropped

### Frontend

- **Pages removed:** `/analytics`, `/dashboard`, `/recommendations`, `/search`
- **Components removed:** ReviewDashboard, RecommendationList, VerificationStatus, SearchBar, SearchFilters, SearchResults
- **Libs removed:** `safety_engine.ts`, `recommendation_engine.ts` (both queried `menu_items`)
- **Types:** `MenuItem`, `VerificationLog` removed from `types/index.ts`

### Backend

- **seed_data.py:** No longer inserts into `menu_items` or `verified_items`; script is a no-op with a note to use `seed_user.py` or `seed_ingredient_knowledge.py`.

---

## What remains in Supabase

- **users** — Auth / demo user (e.g. `seed_user.py`).
- **ingredient_groups, ingredients, ingredient_aliases, unknown_ingredients, enrichment_metrics** — Knowledge base for ingredient resolution and compliance (unchanged).

---

## Applying the migration

**Local (fresh DB):** From repo root run `supabase db reset`. All migrations apply in order.

**Remote (existing DB):** If `supabase db push` fails with e.g. `relation "users" already exists`, the remote already has the schema and only the drop migration needs to run:

1. Open **Supabase Dashboard** → your project → **SQL Editor**.
2. Paste and run the contents of **`supabase/run_drop_menu_schema_remote.sql`** (or run that file if your CLI supports it).

That script drops only the menu/restaurant tables, policies, and `search_menu_items()`. It uses `drop if exists` so it’s safe if some objects are already missing.

After this, the database has no menu/restaurant tables. The app does not use or require them.

---

## Did I apply this on the server / Dashboard?

| Where | Status | What to do |
|-------|--------|------------|
| **Local** (e.g. `supabase start`) | ✅ Done | Migration ran when you did `supabase start` after the project_id fix. Menu/restaurant tables are dropped. |
| **Remote** (Supabase Dashboard – hosted project) | ⚠️ Manual | `supabase db push` failed on remote (schema already existed). You must run the drop script **once** in the Dashboard. |

### Apply on remote (Dashboard)

1. Open [Supabase Dashboard](https://supabase.com/dashboard) → select your project (e.g. the one with URL `https://gcufjqokqqmcuuayaybu.supabase.co`).
2. Go to **SQL Editor**.
3. Open **`supabase/run_drop_menu_schema_remote.sql`** in your repo, copy its **entire** contents, paste into the editor, and click **Run**.
4. You should see no errors (or only “relation does not exist” for objects already dropped). Done.

### Verify on Dashboard

- **Table Editor**: In the left sidebar, under **Tables**, you should **not** see: `menu_items`, `verified_items`, `verification_logs`, `item_ingredients`, `tag_history`, `embeddings`, `restaurant_submissions`.
- You **should** still see: `users`, and (if you use the knowledge base) `ingredient_groups`, `ingredients`, `ingredient_aliases`, `unknown_ingredients`, etc.
