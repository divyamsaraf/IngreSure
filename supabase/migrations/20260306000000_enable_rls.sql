-- Enable Row Level Security (RLS) on all public application tables.
-- Backend uses SUPABASE_SERVICE_ROLE_KEY, which bypasses RLS; anon/authenticated
-- have no access unless we add policies. This locks down tables so they are not
-- "unrestricted" when using the anon key in the dashboard or from clients.

-- Knowledge base tables (backend-only: no policies => only service_role can access)
alter table if exists public.ingredient_groups enable row level security;
alter table if exists public.ingredients enable row level security;
alter table if exists public.ingredient_aliases enable row level security;
alter table if exists public.unknown_ingredients enable row level security;
alter table if exists public.enrichment_metrics enable row level security;

-- Init/menu tables (backend-only in current app; enable RLS so not unrestricted)
alter table if exists public.users enable row level security;
alter table if exists public.restaurant_submissions enable row level security;
alter table if exists public.verified_items enable row level security;
alter table if exists public.embeddings enable row level security;
alter table if exists public.menu_items enable row level security;
alter table if exists public.item_ingredients enable row level security;
alter table if exists public.tag_history enable row level security;
alter table if exists public.verification_logs enable row level security;

-- Policies for user-owned data (so authenticated users can access their own rows when using anon/authenticated key)
-- Users: read/update own row
create policy "users_select_own" on public.users for select using (auth.uid() = id);
create policy "users_update_own" on public.users for update using (auth.uid() = id);

-- Menu / restaurant data: restrict by restaurant_id = auth.uid()
create policy "menu_items_select_own" on public.menu_items for select using (auth.uid() = restaurant_id);
create policy "menu_items_insert_own" on public.menu_items for insert with check (auth.uid() = restaurant_id);
create policy "menu_items_update_own" on public.menu_items for update using (auth.uid() = restaurant_id);
create policy "menu_items_delete_own" on public.menu_items for delete using (auth.uid() = restaurant_id);

create policy "item_ingredients_select_own" on public.item_ingredients for select
  using (exists (select 1 from public.menu_items mi where mi.id = menu_item_id and mi.restaurant_id = auth.uid()));
create policy "item_ingredients_insert_own" on public.item_ingredients for insert
  with check (exists (select 1 from public.menu_items mi where mi.id = menu_item_id and mi.restaurant_id = auth.uid()));
create policy "item_ingredients_update_own" on public.item_ingredients for update
  using (exists (select 1 from public.menu_items mi where mi.id = menu_item_id and mi.restaurant_id = auth.uid()));
create policy "item_ingredients_delete_own" on public.item_ingredients for delete
  using (exists (select 1 from public.menu_items mi where mi.id = menu_item_id and mi.restaurant_id = auth.uid()));

create policy "tag_history_select_own" on public.tag_history for select
  using (exists (select 1 from public.menu_items mi where mi.id = menu_item_id and mi.restaurant_id = auth.uid()));
create policy "tag_history_insert_own" on public.tag_history for insert
  with check (exists (select 1 from public.menu_items mi where mi.id = menu_item_id and mi.restaurant_id = auth.uid()));

create policy "verification_logs_select_own" on public.verification_logs for select
  using (exists (select 1 from public.menu_items mi where mi.id = menu_item_id and mi.restaurant_id = auth.uid()));

create policy "restaurant_submissions_select_own" on public.restaurant_submissions for select using (auth.uid() = restaurant_id);
create policy "restaurant_submissions_insert_own" on public.restaurant_submissions for insert with check (auth.uid() = restaurant_id);
create policy "restaurant_submissions_update_own" on public.restaurant_submissions for update using (auth.uid() = restaurant_id);

create policy "verified_items_select_own" on public.verified_items for select using (auth.uid() = restaurant_id);
create policy "verified_items_insert_own" on public.verified_items for insert with check (auth.uid() = restaurant_id);
create policy "verified_items_update_own" on public.verified_items for update using (auth.uid() = restaurant_id);

create policy "embeddings_select_own" on public.embeddings for select
  using (exists (select 1 from public.verified_items vi where vi.id = item_id and vi.restaurant_id = auth.uid()));
create policy "embeddings_insert_own" on public.embeddings for insert
  with check (exists (select 1 from public.verified_items vi where vi.id = item_id and vi.restaurant_id = auth.uid()));

-- Knowledge tables have no policies: only service_role (backend) can read/write.
-- That is the intended fix for "RLS disabled" / unrestricted access.

-- Optional: function for scripts to list public tables and RLS status (service_role can call)
create or replace function public.get_public_tables_rls()
returns table(tablename text, rls_enabled boolean)
language sql
security definer
set search_path = public
as $$
  select c.relname::text, c.relrowsecurity
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public' and c.relkind = 'r'
  order by c.relname;
$$;
grant execute on function public.get_public_tables_rls() to service_role;
grant execute on function public.get_public_tables_rls() to authenticated;
grant execute on function public.get_public_tables_rls() to anon;
