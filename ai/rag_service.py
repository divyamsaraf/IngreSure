import os
import logging
from functools import lru_cache
from typing import List, Dict, Generator
from sentence_transformers import SentenceTransformer
from supabase import create_client, Client
import requests
import json
from dietary_rules import DietaryRuleEngine

# Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        logger.info("Initializing RAG Service...")
        
        # Load Config inside init to ensure env vars are loaded
        self.supabase_url = os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
        self.supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        
        print(f"RAG Service Config: URL={self.supabase_url}, KEY={'Found' if self.supabase_key else 'Missing'}")

        # 1. Load Embedding Model (Local)
        # all-MiniLM-L6-v2 is fast and effective (384 dims)
        self.embed_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 2. Connect to Supabase
        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase credentials not found in env. RAG will fail.")
            self.supabase = None
        else:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def generate_embedding(self, text: str) -> List[float]:
        """Generates a 384-dim embedding for the given text."""
        return self.embed_model.encode(text).tolist()

    @lru_cache(maxsize=100)
    def retrieve(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Retrieves relevant menu items from Supabase using vector search.
        Cached to improve performance on repeated queries.
        """
        if not self.supabase:
            return []

        try:
            # 1. Preprocess Query (Extract Filters)
            filters = DietaryRuleEngine.extract_filters(query)
            filter_dietary = filters["dietary"] if filters["dietary"] else None
            filter_allergens = filters["allergens"] if filters["allergens"] else None
            
            logger.info(f"Retrieving with filters - Diet: {filter_dietary}, Allergens: {filter_allergens}")

            # 2. Generate query embedding
            query_embedding = self.generate_embedding(query)
            
            # 3. Call RPC function
            # Note: We pass query_text="" to disable strict FTS filtering and rely on vector similarity.
            # The RPC function uses AND logic for FTS, which breaks natural language queries.
            response = self.supabase.rpc(
                'search_menu_items',
                {
                    'query_text': "", 
                    'query_embedding': query_embedding,
                    'match_threshold': 0.3, # Maybe lower this if filtering is strict?
                    'match_count': limit,
                    'filter_dietary': filter_dietary,
                    'filter_allergens': filter_allergens
                }
            ).execute()
            
            return response.data
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []

    def generate_answer_stream(self, query: str, context_items: List[Dict]) -> Generator[str, None, None]:
        """
        Generates a streaming answer using Mistral-7B.
        Yields chunks of text as they are generated.
        """
        # Format context
        if not context_items:
            context_str = "No specific menu items matched the criteria."
        else:
            context_str = "\n".join([
                f"- {item['name']}: {item['description']} (Price: ${item['price']})"
                for item in context_items
            ])
        
        # Restaurant Persona Prompt
        prompt = f"""
        You are a friendly and helpful waiter at a restaurant. Your goal is to assist the customer with their order or questions based ONLY on the menu items provided below.
        
        Rules:
        1. Be polite, welcoming, and professional.
        2. Use the provided "Menu Context" to answer. Do not make up items.
        3. If the user mentions diet/allergens, reassure them if the retrieved items fit.
        4. Mention prices where relevant.
        5. If no items match (context is empty), apologize and suggest general alternatives or ask for different preferences.
        6. Keep answers concise (2-3 sentences max) unless listing multiple options.

        Menu Context:
        {context_str}
        
        Customer: {query}
        
        Waiter:
        """
        
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": True
        }
        
        try:
            # logger.info("Starting Ollama stream...")
            with requests.post(OLLAMA_API_URL, json=payload, stream=True, timeout=300) as response:
                response.raise_for_status()
                # logger.info("Ollama connected. Reading lines...")
                for line in response.iter_lines():
                    if line:
                        body = json.loads(line)
                        token = body.get("response", "")
                        if token:
                            yield token
                        if body.get("done", False):
                            break
                            
        except Exception as e:
            logger.error(f"Streaming Generation failed: {e}")
            yield "I'm having trouble connecting to my brain right now."

    # Removed duplicate generate_answer method to avoid confusion
