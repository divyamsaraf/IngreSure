
-- Phase 5: Global Search Updates

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
