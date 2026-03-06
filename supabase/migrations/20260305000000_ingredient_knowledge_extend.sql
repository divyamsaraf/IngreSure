-- Extend ingredient knowledge schema for global hybrid system.
-- - ingredients.source: add fao, ifct, indb, chebi, dbpedia, foodb
-- - ingredient_aliases: optional region for regional/scientific filtering
-- Safe to run when tables already exist (e.g. after 20260223000000_ingredient_knowledge).

-- ------------------------------------------------------------
-- Extend ingredients.source allowed values
-- ------------------------------------------------------------
do $$
declare
  cn name;
  tbl_exists boolean;
begin
  select exists (select 1 from pg_tables where schemaname = 'public' and tablename = 'ingredients') into tbl_exists;
  if not tbl_exists then
    return;
  end if;
  for cn in
    select c.conname
    from pg_constraint c
    join pg_class t on c.conrelid = t.oid
    where t.relname = 'ingredients' and c.contype = 'c'
      and pg_get_constraintdef(c.oid) like '%source%'
  loop
    execute format('alter table public.ingredients drop constraint if exists %I', cn);
  end loop;
  alter table public.ingredients
    add constraint ingredients_source_check check (
      source in (
        'ontology',
        'usda_fdc',
        'open_food_facts',
        'fao',
        'ifct',
        'indb',
        'pubchem',
        'chebi',
        'wikidata',
        'dbpedia',
        'foodb',
        'uniprot',
        'admin',
        'system'
      )
    );
end $$;

-- ------------------------------------------------------------
-- Optional region on aliases (regional/scientific filtering)
-- ------------------------------------------------------------
do $$
begin
  if exists (select 1 from pg_tables where schemaname = 'public' and tablename = 'ingredient_aliases') then
    alter table public.ingredient_aliases add column if not exists region text;
    create index if not exists idx_aliases_region on public.ingredient_aliases (region) where region is not null;
  end if;
end $$;
