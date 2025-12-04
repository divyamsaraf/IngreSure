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
  restaurant_id uuid references public.users(id), -- Assuming restaurant admins are users
  item_name text not null,
  description text,
  ingredients jsonb default '[]'::jsonb, -- List of ingredients
  dietary_type text, -- e.g., Vegan, Gluten-Free
  allergens jsonb default '[]'::jsonb, -- List of allergens
  cuisine_type text,
  submission_status text default 'pending', -- pending, approved, rejected
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
  source_type text, -- e.g., 'verified_submission', 'manual_entry'
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Embeddings for RAG
create table public.embeddings (
  id uuid default gen_random_uuid() primary key,
  item_id uuid references public.verified_items(id) on delete cascade,
  embedding_vector vector(384), -- Adjust dimension based on embedding model (e.g., 384 for all-MiniLM-L6-v2, 768 for others)
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Indexes
create index idx_restaurant_submissions_ingredients on public.restaurant_submissions using gin (ingredients);
create index idx_verified_items_ingredients on public.verified_items using gin (ingredients);
create index idx_verified_items_dietary_type on public.verified_items (dietary_type);
create index idx_verified_items_allergens on public.verified_items using gin (allergens);
