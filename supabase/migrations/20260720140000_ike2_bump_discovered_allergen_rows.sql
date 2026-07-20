-- Curated allergen/diet rows seeded as DISCOVERED cannot assert medical FAIL
-- (min AUTO_CLASSIFIED) and demote clean SAFE → WARN/Depends. Bump them.
update public.ike2_ingredient_groups
   set knowledge_state = 'AUTO_CLASSIFIED'
 where knowledge_state = 'DISCOVERED'
   and (
        coalesce(fish_source, false)
     or coalesce(shellfish_source, false)
     or coalesce(peanut_source, false)
     or coalesce(tree_nut_source, false)
     or coalesce(egg_source, false)
     or coalesce(dairy_source, false)
     or coalesce(soy_source, false)
     or coalesce(gluten_source, false)
     or coalesce(sesame_source, false)
     or coalesce(insect_derived, false)
     or coalesce(bee_product, false)
   );
