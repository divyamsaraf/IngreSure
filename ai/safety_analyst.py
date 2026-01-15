import logging
import requests
import json
from typing import Generator, List, Dict, Optional

logger = logging.getLogger(__name__)

# Reusing config from rag_service for consistency
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

class SafetyAnalyst:
    """
    Analyzes ingredient lists/product queries against strict dietary and religious standards.
    Supported Profiles:
    - Vegan / Vegetarian
    - Gluten-Free
    - Halal (Islamic)
    - Kosher (Jewish)
    - Hindu (No beef, often vegetarian)
    - Jain (Strict vegetarian, no root vegetables like garlic/onion)
    - Sikh (No Halal/Kutha meat)
    - Allergen-Specific (Nut-free, etc.)
    """

    SYSTEM_PROMPT = """
    System role: You are IngreSure SafetyAnalyst, a grocery safety assistant that behaves like a knowledgeable human grocery expert.

    **CORE RULES:**
    1. **Strict Non-Assumption**: NEVER assume a diet (Hindu, Jain, Halal). If the user hasn't specified one, ASK.
    2. **Interaction**:
       - If {profile} is 'unknown': Analyze for general allergens/additives, then politely ask: "Before I check further, do you have specific religious or dietary restrictions?"
       - If {profile} is specified: Be STRICT and confident.
    3. **No False Uncertainty**: 
       - Milk, Cream, Sugar, Corn Syrup, Carrageenan, Gums are CONFIDENT YES (unless banned by profile).
       - Do not hedge on these.
    4. **Response Structure**:
       - Direct Answer (Yes/No/Unclear)
       - Brief Why (1-3 ingredients)
       - Honest Confidence

    **Truth Tables (Only apply if profile matches):**
    - **Hindu**: Milk=OK, Meat/Eggs=NO.
    - **Jain**: Root Veg/Meat=NO.
    - **Halal**: Pork/Alcohol=NO.
    - **Vegan**: All Animal=NO.

    User Query: {query}
    
    Response:
    """

    @staticmethod
    def _extract_profile(query: str) -> Optional[str]:
        q = query.lower()
        if "jain" in q: return "jain"
        if "vegan" in q: return "vegan"
        if "halal" in q: return "halal"
        if "hindu" in q: return "hindu"
        if "vegetarian" in q: return "vegetarian"
        return None # No default assumption

    @staticmethod
    def _extract_ingredients(query: str) -> List[str]:
        # Simple heuristic: Look for "Ingredients" keyword or just comma-separated list
        # If user says "Ingredients: A, B, C"
        if "ingredients" in query.lower():
            try:
                part = query.lower().split("ingredients")[-1]
                # Clean up colon
                if part.strip().startswith(":"):
                    part = part.strip()[1:]
                return [x.strip() for x in part.split(",") if x.strip()]
            except:
                pass
        
        # Fallback: if user just pastes a list "Water, Sugar, E471"
        if "," in query:
             return [x.strip() for x in query.split(",") if x.strip()]
        
        return []

    @staticmethod
    def analyze(query: str) -> Generator[str, None, None]:
        from ingredient_ontology import evaluate_fast_path
        
        profile = SafetyAnalyst._extract_profile(query)
        ingredients = SafetyAnalyst._extract_ingredients(query)
        
        # --- FAST PATH CHECK ---
        if ingredients:
            # If profile unknown, check "general" (mostly additives)
            check_profile = profile if profile else "general" 
            result = evaluate_fast_path(ingredients, check_profile)
            
            # 1. Deterministic SUCCESS (SAFE)
            if result.verdict == "SAFE":
                if profile:
                    yield f"Yes — this is {profile.title()} safe. 🌱\n\n"
                    yield "All ingredients are compatible.\n"
                else:
                    yield "This looks like a standard product with no common additives. ✅\n\n"
                    yield "However, I noticed you didn't specify a diet. Are you avoiding anything due to allergies or religious reasons (like Jain or Halal)?"
                return

            # 2. Deterministic FAIL (NOT SUITABLE)
            if result.verdict == "NOT SUITABLE":
                if profile:
                    yield f"No — this is not {profile.title()}. 🛑\n\n"
                    yield f"It contains: {', '.join([x.title() for x in result.logic])}.\n"
                else:
                    # Rare for general profile to hit NOT SUITABLE unless we define poisons, 
                    # but if we do:
                    yield f"This contains {', '.join([x.title() for x in result.logic])}. ⚠️\n"
                return

            # 3. HANDOFF (Ambiguous/Unknown) -> SLOW PATH (LLM formatting)
            logic_context = "; ".join(result.logic)
            enhanced_prompt = SafetyAnalyst.SYSTEM_PROMPT.format(profile=str(profile), query=query) + \
                              f"\n\n[SYSTEM INJECTION]: The Rule Engine detected ambiguity: {logic_context}. " \
                              "Explain this humanly. If profile is unknown, ask user."

        else:
            # Fallback for complex natural language queries (no clear list)
            enhanced_prompt = SafetyAnalyst.SYSTEM_PROMPT.format(profile=str(profile), query=query)

        # --- SLOW PATH (LLM) ---
        payload = {
            "model": MODEL_NAME,
            "prompt": enhanced_prompt,
            "stream": True
        }
        
        try:
            with requests.post(OLLAMA_API_URL, json=payload, stream=True, timeout=300) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        try:
                            json_response = json.loads(line)
                            if "response" in json_response:
                                yield json_response["response"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Safety Analysis failed: {e}")
            yield f"Error conducting safety analysis: {str(e)}"
