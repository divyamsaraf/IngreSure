-- Ingredient Knowledge (Canonical Identity) Schema
-- Phase 3 foundation: create canonical groups, ingredients, aliases, unknown log, metrics.
-- NOTE: This migration only adds tables/indexes. It does NOT change runtime behavior yet.

-- ------------------------------------------------------------
-- Canonical ingredient groups (single compliance truth)
-- ------------------------------------------------------------
create table if not exists public.ingredient_groups (
  id uuid default gen_random_uuid() primary key,
  canonical_name text not null,

  -- Origin classification
  origin_type text check (origin_type in ('plant','animal','synthetic','microbial','fungal','insect','unknown')),
  animal_species text,

  -- Compliance-relevant flags (match backend Ingredient schema)
  animal_origin boolean default false,
  plant_origin boolean default false,
  synthetic boolean default false,
  fungal boolean default false,
  insect_derived boolean default false,
  egg_source boolean default false,
  dairy_source boolean default false,
  gluten_source boolean default false,
  nut_source text,
  soy_source boolean default false,
  sesame_source boolean default false,
  alcohol_content double precision,
  root_vegetable boolean default false,
  onion_source boolean default false,
  garlic_source boolean default false,
  fermented boolean default false,

  -- Knowledge lifecycle
  knowledge_state text not null default 'UNKNOWN'
    check (knowledge_state in ('UNKNOWN','DISCOVERED','AUTO_CLASSIFIED','VERIFIED','LOCKED')),

  -- Versioning (never overwrite; supersede)
  version integer not null default 1,
  superseded_by uuid references public.ingredient_groups(id),

  -- Metadata
  uncertainty_flags jsonb default '[]'::jsonb,
  derived_from jsonb default '[]'::jsonb,
  contains jsonb default '[]'::jsonb,
  may_contain jsonb default '[]'::jsonb,
  regions jsonb default '[]'::jsonb,

  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Canonical name must be unique among ACTIVE rows only
create unique index if not exists idx_ingredient_groups_canonical_active
  on public.ingredient_groups (canonical_name)
  where superseded_by is null;

create index if not exists idx_ingredient_groups_state
  on public.ingredient_groups (knowledge_state)
  where superseded_by is null;

create index if not exists idx_ingredient_groups_origin
  on public.ingredient_groups (origin_type)
  where superseded_by is null;

-- ------------------------------------------------------------
-- Ingredient entries (names/strings that map to a group)
-- ------------------------------------------------------------
create table if not exists public.ingredients (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  normalized_name text not null,
  group_id uuid not null references public.ingredient_groups(id),

  source text not null check (source in ('ontology','usda_fdc','open_food_facts','pubchem','wikidata','admin','system')),
  confidence text not null default 'high' check (confidence in ('high','medium','low')),

  version integer not null default 1,
  superseded_by uuid references public.ingredients(id),

  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Normalized name must be unique among ACTIVE rows only
create unique index if not exists idx_ingredients_normalized_active
  on public.ingredients (normalized_name)
  where superseded_by is null;

create index if not exists idx_ingredients_group_id
  on public.ingredients (group_id)
  where superseded_by is null;

create index if not exists idx_ingredients_source
  on public.ingredients (source)
  where superseded_by is null;

-- ------------------------------------------------------------
-- Aliases (normalized routing layer) -> ingredient -> group
-- ------------------------------------------------------------
create table if not exists public.ingredient_aliases (
  id uuid default gen_random_uuid() primary key,
  alias text not null,
  normalized_alias text not null,
  ingredient_id uuid not null references public.ingredients(id) on delete cascade,

  alias_type text not null default 'synonym'
    check (alias_type in ('canonical','synonym','e_number','brand_name','regional','misspelling','abbreviation','scientific')),
  language text not null default 'en',

  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create unique index if not exists idx_aliases_normalized_unique
  on public.ingredient_aliases (normalized_alias);

create index if not exists idx_aliases_ingredient_id
  on public.ingredient_aliases (ingredient_id);

create index if not exists idx_aliases_type
  on public.ingredient_aliases (alias_type);

-- ------------------------------------------------------------
-- Unknown ingredient log (discovery queue)
-- ------------------------------------------------------------
create table if not exists public.unknown_ingredients (
  id uuid default gen_random_uuid() primary key,
  normalized_key text not null,
  raw_inputs jsonb default '[]'::jsonb,
  frequency integer not null default 1,
  first_seen timestamp with time zone default timezone('utc'::text, now()) not null,
  last_seen timestamp with time zone default timezone('utc'::text, now()) not null,

  resolved boolean not null default false,
  resolved_group_id uuid references public.ingredient_groups(id),
  resolution_source text,
  resolution_attempts integer not null default 0,
  last_attempt_at timestamp with time zone,

  restriction_ids_sample jsonb default '[]'::jsonb,
  profile_context_sample jsonb
);

create unique index if not exists idx_unknown_normalized_key_unique
  on public.unknown_ingredients (normalized_key);

create index if not exists idx_unknown_pending
  on public.unknown_ingredients (resolved, resolution_attempts, frequency desc)
  where resolved = false;

-- ------------------------------------------------------------
-- Enrichment metrics (coverage tracking)
-- ------------------------------------------------------------
create table if not exists public.enrichment_metrics (
  id uuid default gen_random_uuid() primary key,
  date date not null,
  total_queries integer not null default 0,
  resolved_static integer not null default 0,
  resolved_cache integer not null default 0,
  resolved_db integer not null default 0,
  resolved_api integer not null default 0,
  unresolved integer not null default 0,
  avg_resolution_time_ms double precision,
  coverage_percent double precision,
  new_groups_created integer not null default 0,
  new_aliases_added integer not null default 0,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  unique(date)
);

