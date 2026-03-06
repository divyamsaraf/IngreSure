#!/usr/bin/env python3
"""
Check if all external enrichment APIs are reachable.

There are 5 APIs in the unknown-ingredient lookup chain (in order):
  1. USDA FDC (optional; needs USDA_FDC_API_KEY)
  2. Open Food Facts (can disable with OPEN_FOOD_FACTS_ENABLED=false)
  3. PubChem
  4. ChEBI
  5. Wikidata

Run from repo root or backend: python backend/scripts/check_external_apis.py
       or from backend:        python scripts/check_external_apis.py
Exit 0 if at least one API works; 1 if all fail or none configured.
"""
import sys
from pathlib import Path
from typing import Tuple

# Add backend to path when run as script
_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))

from dotenv import load_dotenv
load_dotenv(_backend / ".env")
load_dotenv(_backend.parent / "frontend" / ".env.local")

# Short timeout for health check
HEALTH_TIMEOUT = 10


def check_usda(api_key: str) -> Tuple[bool, str]:
    """Return (success, message)."""
    if not (api_key or "").strip():
        return False, "skipped (no USDA_FDC_API_KEY)"
    try:
        from core.external_apis.usda_fdc import fetch_usda_fdc
        res = fetch_usda_fdc("sugar", api_key=api_key.strip(), timeout=HEALTH_TIMEOUT)
        if res.ingredient is not None:
            return True, f"ok (confidence={res.confidence})"
        return False, res.raw_response_summary or "no result"
    except Exception as e:
        return False, str(e)[:60]


def check_open_food_facts() -> Tuple[bool, str]:
    """Return (success, message)."""
    try:
        from core.config import get_open_food_facts_enabled
        if not get_open_food_facts_enabled():
            return False, "skipped (OPEN_FOOD_FACTS_ENABLED=false)"
        from core.external_apis.open_food_facts import fetch_open_food_facts
        res = fetch_open_food_facts("sugar", timeout=HEALTH_TIMEOUT)
        if res.ingredient is not None:
            return True, f"ok (confidence={res.confidence})"
        return False, res.raw_response_summary or "no result"
    except Exception as e:
        return False, str(e)[:60]


def check_pubchem() -> Tuple[bool, str]:
    """Return (success, message)."""
    try:
        from core.external_apis.pubchem import fetch_pubchem
        res = fetch_pubchem("sugar", timeout=HEALTH_TIMEOUT)
        if res.ingredient is not None:
            return True, f"ok (confidence={res.confidence})"
        return False, "no result" if res.source == "none" else res.source or "no result"
    except Exception as e:
        return False, str(e)[:60]


def check_chebi() -> Tuple[bool, str]:
    """Return (success, message)."""
    try:
        from core.external_apis.chebi import fetch_chebi
        res = fetch_chebi("sucrose", timeout=HEALTH_TIMEOUT)
        if res.ingredient is not None:
            return True, f"ok (confidence={res.confidence})"
        return False, "no result" if res.source == "none" else res.source or "no result"
    except Exception as e:
        return False, str(e)[:60]


def check_wikidata() -> Tuple[bool, str]:
    """Return (success, message)."""
    try:
        from core.external_apis.wikidata_api import fetch_wikidata
        res = fetch_wikidata("sugar", timeout=HEALTH_TIMEOUT)
        if res.ingredient is not None:
            return True, f"ok (confidence={res.confidence})"
        return False, "no result" if res.source == "none" else res.source or "no result"
    except Exception as e:
        return False, str(e)[:60]


def main() -> int:
    from core.config import get_usda_fdc_api_key

    usda_key = get_usda_fdc_api_key()
    print("Checking all 5 external enrichment APIs...")
    print("  (Order used for unknown ingredients: USDA → Open Food Facts → PubChem → ChEBI → Wikidata)\n")

    results = []
    # 1. USDA FDC
    ok, msg = check_usda(usda_key)
    results.append(("USDA FDC", ok, msg))
    # 2. Open Food Facts
    ok, msg = check_open_food_facts()
    results.append(("Open Food Facts", ok, msg))
    # 3. PubChem
    ok, msg = check_pubchem()
    results.append(("PubChem", ok, msg))
    # 4. ChEBI
    ok, msg = check_chebi()
    results.append(("ChEBI", ok, msg))
    # 5. Wikidata
    ok, msg = check_wikidata()
    results.append(("Wikidata", ok, msg))

    for name, ok, msg in results:
        status = "OK" if ok else "FAIL"
        print(f"  {name:<18} {status:<6} - {msg}")

    working = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n  Total: {working}/{total} APIs working.")
    if working >= 1:
        print("  At least one API is working; unknown-ingredient lookup will run.")
        return 0
    print("  All APIs failed or were skipped. Set USDA_FDC_API_KEY and/or check network.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
