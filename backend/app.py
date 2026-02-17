"""
IngreSure FastAPI application.

Endpoints:
    GET  /                  Health check
    POST /scan              OCR -> normalize -> compliance -> scorecard
    POST /chat/grocery      Conversational grocery safety assistant
    POST /chat/restaurant   Restaurant menu assistant (RAG)
    POST /onboard-menu      Process restaurant menu for RAG
    POST /verify-menu-item  Verify menu item against claimed diets
    GET  /profile/{user_id} Get user profile
    POST /profile           Create or update profile
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
import json
import re as _re
import uuid
from dotenv import load_dotenv
from pathlib import Path

# Load env vars
load_dotenv(Path(__file__).parent / ".env")

# Initialize App
app = FastAPI(title="IngreSure AI Scanner API")

try:
    from core.config import log_config
    log_config()
except ImportError:
    pass

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

# --- Eagerly import core modules (avoid repeated lazy imports) ---
from core.config import get_ollama_url, get_ollama_model
from core.profile_storage import get_or_create_profile, save_profile, update_profile_partial
from core.models.user_profile import UserProfile
from core.models.verdict import VerdictStatus
from core.bridge import (
    user_profile_model_to_restriction_ids,
    run_new_engine_chat,
    run_new_engine_scan,
    SCAN_DIET_LABELS,
    DIET_LABEL_TO_RESTRICTION_ID,
)
from core.intent_detector import detect_intent, ParsedIntent
from core.llm_intent import llm_extract_intent
from core.response_composer import (
    compose_greeting as template_greeting,
    compose_profile_update as template_profile_update,
    compose_verdict as template_verdict,
    compose_general_question as template_general,
    compose_no_ingredients as template_no_ingredients,
)
from core.llm_response import (
    llm_compose_greeting,
    llm_compose_profile_update,
    llm_compose_general,
)
from core.compound_expansion import expand_compounds

# Service imports (flat modules in backend/)
from ocr_engine import OCREngine
from llm_normalizer import IngredientNormalizer
from verification_service import verify_menu_item
from rag_service import RAGService
from onboarding_service import OnboardingService

ocr_engine = OCREngine()
normalizer = IngredientNormalizer()
rag_service = RAGService()
onboarding_service = OnboardingService(rag_service)


# --- Startup ---
@app.on_event("startup")
async def _warmup_ollama():
    """Pre-load the Ollama model so the first user request is fast."""
    import threading

    def _ping():
        try:
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


# --- Request/Response Models ---
class ScanResult(BaseModel):
    raw_text: str
    ingredients: List[str]
    dietary_scorecard: Dict[str, Dict]
    confidence_scores: Dict[str, float]


class VerificationRequest(BaseModel):
    item_name: str
    description: str
    ingredients: List[str]
    claimed_diet_types: List[str]


class ChatRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    context_filter: Optional[Dict] = None
    userProfile: Optional[Dict] = None


class MenuOnboardRequest(BaseModel):
    restaurant_id: str
    menu_items: List[Dict]


class ProfileBody(BaseModel):
    user_id: str
    dietary_preference: Optional[str] = None
    allergens: Optional[List[str]] = None
    lifestyle: Optional[List[str]] = None


# --- Helper Functions ---

def _profile_json(profile: UserProfile) -> str:
    return f"\n\n<<<PROFILE_UPDATE>>>{json.dumps(profile.to_dict())}<<<PROFILE_UPDATE>>>"


def _parse_update_command(query: str):
    """Parse /update <field> value1, value2. Returns (field, values) or (None, None)."""
    q = query.strip()
    if not q.lower().startswith("/update"):
        return None, None
    m = _re.match(r"/update\s+(\w+)\s+(.+)", q, _re.IGNORECASE | _re.DOTALL)
    if not m:
        return None, None
    field_name = m.group(1).lower()
    if field_name not in ("dietary_preference", "allergens", "lifestyle"):
        return None, None
    raw = m.group(2).strip()
    values = [x.strip() for x in raw.split(",") if x.strip()]
    if field_name == "dietary_preference" and values:
        values = [values[0]]
    return field_name, values


def _apply_profile_updates(profile: UserProfile, updates: dict) -> dict:
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


# --- Endpoints ---

@app.get("/")
def health_check():
    return {"status": "ok", "service": "IngreSure AI Scanner"}


@app.post("/onboard-menu")
async def onboard_menu(request: MenuOnboardRequest):
    logger.info("Onboarding menu for restaurant: %s", request.restaurant_id)
    try:
        return onboarding_service.process_menu(request.restaurant_id, request.menu_items)
    except Exception as e:
        logger.error("Onboarding failed: %s", e)
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

        verdict, scorecard = run_new_engine_scan(ingredients)
        logger.info(
            "Scan status=%s confidence=%s triggered=%s uncertain_count=%s",
            verdict.status.value, verdict.confidence_score,
            verdict.triggered_restrictions, len(verdict.uncertain_ingredients),
        )
        return {
            "raw_text": raw_text,
            "ingredients": ingredients,
            "dietary_scorecard": scorecard,
            "confidence_scores": {"overall": verdict.confidence_score},
        }
    except Exception as e:
        logger.error("Scan failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/verify-menu-item")
async def verify_item(request: VerificationRequest):
    """Verify a menu item against its ingredients and claimed diet types."""
    logger.info("Verifying item: %s", request.item_name)
    try:
        return verify_menu_item(
            item_name=request.item_name,
            description=request.description,
            ingredients=request.ingredients,
            claimed_diet_types=request.claimed_diet_types,
        )
    except Exception as e:
        logger.error("Verification failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/profile/{user_id}")
async def get_profile(user_id: str):
    """Get persisted profile by user_id."""
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
        logger.error("Get profile failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/profile")
async def create_or_update_profile(body: ProfileBody):
    """Create or update profile. Merge: only provided fields are updated."""
    try:
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
        logger.error("Profile save failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/grocery")
async def chat_grocery(request: ChatRequest):
    """
    Conversational Grocery Safety Assistant.

    Architecture (5 layers):
      1. Intent Detector   - rule-based NLU first, LLM fallback for ambiguous queries
      2. Profile Service   - persistent, merge-only updates; never reset on chat
      3. Ingredient Parser  - extract ingredients from natural language or label text
      4. Compliance Engine  - deterministic evaluation against ontology + restrictions
      5. Response Composer  - template-based responses, LLM for greetings/general only
    """
    logger.info("Grocery Chat query=%s user_id=%s", request.query, request.user_id)
    try:
        async def generate_safety():
            # Auto-assign user_id if not provided (eliminates legacy fallback path)
            user_id = request.user_id or f"anon-{uuid.uuid4().hex[:12]}"
            profile = get_or_create_profile(user_id)

            # 1) /update slash-command
            field_name, values = _parse_update_command(request.query)
            if field_name and values is not None:
                if field_name == "dietary_preference":
                    profile.update_merge(dietary_preference=values[0] if values else "No rules")
                elif field_name == "allergens":
                    profile.update_merge(allergens=values)
                elif field_name == "lifestyle":
                    profile.update_merge(lifestyle=values)
                save_profile(profile)
                logger.info("PROFILE_UPDATE user_id=%s field=%s values=%s", user_id, field_name, values)
                yield template_profile_update(profile, {field_name: values}, has_ingredients=False)
                yield _profile_json(profile)
                return

            # 2) Intent detection: rule-based first, LLM fallback
            parsed = detect_intent(request.query)
            logger.info(
                "INTENT_DETECT_RULES intent=%s profile_updates=%s ingredients=%s",
                parsed.intent, parsed.profile_updates, parsed.ingredients,
            )

            # LLM fallback for ambiguous queries
            if parsed.intent == "GENERAL_QUESTION" and not parsed.has_ingredients and not parsed.has_profile_update:
                llm_data = llm_extract_intent(request.query)
                if llm_data:
                    logger.info("INTENT_DETECT_LLM_FALLBACK intent=%s", llm_data["intent"])
                    llm_profile_updates = {}
                    for key in ("dietary_preference", "allergens", "lifestyle", "remove_allergens"):
                        if llm_data.get(key):
                            llm_profile_updates[key] = llm_data[key]
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
                        "PROFILE_UPDATE_NL user_id=%s updated_fields=%s",
                        user_id, list(updated_fields.keys()),
                    )

            # 5) Profile-only update (no ingredients)
            if parsed.intent == "PROFILE_UPDATE" and not parsed.has_ingredients:
                yield template_profile_update(profile, updated_fields, has_ingredients=False)
                yield _profile_json(profile)
                return

            # 6) General question (no ingredients)
            if parsed.intent == "GENERAL_QUESTION" and not parsed.has_ingredients:
                if profile.is_empty():
                    yield "<<<PROFILE_REQUIRED>>>\n\n"
                msg = llm_compose_general(request.query, profile)
                yield msg or template_general()
                yield _profile_json(profile)
                return

            # 7) Extract ingredients
            ingredients = parsed.ingredients

            if profile.is_empty() and not ingredients:
                yield "<<<PROFILE_REQUIRED>>>\n\n"
                msg = llm_compose_general(request.query, profile)
                yield msg or "Please set up your dietary profile first so I can give you personalized advice."
                yield _profile_json(profile)
                return

            if not ingredients:
                msg = llm_compose_general(request.query, profile)
                yield msg or template_no_ingredients()
                yield _profile_json(profile)
                return

            # 8) Expand compound items
            eval_ingredients, compound_map = expand_compounds(ingredients)

            # 9) Run DETERMINISTIC compliance engine
            restriction_ids = user_profile_model_to_restriction_ids(profile)
            profile_context = {
                "dietary_preference": profile.dietary_preference,
                "allergens": profile.allergens,
                "lifestyle": profile.lifestyle,
            }
            logger.info(
                "COMPLIANCE_RUN eval_ingredients=%s compounds=%s restriction_ids=%s",
                eval_ingredients, compound_map, restriction_ids,
            )
            verdict = run_new_engine_chat(
                eval_ingredients,
                user_profile=profile,
                restriction_ids=restriction_ids,
                profile_context=profile_context,
                use_api_fallback=True,
            )
            logger.info(
                "VERDICT=%s confidence=%.2f triggered=%s ingredients=%s",
                verdict.status.value, verdict.confidence_score,
                verdict.triggered_restrictions, ingredients,
            )

            # 10) Compose response (template-based: instant, accurate)
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

        return StreamingResponse(generate_safety(), media_type="text/plain")
    except Exception as e:
        logger.error("Grocery Chat failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/restaurant")
async def chat_restaurant(request: ChatRequest):
    """Restaurant Menu Assistant (RAG)."""
    logger.info("Restaurant Chat query: %s", request.query)
    try:
        context_items = rag_service.retrieve(request.query)

        async def generate_rag():
            for token in rag_service.generate_answer_stream(request.query, context_items):
                yield token

        return StreamingResponse(generate_rag(), media_type="text/plain")
    except Exception as e:
        logger.error("Restaurant Chat failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
