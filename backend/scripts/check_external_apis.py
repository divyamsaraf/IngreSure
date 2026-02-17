#!/usr/bin/env python3
"""
Check if external food APIs (USDA FDC, Open Food Facts) are reachable.
Run from backend: python scripts/check_external_apis.py
Exit 0 if at least one API works; 1 if both fail or none configured.
"""
import os
import sys
from pathlib import Path
from typing import Tuple

# Add backend to path when run as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent.parent / "frontend" / ".env.local")

# Short timeout for health check
HEALTH_TIMEOUT = 8


def check_usda(api_key: str) -> Tuple[bool, str]:
    """Return (success, message)."""
    if not (api_key or "").strip():
        return False, "no API key (set USDA_FDC_API_KEY)"
    from core.external_apis.usda_fdc import fetch_usda_fdc
    res = fetch_usda_fdc("sugar", api_key=api_key.strip(), timeout=HEALTH_TIMEOUT)
    if res.ingredient is not None:
        return True, f"ok (confidence={res.confidence})"
    return False, res.raw_response_summary or "no result"


def check_open_food_facts() -> Tuple[bool, str]:
    """Return (success, message)."""
    from core.external_apis.open_food_facts import fetch_open_food_facts
    res = fetch_open_food_facts("sugar", timeout=HEALTH_TIMEOUT)
    if res.ingredient is not None:
        return True, f"ok (confidence={res.confidence})"
    return False, res.raw_response_summary or "no result"


def main() -> int:
    from core.config import get_usda_fdc_api_key, get_open_food_facts_enabled
    usda_key = get_usda_fdc_api_key()
    off_enabled = get_open_food_facts_enabled()
    print("Checking external food APIs...")
    usda_ok, usda_msg = check_usda(usda_key)
    print(f"  USDA FDC:    {'OK' if usda_ok else 'FAIL'} - {usda_msg}")
    off_ok = False
    off_msg = "disabled (OPEN_FOOD_FACTS_ENABLED=false)"
    if off_enabled:
        off_ok, off_msg = check_open_food_facts()
    print(f"  Open Food Facts: {'OK' if off_ok else 'FAIL'} - {off_msg}")
    if usda_ok or off_ok:
        print("At least one API is working.")
        return 0
    print("All configured APIs failed or none configured.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
