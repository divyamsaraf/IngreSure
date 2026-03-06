#!/usr/bin/env python3
"""
Add a few test unknown ingredients to the DB, then run one enrichment batch.

Useful to exercise: unknown_ingredients → APIs → groups/ingredients/aliases.
Requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY in env or .env

Run from backend: python scripts/add_test_unknowns_and_enrich.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
os.chdir(_backend)

from dotenv import load_dotenv
load_dotenv(_backend / ".env")
load_dotenv(_backend.parent / ".env")

# Test unknowns that external APIs can likely resolve
TEST_RAW = [
    "pitaya",
    "tahini",
    "nutritional yeast",
    "coconut aminos",
]


def main() -> int:
    from core.normalization.normalizer import normalize_ingredient_key
    from core.enrichment.unknown_log import log_unknown_ingredient
    from core.knowledge.ingredient_db import IngredientKnowledgeDB

    db = IngredientKnowledgeDB()
    if not db.enabled:
        print("Supabase not configured; set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return 1

    print("Adding test unknowns...")
    for raw in TEST_RAW:
        key = normalize_ingredient_key(raw)
        if key:
            log_unknown_ingredient(raw, key, restriction_ids=None, profile_context=None)
            print(f"  logged: {raw!r} -> {key!r}")

    print("Running one enrichment batch (limit=10)...")
    import subprocess
    result = subprocess.run(
        [sys.executable, str(_backend / "scripts" / "run_enrich_unknown_once.py"), "10"],
        cwd=str(_backend),
        env=os.environ.copy(),
        capture_output=False,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
