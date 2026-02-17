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
    religious_preferences: Optional[List[str]] = None

def _parse_update_command(query: str):
    """Parse /update <field> value1, value2. Returns (field, values) or (None, None). Supports dietary_preference (single), allergens, lifestyle, religious_preferences."""
    q = query.strip()
    if not q.lower().startswith("/update"):
        return None, None
    import re
    m = re.match(r"/update\s+(\w+)\s+(.+)", q, re.IGNORECASE | re.DOTALL)
    if not m:
        return None, None
    field_name = m.group(1).lower()
    allowed = ("dietary_preference", "allergens", "religious_preferences", "lifestyle")
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
                "religious_preferences": [],
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
            religious_preferences=body.religious_preferences,
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
    Grocery / Food Item Scanner. If user_id is set, profile is loaded from backend and used for compliance.
    Supports /update <field> value1, value2 in chat to update profile.
    """
    logger.info("Grocery Chat query=%s user_id=%s", request.query, request.user_id)
    try:
        from core.profile_storage import get_or_create_profile, save_profile, update_profile_partial
        from core.models.user_profile import UserProfile
        from core.bridge import user_profile_model_to_restriction_ids, run_new_engine_chat, run_legacy_chat
        from core.config import SHADOW_MODE
        from core.models.verdict import VerdictStatus

        async def generate_safety():
            if request.user_id:
                profile = get_or_create_profile(request.user_id)
                field_name, values = _parse_update_command(request.query)
                if field_name and values is not None:
                    # Merge update: only the given field; never reset others to None
                    if field_name == "dietary_preference":
                        profile.update_merge(dietary_preference=values[0] if values else "No rules")
                    elif field_name == "allergens":
                        profile.update_merge(allergens=values)
                    elif field_name == "lifestyle":
                        profile.update_merge(lifestyle=values)
                    elif field_name == "religious_preferences":
                        profile.update_merge(religious_preferences=values)
                    save_profile(profile)
                    logger.info("PROFILE_UPDATE user_id=%s field=%s values=%s", request.user_id, field_name, values)
                    msg = (
                        f"Profile updated: {field_name}=[{', '.join(values)}]. "
                        f"Dietary: {profile.dietary_preference}, Allergens: {profile.allergens}, "
                        f"Religious: {profile.religious_preferences}, Lifestyle: {profile.lifestyle}."
                    )
                    yield msg + "\n\n"
                    import json
                    yield f"<<<PROFILE_UPDATE>>>{json.dumps(profile.to_dict())}<<<PROFILE_UPDATE>>>"
                    return
                ingredients = SafetyAnalyst._extract_ingredients(request.query)
                # First-time user: no profile and no ingredients → prompt for profile
                if profile.is_empty() and not ingredients:
                    yield "<<<PROFILE_REQUIRED>>>\n\nPlease set your dietary preference, allergens, and lifestyle (e.g. use the profile dialog or /update dietary_preference Jain)."
                    import json
                    yield f"\n\n<<<PROFILE_UPDATE>>>{json.dumps(profile.to_dict())}<<<PROFILE_UPDATE>>>"
                    return
                restriction_ids = user_profile_model_to_restriction_ids(profile)
                profile_context = {
                    "dietary_preference": profile.dietary_preference,
                    "allergens": profile.allergens,
                    "religious_preferences": profile.religious_preferences,
                    "lifestyle": profile.lifestyle,
                }
                verdict = run_new_engine_chat(
                    ingredients,
                    user_profile=profile,
                    restriction_ids=restriction_ids,
                    profile_context=profile_context,
                    use_api_fallback=True,
                )
                if SHADOW_MODE:
                    legacy_status = run_legacy_chat(ingredients, profile.to_dict())
                    logger.info(
                        "SHADOW_CHAT legacy_status=%s new_status=%s user_id=%s confidence=%.2f triggered=%s uncertain_count=%s",
                        legacy_status, verdict.status.value, request.user_id,
                        verdict.confidence_score, verdict.triggered_restrictions, len(verdict.uncertain_ingredients),
                    )
                    if legacy_status != verdict.status.value:
                        logger.warning(
                            "SHADOW_CHAT diff legacy_status=%s new_status=%s ingredients=%s",
                            legacy_status, verdict.status.value, ingredients[:15],
                        )
                else:
                    logger.info(
                        "INGRESURE_ENGINE: USER_PROFILE user_id=%s dietary_preference=%s allergens=%s religious=%s lifestyle=%s | "
                        "CHAT verdict=%s confidence=%.2f triggered=%s",
                        request.user_id, profile.dietary_preference, profile.allergens,
                        profile.religious_preferences, profile.lifestyle,
                        verdict.status.value, verdict.confidence_score, verdict.triggered_restrictions,
                    )
                profile_desc = f"Dietary: {profile.dietary_preference}; Allergens: {profile.allergens}; Religious: {profile.religious_preferences}; Lifestyle: {profile.lifestyle}"
                if verdict.status == VerdictStatus.NOT_SAFE:
                    yield f"❌ NOT SAFE — {', '.join(verdict.triggered_ingredients or verdict.triggered_restrictions)}.\n\n"
                    yield f"Evaluated for: **{profile_desc}**.\n"
                    if verdict.informational_ingredients and verdict.confidence_score < 1.0:
                        yield f"Minor ingredients (informational only): {', '.join(verdict.informational_ingredients)}.\n"
                    yield f"Confidence: {verdict.confidence_score:.2f}"
                elif verdict.status == VerdictStatus.UNCERTAIN:
                    yield f"⚠️ UNCLEAR — unknown or ambiguous: {', '.join(verdict.uncertain_ingredients)}.\n\n"
                    yield f"Evaluated for: **{profile_desc}**.\n"
                    if verdict.informational_ingredients and verdict.confidence_score < 1.0:
                        yield f"Minor ingredients (informational only): {', '.join(verdict.informational_ingredients)}.\n"
                    yield f"Confidence: {verdict.confidence_score:.2f}"
                elif verdict.status == VerdictStatus.SAFE and ingredients:
                    yield f"✅ SAFE — Compatible with your profile.\n\n"
                    if verdict.informational_ingredients and verdict.confidence_score < 1.0:
                        yield f"Minor ingredients (informational only): {', '.join(verdict.informational_ingredients)}.\n"
                    yield f"Confidence: {verdict.confidence_score:.2f}"
                else:
                    yield f"ℹ️ Please provide ingredients to analyze, or use /update to change your profile."
                import json
                yield f"\n\n<<<PROFILE_UPDATE>>>{json.dumps(profile.to_dict())}<<<PROFILE_UPDATE>>>"
                return
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
