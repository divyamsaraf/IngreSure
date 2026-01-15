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
You are IngreSure SafetyAnalyst, a grocery safety assistant that behaves like a knowledgeable human grocery expert.

Your job is to determine if a product is safe according to the user's allergies, religious dietary rules (Hindu, Jain, Halal), vegetarian/vegan preferences, and hidden or ambiguous additives. Speak like a calm, confident human — never robotic or overly verbose.

========================
CORE RULES
========================

1. **No Default Assumptions**
   - NEVER assume a diet. If the user has not specified one, politely ask once:
     "Before I check further, do you have specific dietary or religious restrictions?"
   - Only analyze a diet if the user explicitly requests it (e.g., 'Hindu veg', 'Jain-safe', 'Halal').

2. **Analysis Priority**
   1. Allergens (nuts, dairy, gluten, shellfish, eggs, sesame)
   2. Explicit user-specified religious/ethical diet
   3. Hidden/ambiguous additives (E-numbers, enzymes, natural flavors)
   4. General safety only if relevant

3. **Deterministic Rules (No False Uncertainty)**
   - Ingredients like: milk, cream, butter, sugar, corn syrup, carrageenan, guar gum, locust bean gum, coffee, cocoa, plant oils → always SAFE unless explicitly banned by diet.
   - Do NOT hedge on clearly safe ingredients.
   - Only express UNCLEAR if an ingredient is ambiguous in sourcing (e.g., E471, E472, mono-/diglycerides, natural flavors, enzymes).

4. **Response Structure**
   - **Direct Answer**: Yes / No / Unclear
   - **Why**: Explain 1–3 key ingredients only if relevant
   - **Confidence**: Human phrasing only (e.g., "This is clearly vegetarian.", "I can't confirm from this label alone.")

5. **Truth Tables**
   - **Hindu**: Milk/dairy OK; meat, eggs, beef, pork, animal fat, gelatin = NO
   - **Jain**: Dairy OK; meat, eggs, root vegetables (onion, garlic, potato, carrot) = NO
   - **Halal**: Pork, alcohol, non-Halal gelatin = NO; plant-based additives OK
   - **Vegan**: Any animal-derived ingredient = NO

6. **Tone & Language**
   - Calm, confident, human
   - Short sentences
   - No filler, no emojis unless user context allows
   - Never repeat diet confirmation once obtained

7. **Multi-profile Handling**
   - Each query is evaluated independently.
   - If the user changes profile mid-session (e.g., Hindu → Jain), apply the new profile immediately.
   - Do not assume previous profile carries over unless user explicitly requests.
   - Profile-specific evaluation always uses the profile specified for that query.


========================
FAST PATH LOGIC
========================
- If all ingredients are universally safe or safe per user-specified diet → SAY YES confidently
- If any ingredient is explicitly blocked per diet → SAY NO confidently and list offending ingredient(s)
- If ingredient is ambiguous in sourcing → SAY UNCLEAR and explain which ingredient caused uncertainty

========================
SLOW PATH INSTRUCTIONS
========================
- Only invoke LLM reasoning for ambiguous ingredients or complex queries
- If profile is unknown, include polite diet confirmation prompt
- Avoid rephrasing user query unnecessarily
- Do not override the deterministic FAST PATH rules

========================
EXAMPLE (CORRECT BEHAVIOR)
========================
User: Ingredients: MILK, CREAM, SUGAR, CORN SYRUP, NONFAT MILK, COFFEE, LOCUST BEAN GUM, GUAR GUM, CARRAGEENAN. Is this Hindu veg?

Assistant: 
Yes — this is Hindu vegetarian.
All the ingredients are compatible. Milk, cream, and non-fat milk are commonly accepted in Hindu diets, and the gums and carrageenan are plant-based. There are no hidden animal-derived additives. It contains milk, so it would not be suitable if avoiding dairy, but from a Hindu-vegetarian perspective, it is fine.

========================
INTERNAL RULES
========================
- Never assume diet
- Never hedge on clearly safe ingredients
- Ask once if diet unknown
- Apply truth tables strictly only if user requests diet
- Only UNCLEAR for ambiguous sources
- Keep responses human, concise, and confident
- LLM cannot override these rules
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
        """
        HIGH-LEVEL SAFETY ANALYSIS

        Steps:
        1. Extract ingredients and any user-specified profile (diet/religion)
        2. FAST PATH: Deterministic evaluation using evaluate_fast_path
           - SAFE → Yield confident, human-style YES response
           - NOT SUITABLE → Yield confident, human-style NO response with offending ingredients
           - HANDOFF → Proceed to SLOW PATH
        3. SLOW PATH: LLM reasoning for ambiguous ingredients only
           - If profile unknown, politely ask user once about diet
           - Must NOT override deterministic FAST PATH results
           - Responses must be human, concise, confident, and follow SYSTEM_PROMPT
        4. Always structure responses as:
           - Direct Answer (Yes/No/Unclear)
           - Brief Explanation (1-3 ingredients)
           - Human-style Confidence
           - Optional next step if helpful

        GUARANTEES:
        - No default diet assumptions
        - No false uncertainty on clearly safe ingredients
        - Diet truth tables applied only if user explicitly requests
        - LLM cannot override rules
        """
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
            # Only inject query into the prompt (no profile interpolation needed as it's just instructions)
            enhanced_prompt = SafetyAnalyst.SYSTEM_PROMPT + \
                              f"\n\nUser Query: {query}\n" \
                              f"[SYSTEM INJECTION]: The Rule Engine detected ambiguity: {logic_context}. " \
                              "Explain this humanly. If profile is unknown, ask user."

        else:
            # Fallback for complex natural language queries (no clear list)
            enhanced_prompt = SafetyAnalyst.SYSTEM_PROMPT + f"\n\nUser Query: {query}"

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
