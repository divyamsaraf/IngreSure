-- Remove all menu/restaurant schema: platform is grocery-only (scan, chat, profile, verify).
-- Drops: RLS policies, search_menu_items(), then tables in FK order.
-- Keeps: users (auth/demo), ingredient_groups, ingredients, ingredient_aliases, unknown_ingredients, enrichment_metrics.

-- 1. Drop RLS policies (tables must exist to drop policies)
drop policy if exists "embeddings_select_own" on public.embeddings;
drop policy if exists "embeddings_insert_own" on public.embeddings;
drop policy if exists "tag_history_select_own" on public.tag_history;
drop policy if exists "tag_history_insert_own" on public.tag_history;
drop policy if exists "verification_logs_select_own" on public.verification_logs;
drop policy if exists "item_ingredients_select_own" on public.item_ingredients;
drop policy if exists "item_ingredients_insert_own" on public.item_ingredients;
drop policy if exists "item_ingredients_update_own" on public.item_ingredients;
drop policy if exists "item_ingredients_delete_own" on public.item_ingredients;
drop policy if exists "menu_items_select_own" on public.menu_items;
drop policy if exists "menu_items_insert_own" on public.menu_items;
drop policy if exists "menu_items_update_own" on public.menu_items;
drop policy if exists "menu_items_delete_own" on public.menu_items;
drop policy if exists "verified_items_select_own" on public.verified_items;
drop policy if exists "verified_items_insert_own" on public.verified_items;
drop policy if exists "verified_items_update_own" on public.verified_items;
drop policy if exists "restaurant_submissions_select_own" on public.restaurant_submissions;
drop policy if exists "restaurant_submissions_insert_own" on public.restaurant_submissions;
drop policy if exists "restaurant_submissions_update_own" on public.restaurant_submissions;

-- 2. Drop function that depends on menu_items and embeddings
drop function if exists public.search_menu_items(text, vector, float, int, text[], text[]);

-- 3. Drop tables in FK order (child first)
drop table if exists public.embeddings;
drop table if exists public.tag_history;
drop table if exists public.verification_logs;
drop table if exists public.item_ingredients;
drop table if exists public.menu_items;
drop table if exists public.verified_items;
drop table if exists public.restaurant_submissions;
