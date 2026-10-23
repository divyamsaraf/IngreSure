-- L3: ike2_* is backend-only. RLS is already on with no policies; also revoke
-- table/view grants so the anon key cannot read via PostgREST (including the
-- alias view, which would otherwise run as owner and skip RLS).
alter view if exists public.ike2_v_alias_resolution set (security_invoker = true);

revoke all on table public.ike2_ingredient_groups from anon, authenticated;
revoke all on table public.ike2_ingredients from anon, authenticated;
revoke all on table public.ike2_aliases from anon, authenticated;
revoke all on table public.ike2_alias_disambiguation from anon, authenticated;
revoke all on table public.ike2_restriction_rules from anon, authenticated;
revoke all on table public.ike2_resolution_cache from anon, authenticated;
revoke all on table public.ike2_unknown_queue from anon, authenticated;
revoke all on table public.ike2_shadow_diffs from anon, authenticated;
revoke all on table public.ike2_group_merges from anon, authenticated;
revoke all on table public.ike2_v_alias_resolution from anon, authenticated;

alter table if exists ike2_staging.ingredient_groups enable row level security;
alter table if exists ike2_staging.stg_rejects enable row level security;
revoke all on all tables in schema ike2_staging from anon, authenticated;
