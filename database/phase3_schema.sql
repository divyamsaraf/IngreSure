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

-- Verification Logs (Placeholder for Developer B)
create table public.verification_logs (
  id uuid default gen_random_uuid() primary key,
  menu_item_id uuid references public.menu_items(id) on delete cascade,
  verification_result jsonb,
  verifier_model text,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Indexes
create index idx_menu_items_restaurant_id on public.menu_items(restaurant_id);
create index idx_item_ingredients_menu_item_id on public.item_ingredients(menu_item_id);
create index idx_tag_history_menu_item_id on public.tag_history(menu_item_id);
