-- IKE-2 (IngreSure Knowledge Engine v2) schema.
-- Greenfield ike2_* tables that run in parallel with the legacy ingredient_* path.
-- Backend-only: RLS enabled with NO policies => only the service_role key can access.
-- Safety CHECK constraints implement the fail-closed correctness contract (design §3).

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
do $$ begin
  create type ike2_knowledge_state as enum (
    'UNCLASSIFIED', 'DISCOVERED', 'AUTO_CLASSIFIED', 'VERIFIED', 'LOCKED', 'DEPRECATED'
  );
exception when duplicate_object then null; end $$;

-- ---------------------------------------------------------------------------
-- 5.1 ike2_ingredient_groups — canonical identity + compliance truth
-- ---------------------------------------------------------------------------
create table if not exists public.ike2_ingredient_groups (
  id uuid primary key default gen_random_uuid(),
  canonical_name text not null unique,
  slug text,

  -- origin
  animal_origin boolean not null default false,
  plant_origin boolean not null default false,
  synthetic boolean not null default false,
  fungal boolean not null default false,
  insect_derived boolean not null default false,

  -- allergen flags (full booleans; one ingredient can be several allergens)
  egg_source boolean not null default false,
  dairy_source boolean not null default false,
  gluten_source boolean not null default false,
  soy_source boolean not null default false,
  sesame_source boolean not null default false,
  peanut_source boolean not null default false,
  tree_nut_source boolean not null default false,
  fish_source boolean not null default false,
  shellfish_source boolean not null default false,
  mustard_source boolean not null default false,
  celery_source boolean not null default false,
  lupin_source boolean not null default false,
  sulphite_source boolean not null default false,

  -- meat / diet
  animal_species text,                 -- retained ONLY for halal/kosher meat-species rules
  root_vegetable boolean not null default false,
  onion_source boolean not null default false,
  garlic_source boolean not null default false,
  fermented boolean not null default false,
  alcohol_content numeric,
  alcohol_role text not null default 'none'
    check (alcohol_role in ('none', 'ingredient', 'fermentation_trace')),

  -- knowledge
  knowledge_state ike2_knowledge_state not null default 'UNCLASSIFIED',
  classification_method text,
  verdict_cap text,                    -- nullable; e.g. 'WARN'
  primary_source_url text,
  uncertainty_flags text[] not null default '{}',

  -- lifecycle
  superseded_by uuid references public.ike2_ingredient_groups(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  version integer not null default 1,

  -- safety CHECK constraints (design §3)
  constraint insect_implies_animal check (not insect_derived or animal_origin),
  constraint egg_implies_animal check (not egg_source or animal_origin),
  constraint dairy_implies_animal check (not dairy_source or animal_origin),
  constraint fish_implies_animal check (not fish_source or animal_origin),
  constraint shellfish_implies_animal check (not shellfish_source or animal_origin),
  constraint verified_requires_source check (
    knowledge_state not in ('VERIFIED', 'LOCKED') or primary_source_url is not null
  ),
  -- a group claiming both animal and plant origin must flag the uncertainty
  constraint dual_origin_requires_uncertainty check (
    not (animal_origin and plant_origin)
    or array_length(uncertainty_flags, 1) is not null
  )
);

-- ---------------------------------------------------------------------------
-- 5.2 ike2_ingredients — named substance forms per group
-- ---------------------------------------------------------------------------
create table if not exists public.ike2_ingredients (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.ike2_ingredient_groups(id) on delete cascade,
  normalized_name text not null,
  source text,
  superseded_by uuid references public.ike2_ingredients(id),
  created_at timestamptz not null default now()
);
create index if not exists ike2_ingredients_group_idx on public.ike2_ingredients (group_id);
create index if not exists ike2_ingredients_norm_idx on public.ike2_ingredients (normalized_name);

-- ---------------------------------------------------------------------------
-- 5.3 ike2_aliases — routing layer (raw string -> ingredient)
-- ---------------------------------------------------------------------------
create table if not exists public.ike2_aliases (
  id uuid primary key default gen_random_uuid(),
  normalized_alias text not null,
  ingredient_id uuid not null references public.ike2_ingredients(id) on delete cascade,
  alias_type text not null default 'common'
    check (alias_type in (
      'common', 'brand', 'regional', 'misspelling',
      'e_number', 'cas_number', 'fda_number', 'iupac_name'
    )),
  language text,
  region text,
  match_confidence text not null default 'high'
    check (match_confidence in ('exact', 'high', 'possible')),
  source text,
  created_at timestamptz not null default now()
);

-- Global unique for unambiguous code types only.
create unique index if not exists ike2_aliases_global_code_uidx
  on public.ike2_aliases (normalized_alias)
  where alias_type in ('e_number', 'cas_number', 'fda_number', 'iupac_name');

-- Region-scoped unique for everything else.
create unique index if not exists ike2_aliases_region_uidx
  on public.ike2_aliases (normalized_alias, coalesce(region, 'GLOBAL'))
  where alias_type not in ('e_number', 'cas_number', 'fda_number', 'iupac_name');

-- ---------------------------------------------------------------------------
-- 5.4 ike2_alias_disambiguation — known conflicts
-- ---------------------------------------------------------------------------
create table if not exists public.ike2_alias_disambiguation (
  id uuid primary key default gen_random_uuid(),
  normalized_alias text not null,
  context_region text,
  ingredient_id uuid not null references public.ike2_ingredients(id) on delete cascade,
  priority integer not null default 0,
  notes text
);
create index if not exists ike2_alias_disambig_idx
  on public.ike2_alias_disambiguation (normalized_alias);

-- ---------------------------------------------------------------------------
-- 5.5 ike2_restriction_rules — deterministic rule config
-- ---------------------------------------------------------------------------
create table if not exists public.ike2_restriction_rules (
  id uuid primary key default gen_random_uuid(),
  category text not null,
  field text not null,
  operator text not null default 'eq',
  value text,
  action text not null check (action in ('FAIL', 'WARN')),
  min_knowledge_state ike2_knowledge_state not null default 'AUTO_CLASSIFIED',
  region text,
  version integer not null default 1
);

-- ---------------------------------------------------------------------------
-- 5.6 ike2_resolution_cache — write-only audit/analytics (NEVER read on hot path)
-- ---------------------------------------------------------------------------
create table if not exists public.ike2_resolution_cache (
  id uuid primary key default gen_random_uuid(),
  normalized_key text not null,
  region text,
  resolved jsonb,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 5.7 ike2_unknown_queue — discovery + enrichment
-- ---------------------------------------------------------------------------
create table if not exists public.ike2_unknown_queue (
  id uuid primary key default gen_random_uuid(),
  normalized_key text not null unique,
  frequency integer not null default 1,
  enrichment jsonb,
  classification_decision text,
  status text not null default 'pending',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- 5.8 Shadow + ops tables
-- ---------------------------------------------------------------------------
create table if not exists public.ike2_shadow_diffs (
  id uuid primary key default gen_random_uuid(),
  raw_input text,
  legacy_verdict text,
  ike2_verdict text,
  match boolean,
  false_safe_regression boolean not null default false,
  detail jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.ike2_group_merges (
  id uuid primary key default gen_random_uuid(),
  from_group_id uuid,
  into_group_id uuid,
  rollback_snapshot jsonb,
  created_at timestamptz not null default now()
);

-- Staging mirrors (no UNIQUE/CHECK so raw rows land, validated downstream) + reject quarantine.
create schema if not exists ike2_staging;

create table if not exists ike2_staging.ingredient_groups (
  id uuid primary key default gen_random_uuid(),
  source text,
  raw jsonb,
  created_at timestamptz not null default now()
);

create table if not exists ike2_staging.stg_rejects (
  id uuid primary key default gen_random_uuid(),
  source text,
  raw jsonb,
  violated_constraint text,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Single-query resolution view (alias -> ingredient -> group), active rows only
-- ---------------------------------------------------------------------------
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

-- ---------------------------------------------------------------------------
-- RLS: backend-only. Enable with no policies => only service_role can access.
-- ---------------------------------------------------------------------------
alter table public.ike2_ingredient_groups enable row level security;
alter table public.ike2_ingredients enable row level security;
alter table public.ike2_aliases enable row level security;
alter table public.ike2_alias_disambiguation enable row level security;
alter table public.ike2_restriction_rules enable row level security;
alter table public.ike2_resolution_cache enable row level security;
alter table public.ike2_unknown_queue enable row level security;
alter table public.ike2_shadow_diffs enable row level security;
alter table public.ike2_group_merges enable row level security;
