-- ===========================================================================
-- IKE-2 restriction rule seed (design §5.5).
-- Mirrors core/knowledge/ike2/rules.py::RULE_SEED (single source of truth for
-- the loader/tests; this file seeds the live table). Keep the two in sync — the
-- test `test_seed_sql_covers_rule_seed` guards drift.
--
-- Scope: boolean group flags, alcohol rule, and multi-field religious/lifestyle
-- rules (animal_species, meat_fish_derived, alcohol_content). Species/multi-field
-- restrictions omitted here previously caused UNCERTAIN via the coverage guard;
-- they are now seeded to match data/restrictions.json semantics.
-- ===========================================================================

-- Natural key for idempotent re-seeding.
create unique index if not exists ike2_restriction_rules_uidx
  on public.ike2_restriction_rules (category, field, coalesce(region, 'GLOBAL'));

insert into public.ike2_restriction_rules
  (category, field, operator, value, action, min_knowledge_state)
values
  -- allergens (safety)
  ('peanut_allergy',    'peanut_source',    'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('tree_nut_allergy',  'tree_nut_source',  'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('soy_allergy',       'soy_source',       'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('sesame_allergy',    'sesame_source',    'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('fish_allergy',      'fish_source',      'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('shellfish_allergy', 'shellfish_source', 'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('mustard_allergy',   'mustard_source',   'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('lupin_allergy',     'lupin_source',     'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('celery_allergy',    'celery_source',    'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('onion_allergy',     'onion_source',     'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('garlic_allergy',    'garlic_source',    'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  -- medical
  ('gluten_free',       'gluten_source',    'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('celiac_strict',     'gluten_source',    'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('lactose_free',      'dairy_source',     'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('dairy_free',        'dairy_source',     'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('egg_free',          'egg_source',       'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  ('sulfite_sensitive', 'sulphite_source',  'eq', 'true', 'FAIL', 'AUTO_CLASSIFIED'),
  -- lifestyle / preference
  ('vegan',             'animal_origin',    'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('no_insect_derived', 'insect_derived',   'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('no_onion',          'onion_source',     'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('no_garlic',         'garlic_source',    'eq', 'true', 'FAIL', 'DISCOVERED'),
  -- alcohol (compliance keys off alcohol_role: ingredient->FAIL, fermentation_trace->WARN)
  ('no_alcohol',        'alcohol_role',     'ne', 'none', 'FAIL', 'DISCOVERED'),
  -- religious / multi-field
  ('halal',             'alcohol_content',  'gt', '0',    'FAIL', 'DISCOVERED'),
  ('halal',             'animal_species',   'eq', 'pig',  'FAIL', 'DISCOVERED'),
  ('halal',             'insect_derived',   'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('kosher',            'animal_species',   'in_list', '["pig","shellfish"]', 'FAIL', 'DISCOVERED'),
  ('kosher',            'shellfish_source', 'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('kosher',            'insect_derived',   'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('hindu_vegetarian',  'meat_fish_derived','eq', 'true', 'FAIL', 'DISCOVERED'),
  ('hindu_vegetarian',  'egg_source',       'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('hindu_vegetarian',  'insect_derived',   'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('hindu_non_vegetarian', 'animal_species','in_list', '["cow","pig"]', 'FAIL', 'DISCOVERED'),
  ('hindu_non_vegetarian', 'insect_derived','eq', 'true', 'FAIL', 'DISCOVERED'),
  ('jain',              'meat_fish_derived','eq', 'true', 'FAIL', 'DISCOVERED'),
  ('jain',              'egg_source',       'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('jain',              'insect_derived',   'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('jain',              'bee_product',      'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('jain',              'root_vegetable',   'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('jain',              'alcohol_content',  'gt', '0',    'FAIL', 'DISCOVERED'),
  ('jain',              'onion_source',     'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('jain',              'garlic_source',    'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('jain',              'fermented',        'eq', 'true', 'WARN', 'DISCOVERED'),
  ('jain',              'fungal',           'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('vegetarian',        'meat_fish_derived','eq', 'true', 'FAIL', 'DISCOVERED'),
  ('vegetarian',        'insect_derived',   'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('lacto_vegetarian',  'meat_fish_derived','eq', 'true', 'FAIL', 'DISCOVERED'),
  ('lacto_vegetarian',  'egg_source',       'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('lacto_vegetarian',  'insect_derived',   'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('ovo_vegetarian',    'meat_fish_derived','eq', 'true', 'FAIL', 'DISCOVERED'),
  ('ovo_vegetarian',    'dairy_source',     'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('ovo_vegetarian',    'insect_derived',   'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('pescatarian',       'meat_land_derived','eq', 'true', 'FAIL', 'DISCOVERED')
on conflict (category, field, coalesce(region, 'GLOBAL')) do nothing;
