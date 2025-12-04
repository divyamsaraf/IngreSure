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

-- Menu Items (Central table for all items)
create table public.menu_items (
  id uuid default gen_random_uuid() primary key,
  restaurant_id uuid references public.users(id),
  name text not null,
  description text,
  price numeric,
  currency text default 'USD',
  is_available boolean default true,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Item Ingredients (Many-to-Many link or structured list)
create table public.item_ingredients (
  id uuid default gen_random_uuid() primary key,
  menu_item_id uuid references public.menu_items(id) on delete cascade,
  ingredient_name text not null,
  quantity text,
  unit text,
  is_allergen boolean default false,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Tag History (Versioning for tags)
create table public.tag_history (
  id uuid default gen_random_uuid() primary key,
  menu_item_id uuid references public.menu_items(id) on delete cascade,
  tags jsonb default '[]'::jsonb, -- e.g. ["Vegan", "Gluten-Free"]
  changed_by uuid references public.users(id),
  reason text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Verification Logs (LLM results)
create table public.verification_logs (
  id uuid default gen_random_uuid() primary key,
  menu_item_id uuid references public.menu_items(id) on delete cascade,
  is_consistent boolean,
  confidence_score float,
  issues jsonb default '[]'::jsonb,
  suggested_corrections jsonb default '{}'::jsonb,
  verified_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Restaurant Submissions (Staging - kept for backward compatibility if needed, or deprecated)
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

-- Verified Items (Source of Truth - kept for backward compatibility)
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

-- Indexes
create index idx_restaurant_submissions_ingredients on public.restaurant_submissions using gin (ingredients);
create index idx_verified_items_ingredients on public.verified_items using gin (ingredients);
create index idx_verified_items_dietary_type on public.verified_items (dietary_type);
create index idx_verified_items_allergens on public.verified_items using gin (allergens);
create index idx_menu_items_restaurant on public.menu_items(restaurant_id);
create index idx_item_ingredients_item on public.item_ingredients(menu_item_id);
create index idx_verification_logs_item on public.verification_logs(menu_item_id);
