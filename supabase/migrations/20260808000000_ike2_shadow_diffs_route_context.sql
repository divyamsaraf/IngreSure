-- Item 16 soak instrumentation: distinguish chat vs API diffs and record
-- which restrictions were active so false_safe_regression can be scored
-- against IKE-2's own rules (not legacy UNCERTAIN alone).
-- Forward-only; no backfill of historical rows.

alter table public.ike2_shadow_diffs
  add column if not exists source_route text;

alter table public.ike2_shadow_diffs
  add column if not exists restriction_ids jsonb;

comment on column public.ike2_shadow_diffs.source_route is
  'Origin of the shadow comparison: chat | api_evaluate_compliance | api_evaluate_product | test';

comment on column public.ike2_shadow_diffs.restriction_ids is
  'Profile/API restriction ids active when the comparison ran (json array of text)';
