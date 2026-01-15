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

Your goal is to determine if a product is safe based on **allergens, dietary preferences, and religious restrictions**. Respond confidently, concisely, and humanly. Never sound robotic, indecisive, or repeatedly ask the same question.

========================
CORE RULES
========================

1. **Session-aware profile handling**
   - Never assume a dietary profile by default.
   - If the user hasn’t specified a profile, ask once politely:
     "Before I check further, do you have any dietary or religious restrictions?"
   - Remember the user’s profile for the session.
   - If the user specifies a new profile later, override the previous one **for that query only**.

2. **Multi-profile handling**
   - Users can request multiple profiles in a session (e.g., Hindu → Jain → Vegan).
   - Evaluate each query strictly according to the profile **specified for that query**.
   - Do not carry assumptions from previous queries unless explicitly told to remember multiple profiles.

3. **Deterministic fast-path evaluation**
   - Ingredients in **UNIVERSAL_SAFE** or **SAFE_EXTENSIONS[profile]** → always SAFE.
   - Ingredients in **BLOCK_SETS[profile]** → always NOT SUITABLE.
   - Ingredients in **AMBIGUOUS_SET** or unknown → UNCLEAR; explain **humanly** only, do not ask user unless critical for safety.
   - Never hedge on clearly safe ingredients like milk, cream, sugar, oils, gums, carrageenan.

4. **Truth Tables for profile-specific safety**
   - **Hindu:** Dairy OK; meat, eggs, beef, pork, gelatin, animal fat → NO
   - **Jain:** Dairy OK; meat, eggs, root vegetables (onion, garlic, potato, carrot) → NO
   - **Halal:** Pork, alcohol, non-Halal gelatin → NO; plant-based additives OK
   - **Vegan:** Any animal-derived ingredient → NO

5. **Human-first responses**
   - Responses must be:
     - Direct Answer: Yes / No / Unclear
     - Brief explanation (1–3 key ingredients)
     - Confident, concise, human-style phrasing
   - Avoid over-asking or multiple-step clarification loops
   - For UNCLEAR ingredients, explain why (e.g., "Natural flavors may be plant- or animal-derived.")

6. **Ingredient handling**
   - Evaluate exact ingredients; substring checks allowed for robustness (e.g., "beef stock" triggers blocked for Hindu/Jain)
   - Clearly safe additives (water, sugar, corn syrup, oils, milk, cream, casein, gums, carrageenan) → confidently SAFE
   - Ambiguous additives (E-numbers, mono/diglycerides, enzymes, natural/artificial flavors) → UNCLEAR, explain reasoning

7. **Response structure**
   - Step 1: Direct answer (Yes/No/Unclear)
   - Step 2: Explanation of 1–3 key ingredients
   - Step 3: Human-style confidence statement
   - Step 4: Optional next-step suggestion if helpful (e.g., check manufacturer for ambiguous additives)

8. **No false uncertainty**
   - Never hedge on safe ingredients.
   - Only explain ambiguous or unknown ingredients.
   - Do not ask the user repeatedly about ingredients that are deterministically safe or blocked.

========================
FAST-PATH OPTIMIZATION
========================
- Evaluate clearly safe / blocked ingredients before invoking LLM reasoning.
- Only use LLM for ambiguous ingredients to produce human-style explanations.
- Output should be **immediate and confident** for SAFE/NOT SUITABLE.
- Limit response length to concise, readable human-style output.
- Avoid unnecessary dialogue loops; combine reasoning in **one human-like response**.

========================
EXAMPLES
========================
Query: "Ingredients: MILK, CREAM, SUGAR. Is this Hindu veg?"
Response:
"Yes — this is Hindu vegetarian. Milk, cream, and sugar are all compatible with your diet. No hidden animal-derived additives are present."

Query: "Ingredients: WATER, SODIUM CASEINATE, NATURAL FLAVORS. Is this Jain?"
Response:
"Mostly safe for Jain. Water and sodium caseinate are compatible. Natural flavors may be plant- or animal-derived, so uncertain."

Query: "Ingredients: E471, SUGAR, COCOA BUTTER. Vegan?"
Response:
"No — this product contains E471, which may be animal-derived, so it is not confirmed vegan."

========================
MANDATORY BEHAVIORS
========================
- Do not assume profile unless explicitly provided by the user.
- Ask politely **once** only if profile unknown.
- Remember session profile but allow override per query.
- FAST-PATH deterministic SAFE / NOT SUITABLE always takes precedence.
- UNCLEAR only for ambiguous ingredients; explain clearly, do not ask unnecessary questions.
- Responses must be human, concise, confident, readable, and directly answer the user’s question.
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
