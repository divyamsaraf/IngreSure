-- Consolidated Migration Script

-- ==========================================
-- FROM schema.sql (Phase 1/2) - Base Tables
-- ==========================================

-- Enable pgvector extension for embeddings
create extension if not exists vector;

-- Users table
create table public.users (
  id uuid references auth.users not null primary key,
  name text,
  email text unique,
  allergies jsonb default '[]'::jsonb,
  diet_type text,
  preferences jsonb default '{}'::jsonb,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Restaurant Submissions (Staging)
create table public.restaurant_submissions (
  id uuid default gen_random_uuid() primary key,
  restaurant_id uuid references public.users(id),
  item_name text not null,
  description text,
  ingredients jsonb default '[]'::jsonb,
  dietary_type text,
  allergens jsonb default '[]'::jsonb,
  cuisine_type text,
  submission_status text default 'pending',
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Verified Items (Source of Truth)
create table public.verified_items (
  id uuid default gen_random_uuid() primary key,
  restaurant_id uuid references public.users(id),
  item_name text not null,
  description text,
  ingredients jsonb default '[]'::jsonb,
  dietary_type text,
  allergens jsonb default '[]'::jsonb,
  cuisine_type text,
  source_type text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Embeddings for RAG
create table public.embeddings (
  id uuid default gen_random_uuid() primary key,
  item_id uuid references public.verified_items(id) on delete cascade,
  embedding_vector vector(384),
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Indexes from schema.sql
create index idx_restaurant_submissions_ingredients on public.restaurant_submissions using gin (ingredients);
create index idx_verified_items_ingredients on public.verified_items using gin (ingredients);
create index idx_verified_items_dietary_type on public.verified_items (dietary_type);
create index idx_verified_items_allergens on public.verified_items using gin (allergens);


-- ==========================================
-- FROM phase3_schema.sql - Core Menu Tables
-- ==========================================

-- Menu Items Table
create table public.menu_items (
  id uuid default gen_random_uuid() primary key,
  restaurant_id uuid references public.users(id),
  name text not null,
  description text,
  price numeric,
  currency text default 'USD',
  category text, -- e.g., Appetizer, Main Course
  image_url text,
  is_available boolean default true,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Item Ingredients (Normalized)
create table public.item_ingredients (
  id uuid default gen_random_uuid() primary key,
  menu_item_id uuid references public.menu_items(id) on delete cascade,
  ingredient_name text not null,
  quantity text, -- e.g., "100g", "1 cup"
  is_optional boolean default false,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Tag History (Versioning for Tags)
create table public.tag_history (
  id uuid default gen_random_uuid() primary key,
  menu_item_id uuid references public.menu_items(id) on delete cascade,
  tags jsonb default '[]'::jsonb, -- Array of tags: ["Vegan", "Gluten-Free"]
  allergens jsonb default '[]'::jsonb, -- Array of allergens
  source text, -- "auto-tagging", "manual", "llm-verification"
  confidence_score numeric, -- 0.0 to 1.0
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Verification Logs
create table public.verification_logs (
  id uuid default gen_random_uuid() primary key,
  menu_item_id uuid references public.menu_items(id) on delete cascade,
  verification_result jsonb,
  verifier_model text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Indexes from phase3
create index idx_menu_items_restaurant_id on public.menu_items(restaurant_id);
create index idx_item_ingredients_menu_item_id on public.item_ingredients(menu_item_id);
create index idx_tag_history_menu_item_id on public.tag_history(menu_item_id);


-- ==========================================
-- FROM phase5_schema.sql - Search & Functions
-- ==========================================

-- Enable pg_trgm extension for fuzzy search
create extension if not exists pg_trgm;

-- Add Full Text Search Index to menu_items
alter table public.menu_items
add column fts tsvector generated always as (to_tsvector('english', name || ' ' || coalesce(description, ''))) stored;

create index idx_menu_items_fts on public.menu_items using gin (fts);

-- Ensure embeddings table is ready for vector search
create index if not exists idx_embeddings_item_id on public.embeddings(item_id);

-- Hybrid Search Function
create or replace function search_menu_items(
  query_text text,
  query_embedding vector(384),
  match_threshold float,
  match_count int,
  filter_dietary text[],
  filter_allergens text[]
)
returns table (
  id uuid,
  name text,
  description text,
  price numeric,
  restaurant_id uuid,
  similarity float,
  rank float
)
language plpgsql
as $$
begin
  return query
  select
    mi.id,
    mi.name,
    mi.description,
    mi.price,
    mi.restaurant_id,
    1 - (e.embedding_vector <=> query_embedding) as similarity,
    ts_rank(mi.fts, websearch_to_tsquery('english', query_text)) as rank
  from public.menu_items mi
  join public.embeddings e on mi.id = e.item_id
  left join public.tag_history th on mi.id = th.menu_item_id
  where 1 - (e.embedding_vector <=> query_embedding) > match_threshold
  and (query_text = '' or mi.fts @@ websearch_to_tsquery('english', query_text))
  and (filter_dietary is null or (th.tags ?& filter_dietary))
  and (filter_allergens is null or not (th.allergens ?| filter_allergens))
  order by rank desc, similarity desc
  limit match_count;
end;
$$;
