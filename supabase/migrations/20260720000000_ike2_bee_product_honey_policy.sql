-- Honey is a bee product, not an insect-derived dye (carmine/shellac).
-- Separates Halal/Kosher/Hindu honey-allowed policy from insect-additive bans.
alter table public.ike2_ingredient_groups
  add column if not exists bee_product boolean not null default false;

alter table public.ike2_ingredient_groups
  drop constraint if exists bee_product_implies_animal;

alter table public.ike2_ingredient_groups
  add constraint bee_product_implies_animal
  check (not bee_product or animal_origin);

-- Live DBs already seeded hindu_vegetarian+insect_derived; retire that rule.
delete from public.ike2_restriction_rules
 where category = 'hindu_vegetarian' and field = 'insect_derived';

insert into public.ike2_restriction_rules
  (category, field, operator, value, action, min_knowledge_state)
values
  ('jain', 'bee_product', 'eq', 'true', 'FAIL', 'DISCOVERED')
on conflict (category, field, coalesce(region, 'GLOBAL')) do nothing;
