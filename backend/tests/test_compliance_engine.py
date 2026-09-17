"""
Unit tests retained after ComplianceEngine removal (Item 16 Prompt 7).
Covers ontology registry, confidence helper, profile→restriction_ids, API mock resolve.
"""
import pytest


def test_ingredient_registry_resolve_static():
    """Ontology lookup: known ingredient resolves from static ontology."""
    from core.config import get_ontology_path
    from core.ontology.ingredient_registry import IngredientRegistry
    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")
    reg = IngredientRegistry(load_dynamic=False)
    ing = reg.resolve("water")
    assert ing is not None
    assert ing.canonical_name == "water"
    ing2, source = reg.resolve_with_source("water")
    assert ing2 is not None
    assert source == "static"


def test_ingredient_registry_unknown_logged():
    """Unknown ingredient returns None and is logged (no API in unit test)."""
    from core.config import get_ontology_path
    from core.ontology.ingredient_registry import IngredientRegistry
    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")
    reg = IngredientRegistry(load_dynamic=False)
    ing = reg.resolve("xyznonexistent123")
    assert ing is None


def test_confidence_high_when_all_resolved():
    """Confidence uses resolution levels: all high -> high score."""
    from core.evaluation.confidence import compute_confidence
    conf = compute_confidence(
        total_ingredients=5,
        resolved_count=5,
        uncertain_ingredients=[],
        warning_count=0,
        resolution_levels=["high"] * 5,
    )
    assert conf >= 0.9


def test_confidence_medium_api_mixed():
    """Confidence with mix of high and medium resolution levels."""
    from core.evaluation.confidence import compute_confidence
    conf = compute_confidence(
        total_ingredients=4,
        resolved_count=4,
        uncertain_ingredients=[],
        resolution_levels=["high", "high", "medium", "low"],
    )
    assert 0 < conf < 1.0


def test_confidence_uncertainty_penalty():
    """Uncertain ingredients reduce confidence."""
    from core.evaluation.confidence import compute_confidence
    conf = compute_confidence(
        total_ingredients=10,
        resolved_count=7,
        uncertain_ingredients=["a", "b", "c"],
        warning_count=0,
    )
    assert conf < 0.7


def test_user_profile_restriction_ids():
    """Profile-derived restriction_ids are applied (allergen + dietary_preference)."""
    from core.bridge import user_profile_model_to_restriction_ids
    from core.models.user_profile import UserProfile
    ids = user_profile_model_to_restriction_ids(
        UserProfile(
            user_id="u1",
            dietary_preference="Vegan",
            allergens=["peanut"],
            lifestyle=[],
        )
    )
    assert "peanut_allergy" in ids
    assert "vegan" in ids


def test_unknown_ingredient_external_lookup_mocked():
    """When external API returns an ingredient (mocked), registry uses it."""
    from unittest.mock import patch
    from core.ontology.ingredient_schema import Ingredient
    from core.ontology.ingredient_registry import IngredientRegistry
    from core.external_apis.base import EnrichmentResult
    from core.config import get_ontology_path
    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")
    unknown_raw = "zyzzx unknown starch q99"
    mock_ing = Ingredient(
        id="mock_zyzzx_starch",
        canonical_name="zyzzx unknown starch q99",
        aliases=[],
        derived_from=[], contains=[], may_contain=[],
        animal_origin=False, plant_origin=True, synthetic=False, fungal=False, insect_derived=False,
        animal_species=None, egg_source=False, dairy_source=False, gluten_source=False,
        nut_source=None, soy_source=False, sesame_source=False, alcohol_content=None,
        root_vegetable=False, onion_source=False, garlic_source=False, fermented=False,
        uncertainty_flags=[], regions=[],
    )
    with patch("core.external_apis.fetcher.enrich_unknown_ingredient") as mock_enrich:
        mock_enrich.return_value = EnrichmentResult(mock_ing, "high", "open_food_facts", "ok")
        reg = IngredientRegistry(load_dynamic=False)
        assert reg.resolve(unknown_raw) is None
        ing, source, level = reg.resolve_with_fallback(unknown_raw, try_api=True, log_unknown=True)
        assert ing is not None
        assert ing.canonical_name == "zyzzx unknown starch q99"
        assert source == "api"
        assert level == "high"
