import logging
import requests
import json
from typing import Generator, List, Dict

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
    System role: You are IngreSure SafetyAnalyst, a grocery safety assistant that behaves like a knowledgeable human store expert. 
    Your goal is to help users check if groceries are safe based on strict religious (Hindu, Jain, Halal) and dietary rules.
    
    **Interaction Style:**
    - **Human & Calm**: Be empathetic, knowledgeable, and concise. Never robotic.
    - **Direct Conclusion First**: Start with the verdict in 1 sentence.
    - **Short Explanation**: Follow with 1-3 bullet points max.
    - **Confidence**: Be clear about what you know and what is ambiguous.
    
    **Analysis Priorities:**
    1. Allergens (Nuts, Dairy, etc.)
    2. Religious Rules (Jain, Halal, Hindu)
    3. Hidden Additives (E-numbers, Flavors)
    
    **Output Template (Follow this style):**
    
    [Direct Conclusion, e.g., "This looks safe for a Jain diet."]
    
    [Short Explanation]
    - [Ingredient] is compatible because...
    
    [Confidence/Caveats if needed]
    "I'm 95% sure, but [Ingredient] source isn't specified."
    
    **Rules:**
    - If the user asks about a specific diet (e.g., Jain), be STRICT.
    - If no diet is specified, ask for clarification or assume Vegetarian but mention it.
    - Never guess. If source is unknown, say so.
    
    User Query: {query}
    
    Response:
    """

    @staticmethod
    def _extract_profile(query: str) -> str:
        q = query.lower()
        if "jain" in q: return "jain"
        if "vegan" in q: return "vegan"
        if "halal" in q: return "halal"
        return "hindu" # Default

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
            result = evaluate_fast_path(ingredients, profile)
            
            # 1. Deterministic SUCCESS (SAFE)
            if result.verdict == "SAFE":
                yield f"This looks completely safe for a {profile.title()} diet. 🌱\n\n"
                yield "All listed ingredients are compatible compatible with your expectations.\n"
                yield "Enjoy!"
                return

            # 2. Deterministic FAIL (NOT SUITABLE)
            if result.verdict == "NOT SUITABLE":
                yield f"I wouldn't recommend this for a {profile.title()} diet. 🛑\n\n"
                yield "It contains ingredients that are usually not suitable:\n"
                for issue in result.logic:
                    yield f"- {issue.title()}\n"
                return

            # 3. HANDOFF (Ambiguous/Unknown) -> SLOW PATH (LLM formatting)
            # We inject the "Logic" into the prompt so LLM doesn't need to guess.
            logic_context = "; ".join(result.logic)
            enhanced_prompt = SafetyAnalyst.SYSTEM_PROMPT.format(query=query) + \
                              f"\n\n[SYSTEM INJECTION]: The Rule Engine detected ambiguity: {logic_context}. " \
                              "Explain this humanly. Suggest checking with manufacturer."

        else:
            # Fallback for complex natural language queries (no clear list)
            enhanced_prompt = SafetyAnalyst.SYSTEM_PROMPT.format(query=query)

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
