"""
IngreSure FastAPI application.

Endpoints:
    GET  /                  Health check
    POST /chat/grocery      Conversational grocery safety assistant (text only)
    GET  /profile/{user_id} Get user profile
    POST /profile           Create or update profile
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
import json
import re as _re
import uuid
import os
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

# Rate limiting (per-IP)
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
except ImportError:
    limiter = None  # optional: slowapi not installed


def _rate_limit(limit: str):
    """Apply rate limit decorator when slowapi is available; no-op otherwise."""
    return limiter.limit(limit) if limiter else lambda f: f


# Request body size limits (aligned with frontend BFF)
MAX_CHAT_BODY_BYTES = 512 * 1024   # 512KB for POST /chat/grocery
MAX_PROFILE_BODY_BYTES = 64 * 1024  # 64KB for POST /profile (aligned with BFF)
_BODY_LIMIT_BY_PATH = {"/chat/grocery": MAX_CHAT_BODY_BYTES, "/profile": MAX_PROFILE_BODY_BYTES}


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path in _BODY_LIMIT_BY_PATH:
            limit = _BODY_LIMIT_BY_PATH[request.url.path]
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    if int(content_length) > limit:
                        return JSONResponse(
                            {"detail": "Request body too large"},
                            status_code=413,
                        )
                except ValueError:
                    pass
        return await call_next(request)


app.add_middleware(BodySizeLimitMiddleware)

# CORS: use CORS_ORIGINS env (comma-separated) when set; otherwise allow all (dev)
_cors_origins_raw = os.environ.get("CORS_ORIGINS", "").strip()
CORS_ORIGINS = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()] if _cors_origins_raw else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Eagerly import core modules (avoid repeated lazy imports) ---
from core.config import get_ollama_url, get_ollama_model, PRODUCTION, MAX_CHAT_MESSAGE_LENGTH, redact_pii
from core.profile_options import get_profile_options_raw
from core.profile_storage import get_or_create_profile, save_profile, update_profile_partial
from core.models.user_profile import UserProfile
from core.bridge import (
    user_profile_model_to_restriction_ids,
    run_new_engine_chat,
)
from core.intent_detector import detect_intent, ParsedIntent
from core.llm_intent import llm_extract_intent
from core.response_composer import (
    compose_greeting as template_greeting,
    compose_profile_update as template_profile_update,
    compose_verdict as template_verdict,
    compose_general_question as template_general,
    compose_no_ingredients as template_no_ingredients,
    build_ingredient_audit_payload,
)
from core.llm_response import (
    llm_compose_greeting,
    llm_compose_general,
)
from core.compound_expansion import expand_compounds
from core.stream_tags import PROFILE_REQUIRED_TAG, PROFILE_UPDATE_TAG, INGREDIENT_AUDIT_TAG
from core.anon_session import sign_anon_token, verify_anon_token

# Public API (v1) - additive only
try:
    from core.api.v1 import v1_router
    app.include_router(v1_router)
except Exception as _exc:
    # Never break the main app if optional API modules fail to import.
    logger.warning("API v1 router failed to load (non-fatal): %s", _exc)


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
# Max chat length from config (single source; frontend fetches via GET /config)
MAX_CHAT_QUERY_LENGTH = MAX_CHAT_MESSAGE_LENGTH

# user_id: max length and allowed characters (alphanumeric, hyphen, underscore only)
USER_ID_MAX_LENGTH = 256
_USER_ID_RE = _re.compile(r"^[a-zA-Z0-9_-]+$")


def _user_id_from_auth(request: Request) -> Optional[str]:
    """If Authorization: Bearer <token> is present and valid, return user_id from token; else None."""
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    return verify_anon_token(token) if token else None


def _validate_user_id(user_id: str) -> None:
    """Validate user_id length and format. Raises HTTPException(400) if invalid."""
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="user_id is required and cannot be empty.")
    if len(user_id) > USER_ID_MAX_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"user_id must be at most {USER_ID_MAX_LENGTH} characters.",
        )
    if not _USER_ID_RE.match(user_id):
        raise HTTPException(
            status_code=400,
            detail="user_id may only contain letters, numbers, hyphens, and underscores.",
        )


def _500_detail(exc: Exception) -> str:
    """In production, return generic message; otherwise return str(exc). Always log full error."""
    logger.error("Error: %s", exc, exc_info=True)
    if PRODUCTION:
        return "Internal server error."
    return str(exc)


class ChatRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    userProfile: Optional[Dict] = None


class ProfileBody(BaseModel):
    user_id: str
    dietary_preference: Optional[str] = None
    allergens: Optional[List[str]] = None
    lifestyle: Optional[List[str]] = None


# --- Helper Functions ---

def _profile_json(profile: UserProfile) -> str:
    return f"\n\n{PROFILE_UPDATE_TAG}{json.dumps(profile.to_dict())}{PROFILE_UPDATE_TAG}"


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
        new_allergens = updates["allergens"]
        if new_allergens is not None and len(new_allergens) == 0:
            existing = []
        else:
            existing = list(profile.allergens or [])
            for a in (new_allergens or []):
                if a and a.lower() not in [e.lower() for e in existing]:
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
def root():
    return {"status": "ok", "service": "IngreSure AI Scanner"}


@app.get("/health")
def health_check():
    """Health for Docker/K8s. ingredient_audit_emitter: true means chat emits INGREDIENT_AUDIT blocks."""
    return {"status": "ok", "service": "IngreSure AI Scanner", "ingredient_audit_emitter": True}


@app.get("/config")
def get_config():
    """Single source for frontend: profile options and max chat message length."""
    return {
        "profile_options": get_profile_options_raw(),
        "max_chat_message_length": MAX_CHAT_MESSAGE_LENGTH,
    }


@app.get("/anon-session")
def anon_session():
    """
    Issue a server-issued anonymous identity (see docs/auth-and-identity.md).
    Returns { user_id, token }. When ANON_SESSION_SECRET is set, token is a signed
    token to send in Authorization: Bearer; when unset, token is null and client
    may use user_id only (current behaviour).
    """
    user_id = f"anon-{uuid.uuid4().hex[:12]}"
    token = sign_anon_token(user_id)
    return {"user_id": user_id, "token": token}


def _default_profile_response(user_id: str):
    return {
        "user_id": user_id,
        "dietary_preference": "No rules",
        "allergens": [],
        "lifestyle": [],
    }


@app.get("/profile/{user_id}")
@_rate_limit("120/minute")
async def get_profile(request: Request, user_id: str):
    """Get persisted profile by user_id."""
    _validate_user_id(user_id)
    try:
        from core.profile_storage import get_profile as get_stored
        profile = get_stored(user_id)
        if profile is None:
            return _default_profile_response(user_id)
        return profile.to_dict()
    except Exception as e:
        logger.error("Get profile failed: %s", e)
        return _default_profile_response(user_id)


@app.post("/profile")
@_rate_limit("60/minute")
async def create_or_update_profile(request: Request, body: ProfileBody):
    """Create or update profile. Merge: only provided fields are updated. When Authorization Bearer is valid, its user_id is used."""
    resolved_user_id = _user_id_from_auth(request) or body.user_id
    _validate_user_id(resolved_user_id)
    try:
        profile = update_profile_partial(
            resolved_user_id,
            dietary_preference=body.dietary_preference,
            allergens=body.allergens,
            lifestyle=body.lifestyle,
        )
        if profile is None:
            profile = get_or_create_profile(resolved_user_id)
            save_profile(profile)
        logger.info("PROFILE_UPDATE user_id=%s dietary_preference=%s", redact_pii(resolved_user_id), redact_pii(profile.dietary_preference))
        return {"status": "ok", "profile": profile.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_500_detail(e))


@app.post("/chat/grocery")
@_rate_limit("60/minute")
async def chat_grocery(request: Request, body: ChatRequest):
    """
    Conversational Grocery Safety Assistant.

    Architecture (5 layers):
      1. Intent Detector   - rule-based NLU first, LLM fallback for ambiguous queries
      2. Profile Service   - persistent, merge-only updates; never reset on chat
      3. Ingredient Parser  - extract ingredients from natural language or label text
      4. Compliance Engine  - deterministic evaluation against ontology + restrictions
      5. Response Composer  - template-based responses, LLM for greetings/general only
    """
    query = body.query if body.query is not None else ""
    if len(query) > MAX_CHAT_QUERY_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Query too long. Maximum {MAX_CHAT_QUERY_LENGTH} characters allowed.",
        )
    resolved_user_id = _user_id_from_auth(request)
    if not resolved_user_id and body.user_id is not None:
        _validate_user_id(body.user_id)
    logger.info("Grocery Chat query=%s user_id=%s", redact_pii(query), redact_pii(body.user_id or resolved_user_id))
    try:
        async def generate_safety():
            # Identity: Authorization Bearer token > body user_id > new anon- id
            user_id = resolved_user_id or body.user_id or f"anon-{uuid.uuid4().hex[:12]}"
            profile = get_or_create_profile(user_id)

            # 1) /update slash-command
            field_name, values = _parse_update_command(query)
            if field_name and values is not None:
                if field_name == "dietary_preference":
                    profile.update_merge(dietary_preference=values[0] if values else "No rules")
                elif field_name == "allergens":
                    profile.update_merge(allergens=values)
                elif field_name == "lifestyle":
                    profile.update_merge(lifestyle=values)
                save_profile(profile)
                logger.info("PROFILE_UPDATE user_id=%s field=%s values=%s", redact_pii(user_id), field_name, redact_pii(values) if values else values)
                yield template_profile_update(profile, {field_name: values}, has_ingredients=False)
                yield _profile_json(profile)
                return

            # 2) Intent detection: rule-based first, LLM fallback
            parsed = detect_intent(query)

            # Merge client-sent profile only when not a simple greeting (keeps server-authoritative for "hi")
            if parsed.intent != "GREETING" and getattr(body, "userProfile", None) and isinstance(body.userProfile, dict):
                try:
                    client = UserProfile.from_dict({**body.userProfile, "user_id": user_id})
                    if client.dietary_preference and client.dietary_preference != "No rules":
                        profile.update_merge(dietary_preference=client.dietary_preference)
                    if client.allergens:
                        profile.update_merge(allergens=client.allergens)
                    if client.lifestyle:
                        profile.update_merge(lifestyle=client.lifestyle)
                except Exception as e:
                    logger.warning("Could not merge body.userProfile: %s", e)
            logger.info(
                "INTENT_DETECT_RULES intent=%s profile_updates=%s ingredients=%s",
                parsed.intent, redact_pii(parsed.profile_updates), redact_pii(parsed.ingredients),
            )

            # LLM fallback for ambiguous queries
            if parsed.intent == "GENERAL_QUESTION" and not parsed.has_ingredients and not parsed.has_profile_update:
                llm_data = llm_extract_intent(query)
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
                        original_query=query,
                    )

            # 3) Handle GREETING
            if parsed.intent == "GREETING":
                msg = llm_compose_greeting(profile)
                yield msg or template_greeting(profile)
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
                        redact_pii(user_id), list(updated_fields.keys()),
                    )

            # 5) Profile-only update (no ingredients)
            if parsed.intent == "PROFILE_UPDATE" and not parsed.has_ingredients:
                yield template_profile_update(profile, updated_fields, has_ingredients=False)
                yield _profile_json(profile)
                return

            # 6) General question (no ingredients)
            if parsed.intent == "GENERAL_QUESTION" and not parsed.has_ingredients:
                if profile.is_empty():
                    yield f"{PROFILE_REQUIRED_TAG}\n\n"
                msg = llm_compose_general(query, profile)
                yield msg or template_general()
                yield _profile_json(profile)
                return

            # 7) Extract ingredients
            ingredients = parsed.ingredients

            if profile.is_empty() and not ingredients:
                yield f"{PROFILE_REQUIRED_TAG}\n\n"
                msg = llm_compose_general(query, profile)
                yield msg or "Please set up your dietary profile first so I can give you personalized advice."
                yield _profile_json(profile)
                return

            if not ingredients:
                msg = llm_compose_general(query, profile)
                yield msg or template_no_ingredients()
                yield _profile_json(profile)
                return

            # 8) Expand compound items
            eval_ingredients, compound_map = expand_compounds(ingredients)

            # Eager first byte: show progress before compliance run (improves perceived latency)
            yield "Checking ingredients…\n\n"

            # 9) Run DETERMINISTIC compliance engine
            restriction_ids = user_profile_model_to_restriction_ids(profile)
            profile_context = {
                "dietary_preference": profile.dietary_preference,
                "allergens": profile.allergens,
                "lifestyle": profile.lifestyle,
            }
            logger.info(
                "COMPLIANCE_RUN eval_ingredients=%s compounds=%s restriction_ids=%s",
                redact_pii(eval_ingredients), redact_pii(compound_map), restriction_ids,
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
                verdict.triggered_restrictions, redact_pii(ingredients),
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
            # 11) Emit profile first when updated so frontend header shows current diet before audit
            if profile_was_updated:
                yield _profile_json(profile)
            # 12) Emit structured INGREDIENT_AUDIT JSON for premium frontend cards
            audit_payload = build_ingredient_audit_payload(
                verdict=verdict,
                profile=profile,
                ingredients=eval_ingredients,
                display_names=compound_map if compound_map else None,
                explanation_text=response_text,
            )
            audit_block = f"{INGREDIENT_AUDIT_TAG}{json.dumps(audit_payload)}{INGREDIENT_AUDIT_TAG}"
            logger.info("INGREDIENT_AUDIT_EMITTED groups=%s", [g.get("status") for g in audit_payload.get("groups", [])])
            yield audit_block
            if not profile_was_updated:
                yield _profile_json(profile)

        return StreamingResponse(generate_safety(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=_500_detail(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
