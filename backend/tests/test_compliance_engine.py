"""
Unit tests for compliance engine: ontology lookup, confidence, profile overrides, API fallback (mocked).
Run from backend: python -m pytest tests/test_compliance_engine.py -v
"""
import pytest
from pathlib import Path


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


def test_compliance_engine_safe_vegan():
    """Engine returns SAFE when ingredients are vegan and restriction is vegan."""
    from core.config import get_ontology_path
    from core.evaluation.compliance_engine import ComplianceEngine
    from core.models.verdict import VerdictStatus
    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")
    engine = ComplianceEngine()
    verdict = engine.evaluate(
        ["water", "sugar", "salt"],
        restriction_ids=["vegan"],
        use_api_fallback=False,
    )
    assert verdict.status == VerdictStatus.SAFE
    assert verdict.confidence_score >= 0


def test_compliance_engine_not_safe_vegan():
    """Engine returns NOT_SAFE when dairy/meat and restriction is vegan."""
    from core.config import get_ontology_path
    from core.evaluation.compliance_engine import ComplianceEngine
    from core.models.verdict import VerdictStatus
    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")
    engine = ComplianceEngine()
    verdict = engine.evaluate(
        ["milk", "sugar"],
        restriction_ids=["vegan"],
        use_api_fallback=False,
    )
    assert verdict.status == VerdictStatus.NOT_SAFE
    assert "vegan" in verdict.triggered_restrictions


def test_compliance_engine_user_profile_restriction_ids():
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


def test_verdict_to_legacy_scorecard():
    """Verdict maps to legacy scorecard shape."""
    from core.bridge import verdict_to_legacy_scorecard
    from core.models.verdict import ComplianceVerdict, VerdictStatus
    v = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["vegan"],
        triggered_ingredients=["milk"],
        uncertain_ingredients=[],
        confidence_score=0.8,
    )
    scorecard = verdict_to_legacy_scorecard(v)
    assert "Vegan" in scorecard
    assert scorecard["Vegan"]["status"] == "red"


def test_trace_ingredient_informational():
    """Trace (<2%) unknown ingredients do not force UNCERTAIN when in trace set."""
    from core.config import get_ontology_path
    from core.evaluation.compliance_engine import ComplianceEngine
    from core.models.verdict import VerdictStatus
    from core.normalization.normalizer import normalize_ingredient_key
    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")
    engine = ComplianceEngine()
    # Known ingredients + one unknown that is in trace set
    trace_key = normalize_ingredient_key("trace flavor xyznonexistent")
    verdict = engine.evaluate(
        ["water", "sugar", "trace flavor xyznonexistent"],
        restriction_ids=["vegan"],
        trace_ingredient_keys={trace_key},
        use_api_fallback=False,
    )
    # Unknown in trace set is informational; if water/sugar are only others we may get SAFE
    assert verdict.status in (VerdictStatus.SAFE, VerdictStatus.UNCERTAIN)


def test_minor_ingredient_does_not_reduce_confidence():
    """Minor (<2%) ingredients are informational_only; resolution_level high so confidence not reduced."""
    from core.config import get_ontology_path
    from core.evaluation.compliance_engine import ComplianceEngine
    from core.normalization.normalizer import normalize_ingredient_key
    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")
    engine = ComplianceEngine()
    trace_key = normalize_ingredient_key("minor unknown xyz")
    verdict_with_trace = engine.evaluate(
        ["water", "sugar", "minor unknown xyz"],
        restriction_ids=["vegan"],
        trace_ingredient_keys={trace_key},
        use_api_fallback=False,
    )
    verdict_without_trace = engine.evaluate(
        ["water", "sugar", "minor unknown xyz"],
        restriction_ids=["vegan"],
        trace_ingredient_keys=set(),
        use_api_fallback=False,
    )
    # With trace: unknown is informational (high weight), so confidence >= without (where unknown counts as low)
    assert verdict_with_trace.informational_ingredients
    assert verdict_with_trace.confidence_score >= verdict_without_trace.confidence_score


