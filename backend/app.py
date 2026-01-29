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

# Initialize App
app = FastAPI(title="IngreSure Visual Scanner API")

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
    context_filter: Optional[Dict] = None # e.g. {"restaurant_id": "..."}
    userProfile: Optional[Dict] = None # { "diet": "Vegan", "dairy_allowed": False, "allergens": [], "is_onboarding_completed": True }

class MenuOnboardRequest(BaseModel):
    restaurant_id: str
    menu_items: List[Dict]

# Import Engines
from ocr_engine import OCREngine
from llm_normalizer import IngredientNormalizer
from dietary_rules import DietaryRuleEngine
from verification_service import verify_menu_item
from rag_service import RAGService
from onboarding_service import OnboardingService

# Initialize Engines (Global to avoid reloading)
ocr_engine = OCREngine()
normalizer = IngredientNormalizer()
rule_engine = DietaryRuleEngine()
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
    """
    1. OCR (PaddleOCR)
    2. LLM Cleanup (Ollama)
    3. Rule Engine Classification
    """
    logger.info(f"Received scan request: {file.filename}")
    
    try:
        # 1. Read Image
        image_bytes = await file.read()
        
        # 2. Run OCR
        raw_text = ocr_engine.extract_text(image_bytes)
        logger.info(f"OCR Extracted {len(raw_text)} chars")
        
        # 3. Normalize Ingredients (LLM)
        ingredients = normalizer.normalize(raw_text)
        logger.info(f"Normalized {len(ingredients)} ingredients")
        
        # 4. Apply Dietary Rules
        scorecard = rule_engine.classify(ingredients)
        
        # 5. Calculate Confidence (Simple heuristic for now)
        # In a real app, we'd use OCR confidence + LLM logprobs
        confidence = 0.9 if len(ingredients) > 0 else 0.0
        
        return {
            "raw_text": raw_text,
            "ingredients": ingredients,
            "dietary_scorecard": scorecard,
            "confidence_scores": {"overall": confidence}
        }

    except Exception as e:
        logger.error(f"Scan failed: {e}")
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

@app.post("/update-profile")
async def update_profile(request: UpdateProfileRequest):
    """
    Endpoint to log profile updates. State is now managed client-side and synced via chat protocol.
    This remains for logging/validation purposes.
    """
    try:
        # Stateless Backend Refactor: We don't store session state in global anymore.
        # Frontend is the Source of Truth.
        logger.info(f"Frontend Profile Sync: {request.profile}")
        return {"status": "ok", "message": "Profile synced (Stateless)"}
    except Exception as e:
        logger.error(f"Profile sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/grocery")
async def chat_grocery(request: ChatRequest):
    """
    Endpoint 1: Grocery / Food Item Scanner (SafetyAnalyst, The "IngreSure Assistant").
    Strict Deterministic Rules.
    """
    logger.info(f"Grocery Chat query: {request.query}")
    try:
        async def generate_safety():
            # Pass profile explicitly to stateless analyst
            for token in SafetyAnalyst.analyze(request.query, request.userProfile):
                yield token
        return StreamingResponse(generate_safety(), media_type="text/plain")
    except Exception as e:
        logger.error(f"Grocery Chat failed: {e}")
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
