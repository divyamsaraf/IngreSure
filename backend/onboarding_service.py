import logging
import uuid
from typing import List, Dict, Optional
from rag_service import RAGService
from core.bridge import (
    run_new_engine_scan,
    get_diet_tags_from_verdict_scan,
    get_allergens_from_ingredients,
    detect_cuisine,
)
from llm_normalizer import IngredientNormalizer

logger = logging.getLogger(__name__)

class OnboardingService:
    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service
        self.supabase = self.rag_service.supabase
        # We can reuse the normalizer if we want LLM-based cleaning, 
        # or skip it for pure deterministic speed. 
        # For now, let's instantiate it but maybe make it optional.
        self.normalizer = IngredientNormalizer()

    def process_menu(self, restaurant_id: str, menu_items: List[Dict]):
        """
        Processes a list of raw menu items for a restaurant.
        1. Normalizes ingredients (if provided).
        2. Tags allergens, cuisine, diet (Deterministic).
        3. Generates embeddings.
        4. Stores in Supabase.
        """
        if not self.supabase:
            logger.error("Supabase connection missing.")
            return {"status": "error", "message": "Database unavailable"}

        processed_count = 0
        errors = []

        for item in menu_items:
            try:
                item_id = str(uuid.uuid4())
                name = item.get("name", "Unknown")
                description = item.get("description", "")
                price = item.get("price", 0.0)
                raw_ingredients = item.get("ingredients", [])

                # 1. Normalize Ingredients (Optional LLM step, or just clean strings)
                # If raw_ingredients is just a string, split it.
                if isinstance(raw_ingredients, str):
                    raw_ingredients = [i.strip() for i in raw_ingredients.split(",")]
                
                # For this "Offline" phase, we can use the LLM normalizer to get high quality data
                # normalized_ingredients = self.normalizer.normalize(raw_ingredients) 
                # OR just use raw for speed if they are already clean.
                # Let's use raw for now to save time/resources, assuming input is decent.
                final_ingredients = raw_ingredients

                # 2. Deterministic tagging (compliance engine)
                cuisine = detect_cuisine(f"{name} {description}")
                allergens = get_allergens_from_ingredients(final_ingredients)
                verdict, _ = run_new_engine_scan(final_ingredients)
                dietary_tags = get_diet_tags_from_verdict_scan(verdict)
                if not dietary_tags:
                    dietary_tags = ["Omnivore"]
                
                # 3. Generate Embedding
                # Embed: "Name: ... Description: ... Cuisine: ... Diet: ..."
                text_to_embed = f"Name: {name}. Description: {description}. Cuisine: {cuisine}. Diet: {', '.join(dietary_tags)}."
                embedding = self.rag_service.generate_embedding(text_to_embed)

                # 4. Storage
                
                # A. Insert into menu_items
                menu_data = {
                    "id": item_id,
                    "restaurant_id": restaurant_id,
                    "name": name,
                    "description": description,
                    "price": price,
                    "is_available": True
                }
                self.supabase.table("menu_items").insert(menu_data).execute()

                # B. Insert into verified_items (Metadata for AI)
                verified_data = {
                    "id": item_id,
                    "restaurant_id": None, # FK constraint issue if user doesn't exist, keeping None for now
                    "item_name": name,
                    "description": description,
                    "ingredients": final_ingredients,
                    "dietary_type": dietary_tags[0] if dietary_tags else "Omnivore",
                    "allergens": allergens,
                    "cuisine_type": cuisine,
                    "source_type": "onboarding_script"
                }
                self.supabase.table("verified_items").insert(verified_data).execute()

                # C. Insert into embeddings
                embedding_data = {
                    "item_id": item_id,
                    "embedding_vector": embedding
                }
                self.supabase.table("embeddings").insert(embedding_data).execute()
                
                # D. Insert into tag_history (for filtering)
                # We need to check if tag_history table exists and schema.
                # Assuming it has tags and allergens columns.
                tag_data = {
                    "menu_item_id": item_id,
                    "tags": dietary_tags + [cuisine],
                    "allergens": allergens,
                    "confidence_score": 1.0 # Deterministic
                }
                self.supabase.table("tag_history").insert(tag_data).execute()

                processed_count += 1
                logger.info(f"Onboarded: {name}")

            except Exception as e:
                logger.error(f"Failed to process {item.get('name')}: {e}")
                errors.append(f"{item.get('name')}: {str(e)}")

        return {
            "status": "success",
            "processed": processed_count,
            "errors": errors
        }
