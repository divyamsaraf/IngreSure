"""
DEPRECATED — legacy Layer-1 ingest into ``ingredient_*`` tables.

Canonical IKE-2 bulk path (writes ``ike2_*``)::

    cd backend && python -m core.knowledge.ike2.etl.bulk_inject \\
        ../data/layer1_<source>.json --source <label> [--dry-run]

This script remains for grandfathered legacy-table ops only. Prefer
``bulk_inject`` for any new / IKE-2 work (Item 1 Prompt 7).

JSON format (array of objects):
  [
    {
      "canonical_name": "chickpea",
      "aliases": ["chana", "garbanzo", "ceci"],
      "source": "usda_fdc",
      "animal_origin": false,
      "plant_origin": true,
      ...
    }
  ]

Run from backend: python scripts/ingest_layer1_json.py data/layer1_seed.json
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path

# Add backend to path
_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
os.chdir(_backend)

from dotenv import load_dotenv
load_dotenv(_backend / ".env")
load_dotenv(_backend.parent / ".env")

from core.knowledge.ingredient_db import IngredientKnowledgeDB, ALLOWED_INGREDIENT_SOURCES
from core.knowledge.ingest import ensure_group_with_aliases

_DEPRECATION = (
    "ingest_layer1_json.py is deprecated: it writes legacy ingredient_* tables, "
    "not ike2_*. Use: python -m core.knowledge.ike2.etl.bulk_inject "
    "<dump.json> --source <label> [--dry-run]"
)


def main() -> None:
    warnings.warn(_DEPRECATION, DeprecationWarning, stacklevel=2)
    print(f"WARNING: {_DEPRECATION}", file=sys.stderr)
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest_layer1_json.py <path_to_json>")
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    items = data if isinstance(data, list) else data.get("ingredients", data.get("items", []))
    if not items:
        print("No items in JSON")
        sys.exit(0)
    db = IngredientKnowledgeDB()
    if not db.enabled:
        print("Supabase not configured; set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)
    count = 0
    for item in items:
        canonical = item.get("canonical_name") or item.get("id") or item.get("name")
        if not canonical:
            continue
        aliases = item.get("aliases") or []
        source = (item.get("source") or "system").strip().lower()
        if source not in ALLOWED_INGREDIENT_SOURCES:
            source = "system"
        gid = ensure_group_with_aliases(
            db,
            canonical,
            aliases,
            source=source,
            alias_type=item.get("alias_type") or "synonym",
            language=item.get("language") or "en",
            region=item.get("region"),
            regions=item.get("regions"),
            animal_origin=item.get("animal_origin", False),
            plant_origin=item.get("plant_origin", False),
            synthetic=item.get("synthetic", False),
            fungal=item.get("fungal", False),
            insect_derived=item.get("insect_derived", False),
            animal_species=item.get("animal_species"),
            egg_source=item.get("egg_source", False),
            dairy_source=item.get("dairy_source", False),
            gluten_source=item.get("gluten_source", False),
            nut_source=item.get("nut_source"),
            soy_source=item.get("soy_source", False),
            sesame_source=item.get("sesame_source", False),
            alcohol_content=item.get("alcohol_content"),
            root_vegetable=item.get("root_vegetable", False),
            onion_source=item.get("onion_source", False),
            garlic_source=item.get("garlic_source", False),
            fermented=item.get("fermented", False),
            uncertainty_flags=item.get("uncertainty_flags") or [],
            derived_from=item.get("derived_from") or [],
        )
        if gid:
            count += 1
    print(f"Ingested {count}/{len(items)} groups from {path}")


if __name__ == "__main__":
    main()
