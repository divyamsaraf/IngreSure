-- Add fda_gras and foodex2 to ingredients.source allowed values.

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
        'fda_gras',
        'foodex2',
        'uniprot',
        'admin',
        'system'
      )
    );
end $$;
