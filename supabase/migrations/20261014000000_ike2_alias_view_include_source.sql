-- Recreate alias resolution view so g.* picks up columns added after the
-- original view (notably ``source`` from 20260919000000). Postgres expands
-- ``g.*`` at CREATE time; ALTER TABLE ADD COLUMN does not refresh the view.
create or replace view public.ike2_v_alias_resolution as
select
  a.normalized_alias,
  a.alias_type,
  a.region,
  a.match_confidence,
  i.id as ingredient_id,
  i.normalized_name,
  g.*
from public.ike2_aliases a
join public.ike2_ingredients i
  on i.id = a.ingredient_id and i.superseded_by is null
join public.ike2_ingredient_groups g
  on g.id = i.group_id
  and g.superseded_by is null
  and g.knowledge_state <> 'DEPRECATED';
