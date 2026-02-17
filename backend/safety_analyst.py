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
        
        # Careful singularization: only simple plural forms
        # Avoid mangling words like asparagus, couscous, citrus, hummus, lotus
        no_strip_suffixes = ("us", "ss", "is", "os", "as")
        if n.endswith("ies") and len(n) > 4:
            return n[:-3] + "y"  # berries → berry, cherries → cherry
        if n.endswith("es") and len(n) > 3 and not n.endswith(no_strip_suffixes):
            return n[:-2] if n[-3] in "sxzh" else n[:-1]  # dishes → dish, tomatoes → tomato
        if n.endswith("s") and len(n) > 3 and not n.endswith(no_strip_suffixes):
            return n[:-1]  # eggs → egg, carrots → carrot

        return n

    @staticmethod
    def _extract_ingredients(query: str) -> List[str]:
        """
        Extract ingredients from a query string.
        Delegates to the intent detector for robust conversational parsing,
        with fallback to simple comma-split for plain ingredient lists.
        """
        import re
        try:
            from core.intent_detector import detect_intent
            parsed = detect_intent(query)
            if parsed.ingredients:
                return [SafetyAnalyst._normalize_ingredient_name(i) for i in parsed.ingredients if i.strip()]
        except Exception:
            pass

        # Fallback: simple extraction for plain ingredient lists
        clean_q = query.lower()
        if "ingredients:" in clean_q:
            clean_q = clean_q.split("ingredients:")[1]

        clean_q = clean_q.split(".")[0]
        clean_q = clean_q.split("\n")[0]

        stopword_phrases = [
            r"is\s+this\s+safe",
            r"is\s+this",
            r"can\s+i\s+eat",
            r"contains",
            r"ingredients",
            r"for\s+me",
        ]
        stopword_words = [r"with", r"safe", r"are"]
        for phrase in stopword_phrases:
            clean_q = re.sub(phrase, " ", clean_q)
        for word in stopword_words:
            clean_q = re.sub(r"\b" + word + r"\b", " ", clean_q)

        clean_q = re.sub(r"[?:]+", " ", clean_q)
        clean_q = re.sub(r"\s+", " ", clean_q).strip()

        raw_list = [x.strip() for x in clean_q.split(",")]

        # Diet/profile keywords to filter OUT (only filter exact tokens, not substrings)
        _PROFILE_KEYWORDS = {"hindu", "vegan", "vegetarian", "halal", "kosher", "jain"}

        final_list = []
        for x in raw_list:
            if not x:
                continue
            # Only skip if the ENTIRE token is a profile keyword or profile phrase
            words = set(x.lower().split())
            if words <= (_PROFILE_KEYWORDS | {"i", "am", "a", "i'm", "im", "follow", "allergy", "allergic", "diet", "my", "is"}):
                continue
            # Remove leading profile words from mixed tokens like "i am jain eggs"
            cleaned = re.sub(
                r"^(?:i\s+am|i'm|im)\s+(?:a\s+)?(?:" + "|".join(_PROFILE_KEYWORDS) + r")\s*",
                "", x, flags=re.IGNORECASE,
            ).strip()
            if not cleaned:
                continue
            norm = SafetyAnalyst._normalize_ingredient_name(cleaned)
            if norm:
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
        """Legacy path (no user_id). Uses intent detector + NL profile parsing."""
        try:
            from core.intent_detector import detect_intent
            from core.response_composer import compose_verdict, compose_greeting, compose_general_question
            from core.bridge import run_new_engine_chat, profile_to_restriction_ids
            from core.models.verdict import VerdictStatus

            parsed = detect_intent(query)

            # Build base profile from dict or defaults
            if user_profile_dict:
                current_profile = SafetyAnalyst.create_profile_from_dict(user_profile_dict)
            else:
                current_profile = UserProfile("general", True, set())

            # Apply NL profile updates
            updated_profile = SafetyAnalyst._parse_natural_language_profile(query, current_profile)
            # Also apply intent-detected diet if present
            if parsed.has_profile_update and "dietary_preference" in parsed.profile_updates:
                diet_map = {
                    "Jain": "jain", "Vegan": "vegan", "Vegetarian": "vegetarian",
                    "Hindu Veg": "hindu_veg", "Halal": "halal", "Kosher": "kosher",
                    "Hindu Non Vegetarian": "hindu_non_veg",
                    "Lacto Vegetarian": "lacto_vegetarian", "Ovo Vegetarian": "ovo_vegetarian",
                    "Pescatarian": "pescatarian",
                }
                detected_diet = parsed.profile_updates["dietary_preference"]
                mapped = diet_map.get(detected_diet, detected_diet.lower().replace(" ", "_"))
                updated_profile = UserProfile(
                    diet=mapped,
                    dairy_allowed=updated_profile.dairy_allowed,
                    allergens=updated_profile.allergens,
                )
            profile = updated_profile

            # Use intent-detected ingredients (much more robust than old _extract_ingredients)
            ingredients = parsed.ingredients
            if not ingredients:
                ingredients = SafetyAnalyst._extract_ingredients(query)
            else:
                ingredients = [SafetyAnalyst._normalize_ingredient_name(i) for i in ingredients if i.strip()]

            profile_dict = {
                "diet": profile.diet,
                "dairy_allowed": profile.dairy_allowed,
                "allergens": list(profile.allergens),
                "allergies": list(profile.allergens),
                "is_onboarding_completed": True,
            }

            # Handle greeting
            if parsed.intent == "GREETING":
                yield compose_greeting()
                yield f"\n\n<<<PROFILE_UPDATE>>>{json.dumps(profile_dict)}<<<PROFILE_UPDATE>>>"
                return

            verdict = run_new_engine_chat(ingredients, profile_dict)
            logger.info(
                "INGRESURE_ENGINE: CHAT intent=%s verdict=%s confidence=%.2f triggered=%s ingredients=%s",
                parsed.intent, verdict.status.value, verdict.confidence_score,
                verdict.triggered_restrictions, ingredients,
            )

            # Use response composer for human-like output
            response_text = compose_verdict(
                verdict=verdict,
                profile={"dietary_preference": profile.diet.replace("_", " ").title()},
                ingredients=ingredients,
                profile_was_updated=parsed.has_profile_update,
                updated_fields=parsed.profile_updates if parsed.has_profile_update else None,
            )
            yield response_text
            yield f"\n\n<<<PROFILE_UPDATE>>>{json.dumps(profile_dict)}<<<PROFILE_UPDATE>>>"

        except Exception as e:
            logger.error("SafetyAnalyst.analyze failed: %s", e, exc_info=True)
            # Absolute fallback
            yield f"I encountered an error processing your request. Please try again or rephrase."
