-- Systemic DB integrity for IKE-2 safety rows.

-- 1) bee_product and insect_derived are mutually exclusive policy axes.
update public.ike2_ingredient_groups
   set insect_derived = false
 where bee_product is true and insect_derived is true;

alter table public.ike2_ingredient_groups
  drop constraint if exists bee_product_not_insect_derived;

alter table public.ike2_ingredient_groups
  add constraint bee_product_not_insect_derived
  check (not bee_product or not insect_derived);

-- 2) Kosher must fail shellfish_source (seeded offline; was missing from some DBs).
insert into public.ike2_restriction_rules
  (category, field, operator, value, action, min_knowledge_state)
values
  ('kosher', 'shellfish_source', 'eq', 'true', 'FAIL', 'DISCOVERED')
on conflict (category, field, coalesce(region, 'GLOBAL')) do nothing;
