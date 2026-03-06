"""
Unit tests for IngredientKnowledgeDB: upsert_from_enrichment format and edge cases.
Run from backend: python -m pytest tests/test_ingredient_db.py -v
"""
import pytest
from unittest.mock import MagicMock, patch

from core.ontology.ingredient_schema import Ingredient
from core.external_apis.base import EnrichmentResult
from core.knowledge.ingredient_db import ALLOWED_INGREDIENT_SOURCES, IngredientKnowledgeDB


def test_upsert_from_enrichment_returns_none_when_disabled():
    """When DB is not configured, upsert_from_enrichment returns None."""
    with patch("core.knowledge.ingredient_db.get_supabase_config", return_value=None):
        db = IngredientKnowledgeDB(client=None)
    assert not db.enabled
    ing = Ingredient(
        id="test_1",
        canonical_name="test ingredient",
        aliases=[],
        derived_from=[],
        contains=[],
        may_contain=[],
        animal_origin=False,
        plant_origin=True,
        synthetic=False,
        fungal=False,
        insect_derived=False,
        animal_species=None,
        egg_source=False,
        dairy_source=False,
        gluten_source=False,
        nut_source=None,
        soy_source=False,
        sesame_source=False,
        alcohol_content=None,
        root_vegetable=False,
        onion_source=False,
        garlic_source=False,
        fermented=False,
        uncertainty_flags=[],
        regions=[],
    )
    result = EnrichmentResult(ing, "high", "usda_fdc", "ok")
    assert db.upsert_from_enrichment(result, normalized_key="test ingredient") is None


def test_upsert_from_enrichment_returns_none_for_empty_inputs():
    """Returns None when result.ingredient or normalized_key is missing."""
    mock_client = MagicMock()
    db = IngredientKnowledgeDB(client=mock_client)
    assert db.upsert_from_enrichment(EnrichmentResult(None, "low", "none", ""), "key") is None
    ing = Ingredient(
        id="x", canonical_name="x", aliases=[], derived_from=[], contains=[], may_contain=[],
        animal_origin=False, plant_origin=False, synthetic=False, fungal=False, insect_derived=False,
        animal_species=None, egg_source=False, dairy_source=False, gluten_source=False,
        nut_source=None, soy_source=False, sesame_source=False, alcohol_content=None,
        root_vegetable=False, onion_source=False, garlic_source=False, fermented=False,
        uncertainty_flags=[], regions=[],
    )
    assert db.upsert_from_enrichment(EnrichmentResult(ing, "high", "usda_fdc", "ok"), "") is None


def test_upsert_from_enrichment_payload_format_and_source_normalization():
    """
    When client is mocked, verify insert payloads use list values for jsonb fields
    and source is normalized to allowed enum.
    """
    mock_table = MagicMock()
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    # Select chain: .select().eq().is_().limit().execute() -> .data = []
    mock_select = MagicMock()
    mock_execute = MagicMock()
    mock_execute.execute.return_value.data = []
    mock_select.select.return_value.eq.return_value.is_.return_value.limit.return_value.execute.return_value.data = []
    mock_select.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    mock_table.select.return_value.eq.return_value.is_.return_value.limit.return_value.execute.return_value.data = []
    mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

    # Insert: first call returns group id, second ingredient id
    def insert_side_effect(payload):
        mock_exec = MagicMock()
        if "canonical_name" in payload and "animal_origin" in payload:
            mock_exec.execute.return_value.data = [{"id": "group-uuid-1"}]
        elif "normalized_name" in payload:
            mock_exec.execute.return_value.data = [{"id": "ingredient-uuid-1"}]
        else:
            mock_exec.execute.return_value.data = [{"id": "alias-uuid-1"}]
        return MagicMock(execute=mock_exec.execute)
    mock_table.insert.side_effect = insert_side_effect

    db = IngredientKnowledgeDB(client=mock_client)
    ing = Ingredient(
        id="usda_xyz",
        canonical_name="Some Ingredient",
        aliases=[],
        derived_from=[],
        contains=[],
        may_contain=[],
        animal_origin=False,
        plant_origin=True,
        synthetic=False,
        fungal=False,
        insect_derived=False,
        animal_species=None,
        egg_source=False,
        dairy_source=False,
        gluten_source=False,
        nut_source=None,
        soy_source=False,
        sesame_source=False,
        alcohol_content=None,
        root_vegetable=False,
        onion_source=False,
        garlic_source=False,
        fermented=False,
        uncertainty_flags=[],
        regions=[],
    )
    result = EnrichmentResult(ing, "high", "usda_fdc", "ok")
    group_id = db.upsert_from_enrichment(result, normalized_key="some ingredient")
    assert group_id == "group-uuid-1"
    insert_calls = mock_table.insert.call_args_list
    assert len(insert_calls) >= 2
    group_payload = insert_calls[0][0][0]
    assert isinstance(group_payload.get("uncertainty_flags"), list)
    assert isinstance(group_payload.get("derived_from"), list)
    assert isinstance(group_payload.get("regions"), list)
    ing_payload = insert_calls[1][0][0]
    assert ing_payload.get("source") in ALLOWED_INGREDIENT_SOURCES
