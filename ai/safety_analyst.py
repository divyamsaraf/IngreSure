import logging
import requests
import json
from typing import Generator, List, Optional
from ingredient_ontology import evaluate_fast_path

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

# --- SESSION CONTEXT ---
session_profile: Optional[str] = None  # stores user profile for session

class SafetyAnalyst:
    """
    Human-first Grocery Safety Assistant.
    Features:
    - Session-aware profile handling
    - Deterministic fast-path evaluation
    - Concise human-style responses
    - Multi-profile support (Hindu, Jain, Vegan, Halal, Vegetarian, Kosher, Sikh)
    - Allergy, cultural, religious safety checks
    """

    SYSTEM_PROMPT = """
You are IngreSure SafetyAnalyst, a grocery safety assistant that behaves like a knowledgeable human grocery expert.

SYSTEM INSTRUCTIONS:

1. Profiles & Dietary Rules:
   - Handle all known dietary/religious/allergen profiles: Hindu (veg/non-veg, dairy/no dairy), Jain (veg/no root, dairy/no dairy), Vegan, Halal, Kosher, Sikh, Buddhist veg, and allergen-specific (nut, gluten, soy, lactose, egg, shellfish).
   - User can change profile any time; re-evaluate ingredients deterministically based on current profile.

2. Ingredient Classification:
   - All ingredients in the ontology are tagged by dietary compatibility, allergens, and ambiguity.
   - Milk-derived ingredients are safe for Hindu vegetarian if dairy is allowed; unsafe if dairy-free.
   - Oils, starches, sugars, gums, common sweeteners, beta carotene → always safe.
   - Meat, eggs, gelatin, beef → always unsafe unless explicitly allowed by profile (e.g., Hindu Non-Veg).
   - Root vegetables → unsafe for Jain.
   - Artificial/Natural flavors → safe unless labeled as animal-derived.

3. Decision Logic:
   - FAST PATH: SAFE ingredients → immediately YES with high confidence.
   - BLOCKED ingredients → immediately NO with high confidence.
   - AMBIGUOUS ingredients → only trigger cautious note, but do not over-hedge.
   - NEVER mix unrelated dietary rules unless multiple profiles are explicitly selected.

4. Response Style:
   - Provide a single, concise human-style paragraph.
   - Include 1–3 key ingredient examples.
   - Include a confidence statement: High / Medium / Low.
   - Avoid repeating profile questions if already known.

5. Edge Cases:
   - Profile changes mid-session → re-evaluate all ingredients deterministically.
   - All ingredients not in the ontology → ask user only for clarification if truly unknown.
"""

    @staticmethod
    def _extract_profile(query: str) -> Optional[str]:
        q = query.lower()
        # Look for complex phrases first
        
        # Hindu variants
        if "hindu" in q:
            if "non-veg" in q or "non veg" in q: return "hindu non-veg"
            if "vegan" in q: return "hindu vegan"
            if "no dairy" in q or "dairy free" in q: return "hindu (no dairy)"
            return "hindu" # Default veg

        # Jain variants
        if "jain" in q:
            if "vegan" in q: return "jain vegan"
            return "jain"
            
        # Standard profiles
        if "vegan" in q: return "vegan"
        if "halal" in q: return "halal"
        if "vegetarian" in q: return "vegetarian"
        if "kosher" in q: return "kosher"
        if "sikh" in q: return "sikh"
        
        return None

    @staticmethod
    def _get_current_profile(query: str) -> Optional[str]:
        global session_profile
        explicit_profile = SafetyAnalyst._extract_profile(query)
        if explicit_profile:
            session_profile = explicit_profile
            return explicit_profile
        return session_profile

    @staticmethod
    def _extract_ingredients(query: str) -> List[str]:
        if "ingredients" in query.lower():
            try:
                part = query.lower().split("ingredients")[-1]
                if part.strip().startswith(":"):
                    part = part.strip()[1:]
                return [x.strip() for x in part.split(",") if x.strip()]
            except:
                pass
        if "," in query:
            return [x.strip() for x in query.split(",") if x.strip()]
        return []

    @staticmethod
    def analyze(query: str) -> Generator[str, None, None]:
        profile = SafetyAnalyst._get_current_profile(query)
        ingredients = SafetyAnalyst._extract_ingredients(query)

        if ingredients:
            check_profile = profile if profile else "general"
            result = evaluate_fast_path(ingredients, check_profile)

            if result.verdict == "SAFE":
                if profile:
                    # Single confident paragraph
                    safe_list = result.logic[:3] # Top 3 ingredients
                    safe_str = ", ".join([i.lower() for i in safe_list])
                    yield f"✅ Yes — safe for a {profile.title()} diet.\n\n"
                    yield f"Ingredients like {safe_str} are compatible. "
                    yield "Confidence: High."
                else:
                    yield "✅ This product is generally safe. Please specify dietary profile for precise checks."
                return

            if result.verdict == "NOT_SUITABLE":
                if profile:
                    yield f"❌ No — not {profile.title()} safe.\n\n"
                    yield f"It contains {', '.join([x.lower() for x in result.logic])}. "
                    yield "Confidence: High."
                else:
                    yield f"⚠️ Contains potentially unsafe ingredients: {', '.join([x.lower() for x in result.logic])}."
                return

            if result.verdict == "HANDOFF":
                logic_context = ", ".join(result.logic)
                # Ensure we don't ask for profile if we already have it
                profile_context = f"User Profile: {profile}." if profile else "Profile Unknown."
                enhanced_prompt = SafetyAnalyst.SYSTEM_PROMPT + \
                                  f"\n{profile_context}\nUser Query: {query}\nAmbiguous ingredients: {logic_context}\nResponse:"
        else:
            enhanced_prompt = SafetyAnalyst.SYSTEM_PROMPT + f"\nUser Query: {query}\nResponse:"

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
