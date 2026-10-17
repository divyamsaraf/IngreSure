-- Item 1 Prompt 2: provenance `source` on ike2_ingredient_groups so
-- reconcile._PROTECTED_STATES can key on who locked/classified the row.
-- Without this column, existing_source is always "" and LOCKED protection is dead.
-- See docs/item1_ingestion_spec.md Prompt 1b.

alter table public.ike2_ingredient_groups
  add column if not exists source text;

-- Backfill from bulk classification_method ("bulk:<canonical>") or leave null.
update public.ike2_ingredient_groups
   set source = nullif(substring(classification_method from 6), '')
 where source is null
   and classification_method like 'bulk:%';

comment on column public.ike2_ingredient_groups.source is
  'Item 1: provenance key for reconcile tiers / LOCKED protection (e.g. e_number_catalog, human, ontology). Not primary_source_url.';
