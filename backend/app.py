from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import logging
from dotenv import load_dotenv
from pathlib import Path

# Load env vars
env_path = Path(__file__).parent.parent / "frontend" / ".env.local"
load_dotenv(env_path)
# Backend .env for USE_NEW_ENGINE / SHADOW_MODE
load_dotenv(Path(__file__).parent / ".env")

# Initialize App
app = FastAPI(title="IngreSure Visual Scanner API")

try:
    from core.config import log_config
    log_config()
except ImportError:
    def log_config(): pass

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def _warmup_ollama():
    """Pre-load the Ollama model so the first user request is fast."""
    import threading

    def _ping():
        try:
            from core.config import get_ollama_url, get_ollama_model
            import requests as _req
            _req.post(
                get_ollama_url(),
                json={"model": get_ollama_model(), "prompt": "hi", "stream": False,
                      "options": {"num_predict": 1}},
                timeout=60,
            )
            logger.info("WARMUP Ollama model loaded successfully")
        except Exception as exc:
            logger.warning("WARMUP Ollama ping failed (non-fatal): %s", exc)

    threading.Thread(target=_ping, daemon=True).start()


# --- Models ---
class ScanResult(BaseModel):
    raw_text: str
    ingredients: List[str]
    dietary_scorecard: Dict[str, Dict] # { "Vegan": { "status": "red", "reason": "..." } }
    confidence_scores: Dict[str, float]

class VerificationRequest(BaseModel):
    item_name: str
    description: str
    ingredients: List[str]
    claimed_diet_types: List[str]

class ChatRequest(BaseModel):
    query: str
    user_id: Optional[str] = None  # when set, profile is loaded from backend and used for restriction_ids
    context_filter: Optional[Dict] = None
    userProfile: Optional[Dict] = None  # legacy: used when user_id not set

class MenuOnboardRequest(BaseModel):
    restaurant_id: str
    menu_items: List[Dict]

# Import Engines
from ocr_engine import OCREngine
from llm_normalizer import IngredientNormalizer
from verification_service import verify_menu_item
from rag_service import RAGService
from onboarding_service import OnboardingService

ocr_engine = OCREngine()
normalizer = IngredientNormalizer()
rag_service = RAGService()
onboarding_service = OnboardingService(rag_service)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "IngreSure AI Scanner"}

@app.post("/onboard-menu")
async def onboard_menu(request: MenuOnboardRequest):
    logger.info(f"Onboarding menu for restaurant: {request.restaurant_id}")
    try:
        result = onboarding_service.process_menu(request.restaurant_id, request.menu_items)
        return result
    except Exception as e:
        logger.error(f"Onboarding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scan", response_model=ScanResult)
async def scan_image(file: UploadFile = File(...)):
    """OCR -> normalize ingredients -> compliance engine -> scorecard."""
    logger.info("Scan request filename=%s", file.filename)
    try:
        image_bytes = await file.read()
        raw_text = ocr_engine.extract_text(image_bytes)
        logger.info("OCR extracted %d chars", len(raw_text))
        ingredients = normalizer.normalize(raw_text)
        logger.info("Normalized %d ingredients", len(ingredients))
        from core.bridge import run_new_engine_scan, run_legacy_chat, SCAN_DIET_LABELS, DIET_LABEL_TO_RESTRICTION_ID
        from core.config import SHADOW_MODE
        verdict, scorecard = run_new_engine_scan(ingredients)
        if SHADOW_MODE:
            for label in SCAN_DIET_LABELS:
                rid = DIET_LABEL_TO_RESTRICTION_ID.get(label)
                legacy_profile = {"diet": label.lower().replace(" ", "_")} if rid else None
                if legacy_profile and rid == "hindu_vegetarian":
                    legacy_profile["diet"] = "hindu_veg"
                legacy_status = run_legacy_chat(ingredients, legacy_profile)
                new_status = "NOT_SAFE" if rid and rid in verdict.triggered_restrictions else "SAFE"
                if legacy_status != new_status:
                    logger.warning(
                        "SHADOW_SCAN diff diet=%s legacy_status=%s new_status=%s",
                        label, legacy_status, new_status,
                    )
                logger.info(
                    "SHADOW_SCAN diet=%s legacy_status=%s new_status=%s",
                    label, legacy_status, new_status,
                )
        logger.info("Scan status=%s confidence=%s triggered=%s uncertain_count=%s",
                    verdict.status.value, verdict.confidence_score,
                    verdict.triggered_restrictions, len(verdict.uncertain_ingredients))
        return {
            "raw_text": raw_text,
            "ingredients": ingredients,
            "dietary_scorecard": scorecard,
            "confidence_scores": {"overall": verdict.confidence_score}
        }
    except Exception as e:
        logger.error("Scan failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/verify-menu-item")
