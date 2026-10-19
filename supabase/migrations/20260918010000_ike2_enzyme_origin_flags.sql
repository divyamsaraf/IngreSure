-- Item 3.1 Prompt 2: enzyme origin subtype flags (Option A).
-- Additive columns on ike2_ingredient_groups + RULE_SEED parity inserts.

alter table public.ike2_ingredient_groups
  add column if not exists enzyme_animal_source boolean not null default false;

alter table public.ike2_ingredient_groups
  add column if not exists enzyme_microbial_source boolean not null default false;

-- Animal enzyme implies animal_origin (same spirit as egg_implies_animal).
alter table public.ike2_ingredient_groups
  drop constraint if exists enzyme_animal_implies_animal;

alter table public.ike2_ingredient_groups
  add constraint enzyme_animal_implies_animal
  check (not enzyme_animal_source or animal_origin);

-- Prefer not claiming both animal and microbial enzyme origin at once.
alter table public.ike2_ingredient_groups
  drop constraint if exists enzyme_origin_not_both;

alter table public.ike2_ingredient_groups
  add constraint enzyme_origin_not_both
  check (not (enzyme_animal_source and enzyme_microbial_source));

comment on column public.ike2_ingredient_groups.enzyme_animal_source is
  'Item 3.1: animal-derived enzyme (e.g. rennet). Implies animal_origin.';
comment on column public.ike2_ingredient_groups.enzyme_microbial_source is
  'Item 3.1: microbial/fermentation enzyme; not animal. Bare enzymes stay unknown.';

-- Diets that forbid animal enzymes (Prompt 1). Bare enzymes remain verdict_cap WARN.
insert into public.ike2_restriction_rules
  (category, field, operator, value, action, min_knowledge_state)
values
  ('vegan',            'enzyme_animal_source', 'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('vegetarian',       'enzyme_animal_source', 'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('lacto_vegetarian', 'enzyme_animal_source', 'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('ovo_vegetarian',   'enzyme_animal_source', 'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('hindu_vegetarian', 'enzyme_animal_source', 'eq', 'true', 'FAIL', 'DISCOVERED'),
  ('jain',             'enzyme_animal_source', 'eq', 'true', 'FAIL', 'DISCOVERED')
on conflict (category, field, coalesce(region, 'GLOBAL')) do nothing;
