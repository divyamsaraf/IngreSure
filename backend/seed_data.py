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

def seed_data():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase credentials missing.")
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Sample Data from seed.sql
    items = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Vegan Buddha Bowl",
            "description": "Quinoa, roasted chickpeas, avocado, and tahini dressing.",
            "price": 12.99,
            "is_available": True
        },
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "name": "Classic Cheeseburger",
            "description": "Beef patty, cheddar cheese, lettuce, tomato, brioche bun.",
            "price": 14.50,
            "is_available": True
        },
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "name": "Chicken Tikka Masala",
            "description": "Grilled chicken in creamy tomato curry sauce.",
            "price": 16.00,
            "is_available": True
        }
    ]
    
    for item in items:
        try:
            # 1. Insert into menu_items
            existing_menu = supabase.table("menu_items").select("id").eq("id", item['id']).execute()
            if not existing_menu.data:
                supabase.table("menu_items").insert(item).execute()
                logger.info(f"Inserted {item['name']} into menu_items")
            else:
                logger.info(f"Skipped {item['name']} in menu_items (already exists)")

            # 2. Insert into verified_items (to satisfy FK for embeddings)
            # verified_items has slightly different schema, but we just need id and name mostly
            verified_item = {
                "id": item['id'],
                "restaurant_id": None, # User doesn't exist, leaving null
                "item_name": item['name'],
                "description": item['description'],
                "ingredients": [], # Mock
                "dietary_type": "Unknown",
                "allergens": [],
                "cuisine_type": "Global",
                "source_type": "manual"
            }
            
            existing_verified = supabase.table("verified_items").select("id").eq("id", item['id']).execute()
            if not existing_verified.data:
                supabase.table("verified_items").insert(verified_item).execute()
                logger.info(f"Inserted {item['name']} into verified_items")
            else:
                logger.info(f"Skipped {item['name']} in verified_items (already exists)")
                
        except Exception as e:
            logger.error(f"Failed to insert {item['name']}: {e}")

if __name__ == "__main__":
    seed_data()
