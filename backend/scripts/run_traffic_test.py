#!/usr/bin/env python3
"""
Run traffic: scan-style and chat-style flows using compliance engine.
Run from backend: python scripts/run_traffic_test.py
"""
import os
import sys
import logging
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

def main():
    from core.config import log_config
    from core.bridge import run_new_engine_scan, run_new_engine_chat

    log_config()

    ingredients_scan = ["water", "sugar", "beef", "milk", "unknown_xyz"]
    verdict, scorecard = run_new_engine_scan(ingredients_scan)
    logger.info("Scan status=%s confidence=%s triggered=%s uncertain=%s",
                verdict.status.value, verdict.confidence_score,
                verdict.triggered_restrictions, verdict.uncertain_ingredients)

    profile = {"diet": "vegan", "dairy_allowed": False, "allergens": ["peanut"]}
    ingredients_chat = ["water", "peanut", "garlic"]
    verdict = run_new_engine_chat(ingredients_chat, profile)
    logger.info("Chat status=%s confidence=%s triggered=%s",
                verdict.status.value, verdict.confidence_score, verdict.triggered_restrictions)

    logger.info("Traffic test done.")

if __name__ == "__main__":
    main()
