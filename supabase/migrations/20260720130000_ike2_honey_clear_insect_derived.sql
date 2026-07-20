-- Honey (and other bee products) must not carry insect_derived.
-- insect_derived is for dyes/resins (carmine, shellac); bee_product is separate.
-- Stale seeds left honey with insect_derived=true, which false-Avoids Halal /
-- Kosher / Hindu Vegetarian when Tier-3 rows are used without Tier-1 winning.

update public.ike2_ingredient_groups
   set insect_derived = false,
       bee_product = true,
       animal_origin = true
 where canonical_name in ('honey', 'honey powder', 'honey solids')
    or bee_product is true;

-- Re-assert Jain bee_product rule (idempotent).
insert into public.ike2_restriction_rules
  (category, field, operator, value, action, min_knowledge_state)
values
  ('jain', 'bee_product', 'eq', 'true', 'FAIL', 'DISCOVERED')
on conflict (category, field, coalesce(region, 'GLOBAL')) do nothing;
