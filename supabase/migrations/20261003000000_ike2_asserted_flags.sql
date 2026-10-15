-- Item 11: asserted_flags — which bool columns were deliberately set
-- (true or false), vs dataclass/adapter default false.
alter table public.ike2_ingredient_groups
  add column if not exists asserted_flags text[] not null default '{}';
