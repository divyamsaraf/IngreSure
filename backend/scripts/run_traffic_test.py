#!/usr/bin/env python3
"""
Run traffic: chat-style flow using compliance engine (run_new_engine_chat only).
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
    from core.bridge import run_new_engine_chat

    log_config()

    # Chat-style: profile dict with current keys (dietary_preference, allergens, lifestyle)
    profile = {"dietary_preference": "Vegan", "allergens": ["peanut"], "lifestyle": []}
    ingredients = ["water", "peanut", "garlic"]
    verdict = run_new_engine_chat(ingredients, user_profile=profile)
    logger.info(
        "Chat status=%s confidence=%s triggered=%s",
        verdict.status.value, verdict.confidence_score, verdict.triggered_restrictions,
    )

    logger.info("Traffic test done.")


if __name__ == "__main__":
    main()
