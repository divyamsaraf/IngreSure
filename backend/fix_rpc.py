import os
import logging
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client

# Load env vars
env_path = Path(__file__).parent.parent / "frontend" / ".env.local"
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")

def fix_rpc():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase credentials missing.")
        return

    # Note: This might fail if Anon Key doesn't have permissions to create functions.
    # But we'll try.
    # We can't use supabase-py to execute raw SQL directly usually, unless we use a specific endpoint or function.
    # But supabase-py has `rpc` method. We can't use `rpc` to define a function.
    # We can use `postgrest` client? No.
    
    # Actually, if we don't have a way to execute raw SQL, we are stuck.
    # Supabase-py client doesn't expose a raw SQL method for security reasons.
    
    # However, maybe there is a pre-existing function to exec sql? Unlikely.
    
    # Wait, if I can't execute SQL, I can't fix the function.
    # I should check if I can use the `postgres` connection string?
    # I don't have the DB password.
    
    # Let's try to use the `pg` library or `psycopg2` if I had the connection string.
    # But I only have the API URL and Key.
    
    # If I can't fix it, I must notify the user.
    
    logger.error("Cannot execute raw SQL with Supabase Client to fix RPC.")
    logger.info("Please run the following SQL in your Supabase SQL Editor:")
    
    sql = """
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
        ts_rank(mi.fts, websearch_to_tsquery('english', query_text))::float8 as rank
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
    """
    print(sql)

if __name__ == "__main__":
    fix_rpc()
