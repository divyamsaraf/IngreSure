-- Pescatarian: fail on any land-animal meat (not a hardcoded species list).
-- Also remove the incomplete cow/pig/chicken/lamb/goat-only rule if present.
delete from public.ike2_restriction_rules
 where category = 'pescatarian' and field = 'animal_species';

insert into public.ike2_restriction_rules
  (category, field, operator, value, action, min_knowledge_state)
values
  ('pescatarian', 'meat_land_derived', 'eq', 'true', 'FAIL', 'DISCOVERED')
on conflict (category, field, coalesce(region, 'GLOBAL')) do nothing;