async def verify_item(request: VerificationRequest):
    """
    Verifies a menu item against its ingredients and claimed diet types.
    """
    logger.info(f"Verifying item: {request.item_name}")
    try:
        result = verify_menu_item(
            item_name=request.item_name,
            description=request.description,
            ingredients=request.ingredients,
            claimed_diet_types=request.claimed_diet_types
        )
        return result
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Import SafetyAnalyst
from safety_analyst import SafetyAnalyst

class UpdateProfileRequest(BaseModel):
    profile: Dict

class ProfileBody(BaseModel):
    user_id: str
    dietary_preference: Optional[str] = None
    allergens: Optional[List[str]] = None
    lifestyle: Optional[List[str]] = None

def _parse_update_command(query: str):
    """Parse /update <field> value1, value2. Returns (field, values) or (None, None). Supports dietary_preference (single), allergens, lifestyle."""
    q = query.strip()
    if not q.lower().startswith("/update"):
        return None, None
    import re
    m = re.match(r"/update\s+(\w+)\s+(.+)", q, re.IGNORECASE | re.DOTALL)
    if not m:
        return None, None
    field_name = m.group(1).lower()
    allowed = ("dietary_preference", "allergens", "lifestyle")
    if field_name not in allowed:
        return None, None
    raw = m.group(2).strip()
    values = [x.strip() for x in raw.split(",") if x.strip()]
    if field_name == "dietary_preference" and values:
        values = [values[0]]  # single value
    return field_name, values

@app.get("/profile/{user_id}")
async def get_profile(user_id: str):
    """Get persisted profile by user_id. Returns new shape; never None for existing fields."""
    try:
        from core.profile_storage import get_profile as get_stored
        profile = get_stored(user_id)
        if profile is None:
            return {
                "user_id": user_id,
                "dietary_preference": "No rules",
                "allergens": [],
                "lifestyle": [],
                "religious_preferences": [],  # backward compat with frontend
            }
        return profile.to_dict()
    except Exception as e:
        logger.error(f"Get profile failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/profile")
async def create_or_update_profile(body: ProfileBody):
    """Create or update profile by user_id. Merge: only provided fields are updated; never reset to None."""
    try:
        from core.profile_storage import get_or_create_profile, save_profile, update_profile_partial
        from core.models.user_profile import UserProfile
        # Partial update: only set fields that are explicitly provided
        profile = update_profile_partial(
            body.user_id,
            dietary_preference=body.dietary_preference,
            allergens=body.allergens,
            lifestyle=body.lifestyle,
        )
        if profile is None:
            profile = get_or_create_profile(body.user_id)
            save_profile(profile)
        logger.info("PROFILE_UPDATE user_id=%s dietary_preference=%s", body.user_id, profile.dietary_preference)
        return {"status": "ok", "profile": profile.to_dict()}
    except Exception as e:
        logger.error(f"Profile save failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-profile")
async def update_profile(request: UpdateProfileRequest):
    """
    Legacy: frontend profile sync. Prefer POST /profile with user_id for persistent storage.
    """
    try:
        logger.info(f"Frontend Profile Sync: {request.profile}")
        return {"status": "ok", "message": "Profile synced (Stateless)"}
    except Exception as e:
        logger.error(f"Profile sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/grocery")
