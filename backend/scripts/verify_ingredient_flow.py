#!/usr/bin/env python3
"""
Verify ingredient resolution and DB update flow (no live API/DB required when mocked).

Flow:
  1. Resolve from static ontology -> no external call.
  2. Unknown ingredient -> log_unknown_ingredient (JSON) -> enrich_unknown_ingredient (API)
     -> on high confidence: append_to_dynamic_ontology + add_ingredient (in-memory).
  3. Background worker: read unknown_ingredients (Supabase) -> fetch_ingredient_from_apis
     -> upsert_from_enrichment (ingredient_groups, ingredients, ingredient_aliases).

Run: cd backend && python scripts/verify_ingredient_flow.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    from core.ontology.ingredient_registry import IngredientRegistry
    from core.ontology.ingredient_schema import Ingredient
    from core.external_apis.base import EnrichmentResult
    from core.knowledge.ingredient_db import ALLOWED_INGREDIENT_SOURCES, IngredientKnowledgeDB
    from core.config import get_ontology_path

    print("1. Static ontology resolution (no external call)")
    if not get_ontology_path().exists():
        print("   SKIP: ontology.json not found")
    else:
        reg = IngredientRegistry()
        ing = reg.resolve("wheat")
        assert ing is not None, "wheat should be in ontology"
        print(f"   OK: resolve('wheat') -> id={ing.id}, nut_source={ing.nut_source}")

    print("2. Unknown ingredient: external lookup (mocked)")
    from unittest.mock import patch
    mock_ing = Ingredient(
        id="usda_test",
        canonical_name="Test Grain",
        aliases=[],
        derived_from=[], contains=[], may_contain=[],
        animal_origin=False, plant_origin=True, synthetic=False, fungal=False, insect_derived=False,
        animal_species=None, egg_source=False, dairy_source=False, gluten_source=False,
        nut_source=None, soy_source=False, sesame_source=False, alcohol_content=None,
        root_vegetable=False, onion_source=False, garlic_source=False, fermented=False,
        uncertainty_flags=[], regions=[],
    )
    with patch("core.external_apis.fetcher.enrich_unknown_ingredient") as m:
        m.return_value = EnrichmentResult(mock_ing, "high", "usda_fdc", "ok")
        reg2 = IngredientRegistry()
        out, source, level = reg2.resolve_with_fallback("obscure grain", try_api=True, log_unknown=True)
        assert out is not None and source == "api" and level == "high"
        print(f"   OK: unknown -> API (mocked) -> id={out.id}, canonical_name={out.canonical_name}")

    print("3. DB upsert format (mocked client)")
    with patch("core.knowledge.ingredient_db.get_supabase_config", return_value=None):
        db = IngredientKnowledgeDB(client=None)
    assert not db.enabled
    mock_client = __build_mock_supabase()
    db_real = IngredientKnowledgeDB(client=mock_client)
    result = EnrichmentResult(mock_ing, "high", "usda_fdc", "ok")
    gid = db_real.upsert_from_enrichment(result, normalized_key="test grain")
    assert gid is not None
    group_payload = mock_client.table.return_value.insert.call_args_list[0][0][0]
    assert isinstance(group_payload["uncertainty_flags"], list)
    assert group_payload.get("canonical_name") in ("Test Grain", "test grain")
    ing_payload = mock_client.table.return_value.insert.call_args_list[1][0][0]
    assert ing_payload["source"] in ALLOWED_INGREDIENT_SOURCES
    print(f"   OK: upsert_from_enrichment -> group_id={gid}, source={ing_payload['source']}, list fields OK")

    print("All checks passed.")
    return 0


def __build_mock_supabase():
    from unittest.mock import MagicMock
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.is_.return_value.limit.return_value.execute.return_value.data = []
    mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    def insert(payload):
        m = MagicMock()
        if "canonical_name" in payload and "animal_origin" in payload:
            m.execute.return_value.data = [{"id": "group-1"}]
        elif "normalized_name" in payload:
            m.execute.return_value.data = [{"id": "ing-1"}]
        else:
            m.execute.return_value.data = [{"id": "alias-1"}]
        return MagicMock(execute=m.execute)
    mock_table.insert.side_effect = insert
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    return mock_client


if __name__ == "__main__":
    sys.exit(main())
