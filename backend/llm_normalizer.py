import requests
import json
import logging
from typing import List

from core.config import get_ollama_url, get_ollama_model

logger = logging.getLogger(__name__)

class IngredientNormalizer:
    @staticmethod
    def normalize(raw_text: str) -> List[str]:
        """
        Uses Ollama (configured model, e.g. llama3.2:3b) to extract a clean list of
        ingredients from raw OCR text. Returns [] on failure or if Ollama is unavailable.
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
            response = requests.post(get_ollama_url(), json={
                "model": get_ollama_model(),
                "prompt": prompt,
                "stream": False,
                "format": "json"
            })
            
            if response.status_code == 200:
                result = response.json()
                # Parse the 'response' field which contains the generated text
                generated_json = result.get("response", "[]")
                parsed = json.loads(generated_json)
                # API expects List[str]; LLM may return a dict (e.g. name -> list), so coerce
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
                if isinstance(parsed, dict):
                    return [str(k).strip() for k in parsed if str(k).strip()]
                return []
            else:
                logger.error(f"Ollama Error: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Normalization Failed: {e}")
            return []