async def chat_grocery(request: ChatRequest):
    """
    Conversational Grocery Safety Assistant.

    Architecture (5 layers):
      1. Intent Detector   – rule-based NLU first, LLM fallback for ambiguous queries
      2. Profile Service   – persistent, merge-only updates; never reset on chat
      3. Ingredient Parser  – extract ingredients from natural language or label text
      4. Compliance Engine  – deterministic evaluation against ontology + restrictions (NEVER LLM)
      5. Response Composer  – LLM-powered natural responses, template fallback if LLM unavailable

    Supports both:
      - user_id path   (profile from backend storage)
      - legacy path    (profile from request body)
    """
    logger.info("Grocery Chat query=%s user_id=%s", request.query, request.user_id)
    try:
        from core.profile_storage import get_or_create_profile, save_profile
        from core.models.user_profile import UserProfile
        from core.bridge import user_profile_model_to_restriction_ids, run_new_engine_chat, run_legacy_chat
        from core.config import SHADOW_MODE
        from core.models.verdict import VerdictStatus
        from core.intent_detector import detect_intent, ParsedIntent, DIET_KEYWORDS
        from core.response_composer import (
            compose_greeting as template_greeting,
            compose_profile_update as template_profile_update,
            compose_verdict as template_verdict,
            compose_general_question as template_general,
            compose_no_ingredients as template_no_ingredients,
        )
        from core.llm_intent import llm_extract_intent
        from core.llm_response import (
            llm_compose_verdict,
            llm_compose_greeting,
            llm_compose_profile_update,
            llm_compose_general,
        )
        import json
        import re as _re

        def _profile_json(profile):
            return f"\n\n<<<PROFILE_UPDATE>>>{json.dumps(profile.to_dict())}<<<PROFILE_UPDATE>>>"

        # Known restricted ingredient keywords — when found inside a multi-word
        # product name, these are extracted for compliance evaluation.
        _RESTRICTED_KEYWORDS_BIGRAM = {
            "sweet potato", "fish oil", "palm oil",
        }
        _RESTRICTED_KEYWORDS_SINGLE = {
            # Animal-derived
            "egg", "eggs", "chicken", "beef", "pork", "lamb", "fish",
            "tuna", "salmon", "shrimp", "prawn", "crab", "lobster",
            "bacon", "ham", "turkey", "duck", "veal", "mutton",
            "anchovy", "sardine", "squid", "octopus", "venison", "goat",
            # Dairy
            "milk", "cheese", "butter", "cream", "yogurt", "ghee",
            "paneer", "whey", "curd",
            # Root vegetables (Jain)
            "garlic", "onion", "potato", "carrot", "ginger",
            "beet", "beetroot", "radish", "turnip", "shallot", "leek", "yam",
            # Fungal (Jain)
            "mushroom", "truffle",
            # Other
            "gelatin", "honey", "lard", "alcohol", "wine", "beer",
            "peanut", "almond", "walnut", "cashew", "hazelnut", "pecan",
            "soy", "tofu", "wheat", "barley", "rye", "oat", "oats",
            "collagen", "rennet", "shellac", "carmine",
        }
        # Plant modifiers that neutralize the following dairy/meat word
        # e.g. "coconut milk" is plant-based, NOT dairy
        _PLANT_MODIFIERS = {
            "coconut", "almond", "soy", "oat", "oats", "rice", "cashew",
            "hemp", "pea", "cocoa", "shea", "sesame", "flax", "hazelnut",
            "peanut", "walnut", "pistachio", "macadamia", "pecan",
        }

        def _find_sub_ingredients(name: str) -> list:
            """Extract known restricted-ingredient keywords from a compound name.

            'garlic pasta'   → ['garlic']
            'egg noodles'    → ['egg']
            'coconut milk'   → []   (plant modifier neutralizes 'milk')
            'butter chicken' → ['butter', 'chicken']
            """
            words = name.lower().split()
            if len(words) <= 1:
                return []
            found = []
            i = 0
            while i < len(words):
                # Bigram check first: "sweet potato", "fish oil"
                if i + 1 < len(words):
                    bigram = f"{words[i]} {words[i + 1]}"
                    if bigram in _RESTRICTED_KEYWORDS_BIGRAM:
                        found.append(bigram)
                        i += 2
                        continue
                # Skip if preceded by a plant modifier (coconut milk → skip milk)
                if words[i] in _RESTRICTED_KEYWORDS_SINGLE:
                    if i > 0 and words[i - 1] in _PLANT_MODIFIERS:
                        i += 1
                        continue
                    found.append(words[i])
                i += 1
            return found

        def _expand_compounds(ingredients):
            """Expand compound items for compliance evaluation.

            Handles both explicit ('burger with chicken') and implicit
            ('garlic pasta', 'egg noodles') compound product names.

            Returns:
                expanded (list[str]):  ingredient names for the compliance engine
                display_map (dict):    {eval_name_lower: original_compound_display_name}
            """
            expanded = []
            display_map = {}
            seen = set()
            for ing in ingredients:
                # 1. Explicit "X with Y" pattern
                m = _re.match(r"^(.+?)\s+with\s+(.+)$", ing, _re.IGNORECASE)
                if m:
                    sub = m.group(2).strip()
                    key = sub.lower()
                    if key not in seen:
                        seen.add(key)
                        expanded.append(sub)
                        display_map[key] = ing
                    continue

                # 2. Single-word ingredient → pass through directly
                if " " not in ing.strip():
                    key = ing.lower().strip()
                    if key not in seen:
                        seen.add(key)
                        expanded.append(ing)
                    continue

                # 3. Multi-word: extract known ingredient keywords
                subs = _find_sub_ingredients(ing)
                if subs:
                    # Check if ALL words are ingredient keywords (e.g. "butter chicken")
                    # vs. a product with ingredient modifiers (e.g. "garlic pasta")
                    covered = set()
                    for s in subs:
                        covered.update(s.split())
                    all_words = set(ing.lower().split())
                    is_compound_product = bool(all_words - covered)

                    for sub in subs:
                        key = sub.lower()
                        if key not in seen:
                            seen.add(key)
                            expanded.append(sub)
                            if is_compound_product:
                                display_map[key] = ing
                else:
                    # No known keywords found — pass through as-is
                    key = ing.lower().strip()
                    if key not in seen:
                        seen.add(key)
                        expanded.append(ing)
            return expanded, display_map

        def _apply_profile_updates(profile, updates: dict) -> dict:
            """Apply parsed profile updates to the profile model. Returns updated_fields dict."""
            updated_fields = {}
            if "dietary_preference" in updates:
                profile.update_merge(dietary_preference=updates["dietary_preference"])
                updated_fields["dietary_preference"] = updates["dietary_preference"]
            if "allergens" in updates:
                existing = list(profile.allergens or [])
                for a in updates["allergens"]:
                    if a.lower() not in [e.lower() for e in existing]:
                        existing.append(a)
                profile.update_merge(allergens=existing)
                updated_fields["allergens"] = updates["allergens"]
            if "remove_allergens" in updates:
                existing = list(profile.allergens or [])
                to_remove = {a.lower() for a in updates["remove_allergens"]}
                existing = [a for a in existing if a.lower() not in to_remove]
                profile.update_merge(allergens=existing)
                updated_fields["remove_allergens"] = updates["remove_allergens"]
            if "lifestyle" in updates:
                existing_ls = list(profile.lifestyle or [])
                for lf in updates["lifestyle"]:
                    if lf.lower() not in [e.lower() for e in existing_ls]:
                        existing_ls.append(lf)
                profile.update_merge(lifestyle=existing_ls)
                updated_fields["lifestyle"] = updates["lifestyle"]
            return updated_fields

        async def generate_safety():
            # ----------------------------------------------------------------
            # Path A: user_id present → use persistent profile + smart intent
            # ----------------------------------------------------------------
            if request.user_id:
                profile = get_or_create_profile(request.user_id)

                # 1) /update command (existing slash-command syntax)
                field_name, values = _parse_update_command(request.query)
                if field_name and values is not None:
                    if field_name == "dietary_preference":
                        profile.update_merge(dietary_preference=values[0] if values else "No rules")
                    elif field_name == "allergens":
                        profile.update_merge(allergens=values)
                    elif field_name == "lifestyle":
                        profile.update_merge(lifestyle=values)
                    save_profile(profile)
                    logger.info("PROFILE_UPDATE user_id=%s field=%s values=%s", request.user_id, field_name, values)
                    updated_fields = {field_name: values}
                    yield template_profile_update(profile, updated_fields, has_ingredients=False)
                    yield _profile_json(profile)
                    return

                # 2) Intent detection: rule-based FIRST, LLM FALLBACK
                parsed = detect_intent(request.query)
                logger.info(
                    "INTENT_DETECT_RULES intent=%s profile_updates=%s ingredients=%s query=%s",
                    parsed.intent, parsed.profile_updates, parsed.ingredients, request.query,
                )

                # If rules returned GENERAL_QUESTION with no ingredients,
                # the query might be ambiguous — try LLM fallback
                llm_used = False
                if parsed.intent == "GENERAL_QUESTION" and not parsed.has_ingredients and not parsed.has_profile_update:
                    llm_data = llm_extract_intent(request.query)
                    if llm_data:
                        logger.info(
                            "INTENT_DETECT_LLM_FALLBACK intent=%s diet=%s ingredients=%s query=%s",
                            llm_data["intent"], llm_data.get("dietary_preference"), llm_data["ingredients"], request.query,
                        )
                        llm_used = True
                        # Convert LLM result into ParsedIntent-compatible data
                        llm_profile_updates = {}
                        if llm_data.get("dietary_preference"):
                            llm_profile_updates["dietary_preference"] = llm_data["dietary_preference"]
                        if llm_data.get("allergens"):
                            llm_profile_updates["allergens"] = llm_data["allergens"]
                        if llm_data.get("lifestyle"):
                            llm_profile_updates["lifestyle"] = llm_data["lifestyle"]
                        if llm_data.get("remove_allergens"):
                            llm_profile_updates["remove_allergens"] = llm_data["remove_allergens"]

                        parsed = ParsedIntent(
                            intent=llm_data["intent"],
                            profile_updates=llm_profile_updates,
                            ingredients=llm_data["ingredients"],
                            original_query=request.query,
                        )

                # 3) Handle GREETING
                if parsed.intent == "GREETING":
                    msg = llm_compose_greeting(profile)
                    yield msg or template_greeting()
                    yield _profile_json(profile)
                    return

                # 4) Apply profile updates from natural language
                profile_was_updated = False
                updated_fields = {}
                if parsed.has_profile_update:
                    updated_fields = _apply_profile_updates(profile, parsed.profile_updates)
                    if updated_fields:
                        save_profile(profile)
                        profile_was_updated = True
                        logger.info(
                            "PROFILE_UPDATE_NL user_id=%s updated_fields=%s new_dietary=%s",
                            request.user_id, list(updated_fields.keys()), profile.dietary_preference,
                        )

                # 5) If PROFILE_UPDATE only (no ingredients), respond and return
                if parsed.intent == "PROFILE_UPDATE" and not parsed.has_ingredients:
                    yield template_profile_update(profile, updated_fields, has_ingredients=False)
                    yield _profile_json(profile)
                    return

                # 6) If GENERAL_QUESTION and no ingredients, handle via LLM
                if parsed.intent == "GENERAL_QUESTION" and not parsed.has_ingredients:
                    if profile.is_empty():
                        yield "<<<PROFILE_REQUIRED>>>\n\n"
                    msg = llm_compose_general(request.query, profile)
                    yield msg or template_general()
                    yield _profile_json(profile)
                    return

                # 7) Extract ingredients
                ingredients = parsed.ingredients

                # First-time user with empty profile and no ingredients
                if profile.is_empty() and not ingredients:
                    yield "<<<PROFILE_REQUIRED>>>\n\n"
                    msg = llm_compose_general(request.query, profile)
                    yield msg or "Please set up your dietary profile first so I can give you personalized advice."
                    yield _profile_json(profile)
                    return

                # No ingredients found but profile exists
                if not ingredients:
                    msg = llm_compose_general(request.query, profile)
                    yield msg or template_no_ingredients()
                    yield _profile_json(profile)
                    return

                # 8) Expand compound items for compliance evaluation
                eval_ingredients, compound_map = _expand_compounds(ingredients)

                # 9) Run DETERMINISTIC compliance engine (NEVER LLM)
                restriction_ids = user_profile_model_to_restriction_ids(profile)
                profile_context = {
                    "dietary_preference": profile.dietary_preference,
                    "allergens": profile.allergens,
                    "lifestyle": profile.lifestyle,
                }
                logger.info(
                    "COMPLIANCE_RUN ingredients=%s eval_ingredients=%s compounds=%s restriction_ids=%s",
                    ingredients, eval_ingredients, compound_map, restriction_ids,
                )
                verdict = run_new_engine_chat(
                    eval_ingredients,
                    user_profile=profile,
                    restriction_ids=restriction_ids,
                    profile_context=profile_context,
                    use_api_fallback=True,
                )

                # 10) Shadow mode comparison
                if SHADOW_MODE:
                    legacy_status = run_legacy_chat(eval_ingredients, profile.to_dict())
                    logger.info(
                        "SHADOW_CHAT legacy_status=%s new_status=%s user_id=%s confidence=%.2f triggered=%s uncertain_count=%s",
                        legacy_status, verdict.status.value, request.user_id,
                        verdict.confidence_score, verdict.triggered_restrictions, len(verdict.uncertain_ingredients),
                    )
                    if legacy_status != verdict.status.value:
                        logger.warning(
                            "SHADOW_CHAT diff legacy_status=%s new_status=%s ingredients=%s",
                            legacy_status, verdict.status.value, eval_ingredients[:15],
                        )
                else:
                    logger.info(
                        "INGRESURE_ENGINE: USER_PROFILE user_id=%s dietary=%s allergens=%s lifestyle=%s | "
                        "VERDICT=%s confidence=%.2f triggered=%s ingredients=%s",
                        request.user_id, profile.dietary_preference, profile.allergens,
                        profile.lifestyle,
                        verdict.status.value, verdict.confidence_score,
                        verdict.triggered_restrictions, ingredients,
                    )

                # 11) Compose response: template-first (instant, accurate, no filler)
                # LLM is reserved for greetings/general questions only
                response_text = template_verdict(
                    verdict=verdict,
                    profile=profile,
                    ingredients=eval_ingredients,
                    profile_was_updated=profile_was_updated,
                    updated_fields=updated_fields if profile_was_updated else None,
                    display_names=compound_map if compound_map else None,
                )
                yield response_text
                yield _profile_json(profile)
                return

            # ----------------------------------------------------------------
            # Path B: no user_id → legacy SafetyAnalyst path
            # ----------------------------------------------------------------
            for token in SafetyAnalyst.analyze(request.query, request.userProfile):
                yield token

        return StreamingResponse(generate_safety(), media_type="text/plain")
    except Exception as e:
        logger.error(f"Grocery Chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/restaurant")
async def chat_restaurant(request: ChatRequest):
    """
    Endpoint 2: Restaurant Menu Assistant (RAGService).
    For finding food in onboarded menus.
    """
    logger.info(f"Restaurant Chat query: {request.query}")
    try:
        # 1. Retrieve Context
        context_items = rag_service.retrieve(request.query)
        
        # 2. Generate Answer (Stream)
        async def generate_rag():
            for token in rag_service.generate_answer_stream(request.query, context_items):
                yield token

        return StreamingResponse(generate_rag(), media_type="text/plain")

    except Exception as e:
        logger.error(f"Restaurant Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
