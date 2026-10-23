-- Repair only: record migrations whose objects already exist but are missing
-- from supabase_migrations.schema_migrations.
--
-- Local last recorded version: 20260918010000.
-- Objects from 20260919 / 20261003 / 20261014 are already present
-- (ike2_ingredient_groups.source, asserted_flags, and ike2_v_alias_resolution
-- columns from g.*). This script does not apply DDL.
--
-- Expand-only: INSERT missing versions via WHERE NOT EXISTS.
-- Transactional: single BEGIN/COMMIT. Safe to re-run.
-- Do not use this to skip applying those files on a DB that lacks the objects.

begin;

insert into supabase_migrations.schema_migrations (version, name)
select v.version, v.name
from (values
  ('20260919000000', 'ike2_group_provenance_source'),
  ('20261003000000', 'ike2_asserted_flags'),
  ('20261014000000', 'ike2_alias_view_include_source')
) as v(version, name)
where not exists (
  select 1
  from supabase_migrations.schema_migrations existing
  where existing.version = v.version
);

commit;
