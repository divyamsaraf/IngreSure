from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import logging

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

# Import Engines
from ocr_engine import OCREngine
from llm_normalizer import IngredientNormalizer
from dietary_rules import DietaryRuleEngine

# Initialize Engines (Global to avoid reloading)
ocr_engine = OCREngine()
normalizer = IngredientNormalizer()
rule_engine = DietaryRuleEngine()

@app.get("/")
def health_check():
    return {"status": "ok", "service": "IngreSure AI Scanner"}

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

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
