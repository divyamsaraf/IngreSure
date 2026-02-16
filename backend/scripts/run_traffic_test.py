#!/usr/bin/env python3
"""
Run traffic with USE_NEW_ENGINE and SHADOW_MODE from backend/.env.
Exercises scan-style and chat-style flows and logs comparison.
Run from repo root: python backend/scripts/run_traffic_test.py
Or from backend: python scripts/run_traffic_test.py (with PYTHONPATH=.)
"""
import os
import sys
import logging
from pathlib import Path

# Ensure backend is on path and load .env
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

# Configure logging to see INGRESURE_ENGINE, SHADOW_*, UNKNOWN_INGREDIENT, COMPLIANCE_ENGINE
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

def main():
    from core.config import USE_NEW_ENGINE, SHADOW_MODE, log_config
    from core.bridge import run_new_engine_scan, run_new_engine_chat
    from dietary_rules import DietaryRuleEngine
    from ingredient_ontology import UserProfile, evaluate_ingredient_risk
    from safety_analyst import SafetyAnalyst

    log_config()
    logger.info("Traffic test: USE_NEW_ENGINE=%s SHADOW_MODE=%s", USE_NEW_ENGINE, SHADOW_MODE)

    # --- Scan-style: ingredients list, scorecard ---
    ingredients_scan = ["water", "sugar", "beef", "milk", "unknown_xyz"]
    if USE_NEW_ENGINE:
        verdict, scorecard = run_new_engine_scan(ingredients_scan)
        logger.info("Scan new_engine status=%s confidence=%s triggered=%s uncertain=%s",
                    verdict.status.value, verdict.confidence_score,
                    verdict.triggered_restrictions, verdict.uncertain_ingredients)
        if SHADOW_MODE:
            legacy_scorecard = DietaryRuleEngine.classify(ingredients_scan)
            for diet in ["Vegan", "Jain", "Halal", "Hindu Veg"]:
                leg = legacy_scorecard.get(diet, {}).get("status")
                new = scorecard.get(diet, {}).get("status")
                if leg != new:
                    logger.info("SHADOW_SCAN diff diet=%s legacy=%s new=%s", diet, leg, new)
    else:
        scorecard = DietaryRuleEngine.classify(ingredients_scan)
        logger.info("Scan legacy scorecard=%s", {k: v.get("status") for k, v in scorecard.items()})

    # --- Chat-style: ingredients + profile, verdict ---
    profile = {"diet": "vegan", "dairy_allowed": False, "allergens": ["peanut"]}
    ingredients_chat = ["water", "peanut", "garlic"]
    if USE_NEW_ENGINE:
        verdict = run_new_engine_chat(ingredients_chat, profile)
        logger.info("Chat new_engine status=%s confidence=%s triggered=%s",
                    verdict.status.value, verdict.confidence_score, verdict.triggered_restrictions)
        if SHADOW_MODE:
            up = SafetyAnalyst.create_profile_from_dict(profile)
            leg_status = "SAFE"
            for ing in ingredients_chat:
                r = evaluate_ingredient_risk(ing, up)
                if r["status"] == "NOT_SAFE":
                    leg_status = "NOT_SAFE"
                    break
                if r["status"] == "UNCLEAR":
                    leg_status = "UNCLEAR"
            if leg_status != verdict.status.value:
                logger.info("SHADOW_CHAT legacy_status=%s new_status=%s", leg_status, verdict.status.value)
    else:
        up = SafetyAnalyst.create_profile_from_dict(profile)
        for ing in ingredients_chat:
            r = evaluate_ingredient_risk(ing, up)
            logger.info("Chat legacy %s -> %s", ing, r["status"])

    logger.info("Traffic test done.")

if __name__ == "__main__":
    main()
