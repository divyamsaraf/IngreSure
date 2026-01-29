import os
import logging
from dotenv import load_dotenv
from rag_service import RAGService

from pathlib import Path

# Load env vars from .env.local (robust path)
env_path = Path(__file__).parent.parent / "frontend" / ".env.local"
print(f"Loading env from: {env_path}")
print(f"File exists: {env_path.exists()}")
load_dotenv(env_path)
print(f"NEXT_PUBLIC_SUPABASE_URL in env: {'NEXT_PUBLIC_SUPABASE_URL' in os.environ}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_embeddings():
    rag = RAGService()
    if not rag.supabase:
        logger.error("Supabase connection failed.")
        return

    logger.info("Fetching menu items without embeddings...")
    
    # Fetch all items (in a real app, verify which ones need embeddings)
    # For now, we'll just re-embed everything for simplicity
    response = rag.supabase.table("menu_items").select("id, name, description").execute()
    items = response.data
    
    logger.info(f"Found {len(items)} items. Generating embeddings...")
    
    for item in items:
        text_to_embed = f"{item['name']} {item['description'] or ''}"
        embedding = rag.generate_embedding(text_to_embed)
        
        # Upsert into embeddings table
        data = {
            "item_id": item['id'],
            "embedding_vector": embedding
        }
        
        # Check if exists first (or just upsert if we had a unique constraint on item_id, which we do in schema but let's be safe)
        # Actually, the schema has id as PK, item_id as FK. We need to check if an embedding exists for this item_id.
        
        existing = rag.supabase.table("embeddings").select("id").eq("item_id", item['id']).execute()
        
        if existing.data:
            # Update
            emb_id = existing.data[0]['id']
            rag.supabase.table("embeddings").update({"embedding_vector": embedding}).eq("id", emb_id).execute()
            logger.info(f"Updated embedding for {item['name']}")
        else:
            # Insert
            rag.supabase.table("embeddings").insert(data).execute()
            logger.info(f"Created embedding for {item['name']}")

    logger.info("Seeding complete.")

if __name__ == "__main__":
    seed_embeddings()
