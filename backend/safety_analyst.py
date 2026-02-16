import logging
import requests
import json
import re
from typing import Generator, List, Optional, Set, Tuple, Dict
from ingredient_ontology import INGREDIENT_DB, UserProfile, evaluate_ingredient_risk, normalize_text

logger = logging.getLogger(__name__)

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"

class SafetyAnalyst:
    """
    Session-aware, NLP-driven Safety Analyst.
    Stateless Architecture.
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
    def _parse_natural_language_profile(text: str, current_profile: UserProfile) -> UserProfile:
        """
        Derives a NEW UserProfile based on natural language input + existing profile.
        Pure function: no side effects.
        """
        text = text.lower()
        
        # 1. DIET EXTRACTION
        new_diet = current_profile.diet
        
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
        new_dairy = current_profile.dairy_allowed
        new_allergens = set(current_profile.allergens)
        
        # Negative assertions (Allowing dairy)
        if "not allergic to milk" in text or "can eat dairy" in text or "dairy allowed" in text:
            new_dairy = True
            if "milk" in new_allergens:
                new_allergens.remove("milk")
                
        # Positive blocking assertions
        elif "no dairy" in text or "dairy free" in text or "allergic to milk" in text or "lactose intolerant" in text:
            new_dairy = False
            if "allergic to milk" in text:
                new_allergens.add("milk")
        
        # 3. ALLERGIES
        common_allergens = ["peanuts", "nuts", "soy", "wheat", "gluten", "fish", "shellfish", "eggs"]
        for alg in common_allergens:
            # Check for "not allergic to X"
            if f"not allergic to {alg}" in text:
                 if alg in new_allergens:
                     new_allergens.remove(alg)
            elif f"allergic to {alg}" in text or f"allergy to {alg}" in text:
                 new_allergens.add(alg)
                 
        # Return New Profile
        return UserProfile(
            diet=new_diet,
            dairy_allowed=new_dairy,
            allergens=new_allergens
        )

    @staticmethod
    def _normalize_ingredient_name(name: str) -> str:
        """
        Normalize ingredient names to handle cases like "meat (plant based)" 
        mapping them to canonical ontology keys.
        """
        n = name.lower().strip()
        
        # Plant-based meat normalization
        if "plant based" in n or "plant-based" in n:
             if "meat" in n or "beef" in n or "chicken" in n or "pork" in n or "sausage" in n or "burger" in n:
                 return "plant-based meat"
                 
        # Specific mappings
        if "soy meat" in n: return "soy meat"
        if "seitan" in n: return "seitan"
        
        # Singularization (Heuristic)
        if n.endswith("s") and not n.endswith("ss"):
             singular = n[:-1]
             return singular
             
        return n

    @staticmethod
    def _extract_ingredients(query: str) -> List[str]:
        # Clean query
        clean_q = query.lower()
        
        # Remove common chat phrases
        stopwords = ["is this safe", "is this", "can i eat", "contains", "ingredients:", "ingredients", "for me", "with", "safe", "is", "are", "?"]
        
        if "ingredients:" in clean_q:
            clean_q = clean_q.split("ingredients:")[1]

        clean_q = clean_q.split(".")[0]
        clean_q = clean_q.split("\n")[0]
            
        for sw in stopwords:
             clean_q = clean_q.replace(sw, " ") 
                  
        raw_list = [x.strip() for x in clean_q.split(",")]
        
        final_list = []
        for x in raw_list:
            if not x: continue
            if any(k in x for k in ["hindu", "vegan", "allergy", "allergic", "diet", "i am"]):
                 continue
                 
            norm = SafetyAnalyst._normalize_ingredient_name(x)
            final_list.append(norm)
            
        return final_list

    @staticmethod
    def create_profile_from_dict(data: Dict) -> UserProfile:
        """Helper to convert dict to UserProfile namedtuple"""
        algs = set(data.get("allergens", []) or data.get("allergies", []))
        d = data.get("diet", "general").lower().replace(" ", "_")
        if d == "no_specific_rules" or d == "none": d = "general"
        
        return UserProfile(
            diet=d,
            dairy_allowed=data.get("dairy_allowed", True),
            allergens=algs
        )

    @staticmethod
    def analyze(query: str, user_profile_dict: Optional[Dict] = None) -> Generator[str, None, None]:
        if user_profile_dict:
            current_profile = SafetyAnalyst.create_profile_from_dict(user_profile_dict)
        else:
            current_profile = UserProfile("general", True, set())
        updated_profile = SafetyAnalyst._parse_natural_language_profile(query, current_profile)
        profile = updated_profile
        ingredients = SafetyAnalyst._extract_ingredients(query)
        profile_dict = {
            "diet": profile.diet,
            "dairy_allowed": profile.dairy_allowed,
            "allergens": list(profile.allergens),
            "allergies": list(profile.allergens),
            "is_onboarding_completed": True,
        }
        dairy_str = "Dairy Allowed" if profile.dairy_allowed else "No Dairy"
        profile_desc = f"{profile.diet.replace('_', ' ').title()} ({dairy_str})"
        if profile.allergens:
            profile_desc += f", Allergies: {', '.join(profile.allergens)}"

        use_new = False
        shadow = False
        try:
            from core.config import USE_NEW_ENGINE, SHADOW_MODE
            use_new = USE_NEW_ENGINE
            shadow = SHADOW_MODE
        except ImportError:
            pass

        if use_new:
            from core.bridge import run_new_engine_chat
            from core.models.verdict import VerdictStatus
            verdict = run_new_engine_chat(ingredients, profile_dict)
            shadow_suffix = ""
            if shadow:
                unsafe_reasons_legacy = []
                unclear_legacy = []
                for ing in ingredients:
                    result = evaluate_ingredient_risk(ing, profile)
                    if result["status"] == "NOT_SAFE":
                        unsafe_reasons_legacy.append(ing)
                    elif result["status"] == "UNCLEAR":
                        unclear_legacy.append(ing)
                leg_status = "NOT_SAFE" if unsafe_reasons_legacy else ("UNCLEAR" if unclear_legacy else "SAFE")
                if leg_status != verdict.status.value:
                    shadow_suffix = f" | SHADOW_CHAT legacy_status={leg_status} new_status={verdict.status.value}"
                    logger.info("SHADOW_CHAT legacy_status=%s new_status=%s", leg_status, verdict.status.value)
            logger.info(
                "INGRESURE_ENGINE: use_new_engine=True shadow_mode=%s | CHAT verdict=%s confidence=%.2f triggered=%s unknown_ingredients=%s%s",
                shadow, verdict.status.value, verdict.confidence_score,
                verdict.triggered_restrictions, verdict.uncertain_ingredients, shadow_suffix,
            )
            if verdict.status == VerdictStatus.NOT_SAFE:
                yield f"❌ NOT SAFE — {', '.join(verdict.triggered_ingredients or verdict.triggered_restrictions)}.\n\n"
                yield f"Evaluated for: **{profile_desc}**.\n"
                yield f"Confidence: {verdict.confidence_score:.2f}"
            elif verdict.status == VerdictStatus.UNCERTAIN:
                yield f"⚠️ UNCLEAR — unknown or ambiguous: {', '.join(verdict.uncertain_ingredients)}.\n\n"
                yield f"Evaluated for: **{profile_desc}**.\n"
                yield f"Confidence: {verdict.confidence_score:.2f}"
            elif verdict.status == VerdictStatus.SAFE and ingredients:
                yield f"✅ SAFE — Compatible with **{profile_desc}**.\n\n"
                yield f"Confidence: {verdict.confidence_score:.2f}"
            else:
                yield f"ℹ️ Updated Profile: **{profile_desc}**.\n"
                yield "Please provide ingredients to analyze."
            try:
                yield f"\n\n<<<PROFILE_UPDATE>>>{json.dumps(profile_dict)}<<<PROFILE_UPDATE>>>"
            except Exception as e:
                logger.error("Failed to serialize profile: %s", e)
            return

        # Legacy path
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

        leg_verdict = "NOT_SAFE" if unsafe_reasons else ("UNCLEAR" if unclear_items else "SAFE")
        logger.info(
            "INGRESURE_ENGINE: use_new_engine=False shadow_mode=False | CHAT verdict=%s (legacy) ingredients_count=%s",
            leg_verdict, len(ingredients),
        )

        if unsafe_reasons:
            yield f"❌ NOT SAFE — {', '.join(unsafe_reasons)}.\n\n"
            yield f"Evaluated for: **{profile_desc}**.\n"
            yield "Confidence: High"
            
        elif unclear_items:
            # LLM Fallback (Slow Path)
            prompt = SafetyAnalyst.SYSTEM_PROMPT.format(
                profile_desc=profile_desc,
                unknown_ingredients=", ".join(unclear_items)
            )
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
        
        elif safe_items:
            # Safe Path
            top_reasons = safe_items[:3]
            yield f"✅ SAFE — Compatible with **{profile_desc}**.\n\n"
            yield f"Key ingredients: {', '.join(top_reasons)}.\n"
            yield "Confidence: High"
        else:
            # No ingredients found fallback (Just profile update info)
            yield f"ℹ️ Updated Profile: **{profile_desc}**.\n"
            yield "Please provide ingredients to analyze."
            
        # 6. Yield Profile Protocol Update
        # Always yield this so frontend stays in sync with NLP changes
        try:
            profile_dict = {
                "diet": profile.diet,
                "dairy_allowed": profile.dairy_allowed,
                "allergens": list(profile.allergens),
                "allergies": list(profile.allergens), # Frontend compatibility
                "is_onboarding_completed": True
            }
            yield f"\n\n<<<PROFILE_UPDATE>>>{json.dumps(profile_dict)}<<<PROFILE_UPDATE>>>"
        except Exception as e:
            logger.error(f"Failed to serialize profile: {e}")
