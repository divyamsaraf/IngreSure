import requests
import json
import logging
from typing import List

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

class IngredientNormalizer:
    @staticmethod
    def normalize(raw_text: str) -> List[str]:
        """
        Uses Mistral to extract a clean list of ingredients from raw OCR text.
        """
        prompt = f"""
        Task: Extract a clean list of ingredients from the following text.
        
        Rules:
        1. Ignore marketing text, nutrition facts, and addresses.
        2. Normalize names (e.g., "E120" -> "Carmine", "Whey pdr" -> "Whey Powder").
        3. Split compound ingredients (e.g., "Vegetable Oil (Palm, Sunflower)" -> "Palm Oil", "Sunflower Oil").
        4. Return ONLY a JSON array of strings. No other text.

        Raw Text:
        "{raw_text}"

        JSON Output:
        """

        try:
            response = requests.post(OLLAMA_URL, json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json"
            })
            
            if response.status_code == 200:
                result = response.json()
                # Parse the 'response' field which contains the generated text
                generated_json = result.get("response", "[]")
                return json.loads(generated_json)
            else:
                logger.error(f"Ollama Error: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Normalization Failed: {e}")
            return []