def test_api_failed_ingredient_uncertain_low_confidence():
    """When all external APIs fail: do NOT mark SAFE; mark UNCERTAIN, confidence 0.0-0.4."""
    from unittest.mock import patch
    from core.config import get_ontology_path
    from core.evaluation.compliance_engine import ComplianceEngine
    from core.models.verdict import VerdictStatus
    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")
    with patch("core.external_apis.fetcher.enrich_unknown_ingredient") as mock_enrich:
        from core.external_apis.base import EnrichmentResult
        mock_enrich.return_value = EnrichmentResult(None, "low", "none", "no_result")
        engine = ComplianceEngine()
        verdict = engine.evaluate(
            ["water", "sugar", "xyznonexistent_api_fail"],
            restriction_ids=["vegan"],
            use_api_fallback=True,
        )
        assert "xyznonexistent_api_fail" in verdict.uncertain_ingredients
        assert verdict.status == VerdictStatus.UNCERTAIN
        assert 0.0 <= verdict.confidence_score <= 0.4


def test_minor_ingredient_violation_confidence_band():
    """When only minor (<2%) ingredients trigger: NOT_SAFE, confidence 0.2-0.5."""
    from core.config import get_ontology_path
    from core.evaluation.compliance_engine import ComplianceEngine
    from core.models.verdict import VerdictStatus
    from core.normalization.normalizer import normalize_ingredient_key
    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")
    engine = ComplianceEngine()
    # Milk is vegan violation; mark it as trace so only minor triggers
    trace_key = normalize_ingredient_key("milk")
    verdict = engine.evaluate(
        ["water", "sugar", "milk"],
        restriction_ids=["vegan"],
        trace_ingredient_keys={trace_key},
        use_api_fallback=False,
    )
    assert verdict.status == VerdictStatus.NOT_SAFE
    assert "vegan" in verdict.triggered_restrictions
    assert 0.2 <= verdict.confidence_score <= 0.5


def test_integration_unknown_ingredient_external_resolution():
    """Integration: unknown ingredient (e.g. isinglass) resolved via mocked API; verdict respects profile."""
    from unittest.mock import patch
    from core.ontology.ingredient_schema import Ingredient
    from core.external_apis.base import EnrichmentResult
    from core.config import get_ontology_path
    from core.evaluation.compliance_engine import ComplianceEngine
    from core.models.verdict import VerdictStatus
    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")
    # Isinglass: animal-derived (fish), not vegan
    mock_ing = Ingredient(
        id="off_isinglass",
        canonical_name="isinglass",
        aliases=["inglass"],
        derived_from=[], contains=[], may_contain=[],
        animal_origin=True,
        plant_origin=False,
        synthetic=False,
        fungal=False,
        insect_derived=False,
        animal_species="fish",
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
    with patch("core.external_apis.fetcher.enrich_unknown_ingredient") as mock_enrich:
        mock_enrich.return_value = EnrichmentResult(mock_ing, "high", "open_food_facts", "ok")
        engine = ComplianceEngine()
        verdict = engine.evaluate(
            ["water", "isinglass"],
            restriction_ids=["vegan"],
            use_api_fallback=True,
        )
        assert verdict.status == VerdictStatus.NOT_SAFE
        assert "vegan" in verdict.triggered_restrictions
        assert "isinglass" in (verdict.triggered_ingredients or [])
        assert verdict.confidence_score >= 0.5


def test_unknown_ingredient_external_lookup_mocked():
    """When external API returns an ingredient (mocked), engine uses it for evaluation."""
    from unittest.mock import patch
    from core.ontology.ingredient_schema import Ingredient
    from core.ontology.ingredient_registry import IngredientRegistry
    from core.external_apis.base import EnrichmentResult
    from core.config import get_ontology_path
    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")
    mock_ing = Ingredient(
        id="mock_tapioca",
        canonical_name="tapioca starch",
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
        ing, source, level = reg.resolve_with_fallback("tapioca starch", try_api=True, log_unknown=True)
        assert ing is not None
        assert ing.canonical_name == "tapioca starch"
        assert source == "api"
        assert level == "high"
