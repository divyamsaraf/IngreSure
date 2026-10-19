-- Item 4.1 Prompt 2: durable trust-refresh clock for temporal confidence decay.
-- Decay applies to ike2_ingredient_groups only (not Coverage OS L2 files).
-- See backend/core/knowledge/ike2/decay.py module docstring.

alter table public.ike2_ingredient_groups
  add column if not exists trust_refreshed_at timestamptz;

-- Backfill: updated_at is often still insert-time (no bump trigger / reconcile
-- omit), but is the best historical signal we have.
update public.ike2_ingredient_groups
   set trust_refreshed_at = coalesce(updated_at, created_at, now())
 where trust_refreshed_at is null;

alter table public.ike2_ingredient_groups
  alter column trust_refreshed_at set default now();

alter table public.ike2_ingredient_groups
  alter column trust_refreshed_at set not null;

comment on column public.ike2_ingredient_groups.trust_refreshed_at is
  'Item 4.1: last trust-relevant refresh; decay TTL clock. Not Coverage OS L2.';
