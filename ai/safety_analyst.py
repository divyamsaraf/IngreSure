import logging
import requests
import json
import re
from typing import Generator, List, Optional, Set, Tuple
from ingredient_ontology import INGREDIENT_DB, UserProfile, evaluate_ingredient_risk, normalize_text

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

# --- GLOBAL SESSION STORE (Simulated) ---
# In a real app, this would be a DB keyed by user_id. 
# Here we use a global variable to persist state for the demo CLI.
CURRENT_USER_PROFILE = UserProfile(
    diet="general",
    dairy_allowed=True, # Default yes
    allergens=set()
)

class SafetyAnalyst:
    """
    Session-aware, NLP-driven Safety Analyst.
    """

    SYSTEM_PROMPT = """
You are IngreSure SafetyAnalyst, a knowledgeable human grocery expert.

TASK:
Analyze food safety based on a user's known profile and the provide ingredients.
If ingredients are unknown to the strict ontology, provide a cautious, human-friendly explanation.

CONTEXT:
User Profile: {profile_desc}
Ingredients to Analyze: {unknown_ingredients}

OUTPUT RULES:
1. Concise, human-first response.
2. Structure:
   - status: "⚠️ UNCLEAR" or "❌ NOT SAFE" (if likely unsafe).
   - reason: 1-2 sentences explaining why the ingredient is ambiguous or risky.
3. Do not hedge on known facts.
4. Confidence: Medium (since it's an LLM fallback).
"""

    @staticmethod
    def _parse_natural_language_profile(text: str) -> None:
        """
        Updates global CURRENT_USER_PROFILE based on natural language input.
        Handles negative assertions ("not allergic").
        """
        global CURRENT_USER_PROFILE
        text = text.lower()
        
        # 1. DIET EXTRACTION
        new_diet = CURRENT_USER_PROFILE.diet
        
        # Hindu
        if "hindu" in text:
            if "non-veg" in text or "non veg" in text: new_diet = "hindu_non_veg"
            elif "vegan" in text: new_diet = "vegan" # Override
            else: new_diet = "hindu_veg" # Default Hindu -> Veg
            
        # Jain
        elif "jain" in text:
            new_diet = "jain"
            
        # Vegan
        elif "vegan" in text:
            new_diet = "vegan"
            
        # Vegetarian
        elif "vegetarian" in text:
            new_diet = "vegetarian"
            
        # Halal
        elif "halal" in text:
            new_diet = "halal"
            
        # Kosher
        elif "kosher" in text:
            new_diet = "kosher"
            
        # Sikh
        elif "sikh" in text:
            new_diet = "sikh"

        # 2. DAIRY PREFERENCE
        # Capture "no dairy", "dairy free", "allergic to milk" -> False
        # Capture "dairy allowed", "eat dairy", "not allergic to milk" -> True
        
        new_dairy = CURRENT_USER_PROFILE.dairy_allowed
        
        # Negative assertions (Allowing dairy)
        if "not allergic to milk" in text or "can eat dairy" in text or "dairy allowed" in text:
            new_dairy = True
            # Also remove milk from allergens if present
            if "milk" in CURRENT_USER_PROFILE.allergens:
                CURRENT_USER_PROFILE.allergens.remove("milk")
                
        # Positive blocking assertions
        elif "no dairy" in text or "dairy free" in text or "allergic to milk" in text or "lactose intolerant" in text:
            new_dairy = False
            if "allergic to milk" in text:
                CURRENT_USER_PROFILE.allergens.add("milk")
        
        # 3. ALLERGIES
        # "allergic to X", "allergy: X"
        # Be careful with "not allergic to X"
        
        # Simple extraction of common allergens
        common_allergens = ["peanuts", "nuts", "soy", "wheat", "gluten", "fish", "shellfish", "eggs"]
        for alg in common_allergens:
            # Check for "not allergic to X"
            if f"not allergic to {alg}" in text:
                 if alg in CURRENT_USER_PROFILE.allergens:
                     CURRENT_USER_PROFILE.allergens.remove(alg)
            elif f"allergic to {alg}" in text or f"allergy to {alg}" in text:
                 CURRENT_USER_PROFILE.allergens.add(alg)
                 
        # Update Profile
        CURRENT_USER_PROFILE = UserProfile(
            diet=new_diet,
            dairy_allowed=new_dairy,
            allergens=CURRENT_USER_PROFILE.allergens
        )

    @staticmethod
    def _extract_ingredients(query: str) -> List[str]:
        # Robust extraction: look for "Ingredients:" prefix or assume comma list if no keywords
        # Also remove sentences like "Is this safe?"
        
        clean_q = query.lower()
        
        # Remove common chat phrases to isolate ingredients
        stopwords = ["is this safe", "is this", "can i eat", "contains", "ingredients:", "ingredients", "for me", "with"]
        
        # Strategy: If "Ingredients:" exists, take everything after it until a sentence end or new line
        if "ingredients:" in clean_q:
            parts = clean_q.split("ingredients:")
            candidate = parts[1]
            # Split by dot or newline to stop reading user questions
            candidate = candidate.split(".")[0].split("\n")[0]
            clean_q = candidate
        
        # Split by commas
        candidates = [x.strip() for x in clean_q.split(",") if x.strip()]
        
        # Filter out non-ingredient phrasing (heuristically)
        # e.g. "i am hindu" is not an ingredient
        final_list = []
        for c in candidates:
            # Remove profile declarations from ingredient list
            if any(k in c for k in ["hindu", "vegan", "allergy", "allergic", "safe", "diet"]):
                continue
            final_list.append(c)
            
        return final_list

    @staticmethod
    def analyze(query: str) -> Generator[str, None, None]:
        # 1. Update Profile from NLP
        SafetyAnalyst._parse_natural_language_profile(query)
        
        profile = CURRENT_USER_PROFILE
        ingredients = SafetyAnalyst._extract_ingredients(query)

        # 2. Analyze Ingredients
        unsafe_reasons = []
        unclear_items = []
        safe_items = []
        
        for ing in ingredients:
            result = evaluate_ingredient_risk(ing, profile)
            if result["status"] == "NOT_SAFE":
                unsafe_reasons.append(f"{ing.title()} ({result['reason']})")
            elif result["status"] == "UNCLEAR":
                unclear_items.append(ing)
            else:
                safe_items.append(f"{ing.title()} ({result['reason']})")
                
        # 3. Construct Response
        
        # Profile Summary string for context
        dairy_str = "Dairy Allowed" if profile.dairy_allowed else "No Dairy"
        profile_desc = f"{profile.diet.replace('_', ' ').title()} ({dairy_str})"
        if profile.allergens:
            profile_desc += f", Allergies: {', '.join(profile.allergens)}"

        # A. UNSAFE -> Immediate deterministic block
        if unsafe_reasons:
            yield f"❌ NOT SAFE — {', '.join(unsafe_reasons)}.\n\n"
            yield f"Evaluated for: **{profile_desc}**.\n"
            yield "Confidence: High"
            return
            
        # B. UNCLEAR -> LLM Handoff (Slow Path)
        if unclear_items:
            # Call LLM for explanation
            prompt = SafetyAnalyst.SYSTEM_PROMPT.format(
                profile_desc=profile_desc,
                unknown_ingredients=", ".join(unclear_items)
            )
            
            # Stream LLM
            yield f"⚠️ UNCLEAR — checking {', '.join(unclear_items)}...\n\n"
            
            payload = {"model": MODEL_NAME, "prompt": prompt, "stream": True}
            try:
                with requests.post(OLLAMA_API_URL, json=payload, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    for line in r.iter_lines():
                        if line:
                            j = json.loads(line)
                            if "response" in j: yield j["response"]
            except Exception as e:
                yield f"Error checking unknown ingredients: {e}"
            return

        # C. SAFE -> Immediate deterministic success
        if safe_items:
            # Human friendly summary
            top_reasons = safe_items[:3]
            yield f"✅ SAFE — Compatible with **{profile_desc}**.\n\n"
            yield f"Key ingredients: {', '.join(top_reasons)}.\n"
            yield "Confidence: High"
        else:
            # Fallback if no ingredients found
            yield f"ℹ️ Updated Profile: **{profile_desc}**.\n"
            yield "Please provide ingredients to analyze."
