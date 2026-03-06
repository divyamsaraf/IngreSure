#!/usr/bin/env python3
"""
Verify hybrid knowledge flow: normalizer, parser, DB resolution, unknown → DB.
Run from backend: python scripts/verify_knowledge_flow.py

To test with DB: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env
(local: http://127.0.0.1:54321 and the service_role key from supabase status or config).
"""
from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))

def main() -> int:
    print("1. Normalizer (Unicode + variants)")
    from core.normalization.normalizer import normalize_ingredient_key
    assert normalize_ingredient_key("  Chickpea  ") == "chickpea"
    assert normalize_ingredient_key("gelatine") == "gelatin"
    print("   OK: normalize_ingredient_key")

    print("2. Parser (flatten + category expansion)")
    from core.normalization.parser import flatten_ingredients
    out = flatten_ingredients("vegetable oil (sunflower, canola), salt")
    assert "sunflower oil" in out and "canola oil" in out and "salt" in out
    print("   OK: flatten_ingredients category expand")

    print("3. Resolver (DB-first when enabled)")
    from core.knowledge.canonicalizer import CanonicalResolver
    from core.config import USE_KNOWLEDGE_DB
    resolver = CanonicalResolver()
    # Static ontology or DB may have "wheat" / "egg"
    res = resolver.resolve_static("wheat")
    if res.ingredient:
        print(f"   OK: resolve_static('wheat') -> {res.ingredient.canonical_name}")
    else:
        print("   (wheat not in static ontology; DB may have it after seed)")

    print("4. Unknown → DB (when Supabase configured)")
    from core.knowledge.ingredient_db import IngredientKnowledgeDB
    from core.enrichment.unknown_log import log_unknown_ingredient
    from core.normalization.normalizer import normalize_ingredient_key
    db = IngredientKnowledgeDB()
    if db.enabled:
        key = normalize_ingredient_key("dragon fruit powder")
        log_unknown_ingredient("dragon fruit powder", key, restriction_ids=None, profile_context=None)
        print("   OK: log_unknown_ingredient -> unknown_ingredients table (if DB enabled)")
    else:
        print("   SKIP: Supabase not configured (unknowns go to JSON only)")

    print("5. Allowed sources (extended enum)")
    from core.knowledge.ingredient_db import ALLOWED_INGREDIENT_SOURCES
    assert "fao" in ALLOWED_INGREDIENT_SOURCES and "chebi" in ALLOWED_INGREDIENT_SOURCES
    print(f"   OK: {len(ALLOWED_INGREDIENT_SOURCES)} sources")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
