-- Vegetarian-style diets must fail insect-derived additives (carmine, shellac).
-- Honey remains allowed via bee_product (distinct from insect_derived).
insert into public.ike2_restriction_rules
  (category, field, operator, value, action, min_knowledge_state)
values
  ('hindu_vegetarian', 'insect_derived', 'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('vegetarian',       'insect_derived', 'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('lacto_vegetarian', 'insect_derived', 'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('ovo_vegetarian',   'insect_derived', 'eq', 'true', 'FAIL', 'DISCOVERED')
on conflict (category, field, coalesce(region, 'GLOBAL')) do nothing;
