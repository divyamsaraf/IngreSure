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

def seed_user():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Supabase credentials missing.")
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    user_id = "d0d8c19c-3b36-4423-8f5d-8e3607c2d6c6"
    email = "demo@example.com"
    
    # 1. Create User in Auth (Admin API)
    try:
        logger.info("Attempting to create Auth user via Admin API...")
        # Note: With Service Role Key, we can use admin methods.
        # supabase-py v2: supabase.auth.admin.create_user(params)
        
        user_attributes = {
            "email": email,
            "password": "password123",
            "email_confirm": True,
            "user_metadata": {"name": "Demo Restaurant"}
        }
        
        # We want to specify the ID if possible, but create_user usually generates it.
        # Unless we use `create_user_by_id`? Not standard in all clients.
        # Let's just create it and use the returned ID.
        
        user_response = supabase.auth.admin.create_user(user_attributes)
        
        if not user_response.user:
             # Maybe user already exists in Auth but not in public?
             # Try getting user by email
             # list_users is paginated.
             logger.warning("Create user returned no user. Checking if exists...")
             # This part is tricky without a direct 'get_by_email'.
             # Let's assume failure means exists or error.
             pass
        else:
             new_user_id = user_response.user.id
             logger.info(f"Created Auth User: {new_user_id}")
             
             # 2. Insert into public.users
             public_user = {
                "id": new_user_id,
                "name": "Demo Restaurant",
                "email": email,
                "diet_type": "Omnivore"
             }
             supabase.table("users").insert(public_user).execute()
             logger.info(f"Inserted into public.users: {new_user_id}")
             return new_user_id

    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        # Fallback: Try to find the user in public.users if we failed to create
        try:
            res = supabase.table("users").select("id").eq("email", email).execute()
            if res.data:
                logger.info(f"User already exists in public.users: {res.data[0]['id']}")
                return res.data[0]['id']
        except Exception as e2:
            logger.error(f"Could not fetch existing user: {e2}")
            
    return None



if __name__ == "__main__":
    print(seed_user())
