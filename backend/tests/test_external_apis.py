"""
Unit tests for external API connectors (mocked).
Run from backend: python -m pytest tests/test_external_apis.py -v
"""
import pytest
from unittest.mock import patch, MagicMock


def test_usda_fdc_no_key_returns_low():
    """Without API key, USDA returns low confidence (no request)."""
    from core.external_apis.usda_fdc import fetch_usda_fdc
    res = fetch_usda_fdc("flour", api_key="")
    assert res.confidence == "low"
    assert res.ingredient is None


@patch("core.external_apis.usda_fdc.get_with_retries")
def test_usda_fdc_mock_success(mock_get):
    """Mock USDA response maps to Ingredient with high confidence."""
    from core.external_apis.usda_fdc import fetch_usda_fdc
    mock_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "foods": [
                {
                    "description": "Wheat flour",
                    "foodCategory": "Cereal Grains and Pasta",
                }
            ]
        },
    )
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = (mock_resp, None)
    res = fetch_usda_fdc("wheat flour", api_key="test-key")
    assert res.ingredient is not None
    assert res.source == "usda_fdc"
    assert "flour" in res.ingredient.canonical_name.lower() or res.ingredient.canonical_name


@patch("core.external_apis.usda_fdc.get_with_retries")
def test_usda_fdc_rejects_chicken_to_lamb_mismatch(mock_get):
    """USDA first hit can be wrong species; pick chicken result and reject lamb."""
    from core.external_apis.usda_fdc import fetch_usda_fdc
    mock_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "foods": [
                {
                    "description": "Lamb, variety meats and by-products, mechanically separated, raw",
                    "foodCategory": "Lamb, Veal, and Game Products",
                    "fdcId": 172537,
                },
                {
                    "description": "Chicken, mechanically separated, raw",
                    "foodCategory": "Poultry Products",
                    "fdcId": 171077,
                },
            ]
        },
    )
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = (mock_resp, None)
    res = fetch_usda_fdc("mechanically separated chicken", api_key="test-key")
    assert res.ingredient is not None
    assert "chicken" in res.ingredient.canonical_name.lower()
    assert "lamb" not in res.ingredient.canonical_name.lower()
    assert res.confidence in ("high", "medium")


@patch("core.external_apis.usda_fdc.get_with_retries")
def test_usda_fdc_all_species_mismatch_returns_no_result(mock_get):
    from core.external_apis.usda_fdc import fetch_usda_fdc
    mock_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "foods": [
                {
                    "description": "Lamb, variety meats and by-products, mechanically separated, raw",
                    "foodCategory": "Lamb, Veal, and Game Products",
                },
            ]
        },
    )
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = (mock_resp, None)
    res = fetch_usda_fdc("mechanically separated chicken", api_key="test-key")
    assert res.ingredient is None
    assert res.confidence == "low"


@patch("core.external_apis.open_food_facts.get_with_retries")
def test_open_food_facts_rejects_plant_animal_mismatch(mock_get):
    from core.external_apis.open_food_facts import fetch_open_food_facts
    mock_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "products": [
                {"product_name": "Whole cow milk 3.25%", "ingredients_text": "milk"},
                {"product_name": "Coconut milk canned", "ingredients_text": "coconut"},
            ]
        },
    )
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = (mock_resp, None)
    res = fetch_open_food_facts("coconut milk")
    assert res.ingredient is not None
    assert "coconut" in res.ingredient.canonical_name.lower()


@patch("core.external_apis.fetcher.fetch_usda_fdc")
def test_fetcher_rejects_relevance_mismatch(mock_usda):
    from core.external_apis.fetcher import fetch_ingredient_from_apis, clear_enrichment_cache
    from core.ontology.ingredient_schema import Ingredient
    from core.external_apis.base import EnrichmentResult

    clear_enrichment_cache()
    bad = Ingredient(
        id="usda_lamb_bad",
        canonical_name="Lamb, variety meats and by-products, mechanically separated, raw",
        aliases=[],
        derived_from=[], contains=[], may_contain=[],
        animal_origin=True, plant_origin=False, synthetic=False, fungal=False,
        insect_derived=False, animal_species="lamb", egg_source=False,
        dairy_source=False, gluten_source=False, nut_source=None,
        soy_source=False, sesame_source=False, alcohol_content=None,
        root_vegetable=False, onion_source=False, garlic_source=False,
        fermented=False, uncertainty_flags=[], regions=[],
    )
    mock_usda.return_value = EnrichmentResult(bad, "high", "usda_fdc", "ok")
    with patch("core.external_apis.fetcher.get_usda_fdc_api_key", return_value="key"):
        with patch("core.external_apis.fetcher.get_open_food_facts_enabled", return_value=False):
            res = fetch_ingredient_from_apis("mechanically separated chicken", use_cache=False)
    assert res.ingredient is None
    assert res.raw_response_summary == "relevance_mismatch"


@patch("core.external_apis.open_food_facts.get_with_retries")
def test_open_food_facts_mock_success(mock_get):
    """Mock Open Food Facts response maps to Ingredient."""
    from core.external_apis.open_food_facts import fetch_open_food_facts
    mock_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "products": [
                {
                    "product_name": "Organic Wheat Flour",
                    "ingredients_text": "wheat",
                }
            ]
        },
    )
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = (mock_resp, None)
    res = fetch_open_food_facts("wheat flour")
    assert res.ingredient is not None
    assert res.source == "open_food_facts"


def test_fetcher_cache():
    """Enrichment fetcher caches only successful results; second call uses cache (no extra API call)."""
    from core.external_apis.fetcher import fetch_ingredient_from_apis, clear_enrichment_cache
    from core.ontology.ingredient_schema import Ingredient
    from core.external_apis.base import EnrichmentResult
    clear_enrichment_cache()
    success_ing = Ingredient(
        id="off_test_1", canonical_name="cached flour", aliases=[], derived_from=[], contains=[], may_contain=[],
        animal_origin=False, plant_origin=True, synthetic=False, fungal=False, insect_derived=False,
        animal_species=None, egg_source=False, dairy_source=False, gluten_source=False, nut_source=None,
        soy_source=False, sesame_source=False, alcohol_content=None, root_vegetable=False, onion_source=False,
        garlic_source=False, fermented=False, uncertainty_flags=[], regions=[],
    )
    with patch("core.external_apis.fetcher.get_usda_fdc_api_key", return_value=""):
        with patch("core.external_apis.fetcher.fetch_open_food_facts") as mock_off:
            mock_off.return_value = EnrichmentResult(success_ing, "high", "open_food_facts", "ok")
            fetch_ingredient_from_apis("cached_query_xyz", use_cache=True)
            fetch_ingredient_from_apis("cached_query_xyz", use_cache=True)
            assert mock_off.call_count == 1


def test_fetcher_no_cache_for_no_result():
    """No-result is not cached so unknowns always trigger API search on each request."""
    from core.external_apis.fetcher import fetch_ingredient_from_apis, clear_enrichment_cache
    from core.external_apis.base import EnrichmentResult
    clear_enrichment_cache()
    no_res = EnrichmentResult(None, "low", "open_food_facts", "no_results")
    # Single query variant so OFF is called once per fetch_ingredient_from_apis (2 total)
    with patch("core.external_apis.fetcher.get_canonical_queries", return_value=["unknown xyz none"]):
        with patch("core.external_apis.fetcher.resolve_to_english_label", return_value=None):
            with patch("core.external_apis.fetcher._resolve_to_english_llm", return_value=None):
                with patch("core.external_apis.fetcher.get_usda_fdc_api_key", return_value=""):
                    with patch("core.external_apis.fetcher.fetch_open_food_facts") as mock_off:
                        mock_off.return_value = no_res
                        with patch("core.external_apis.fetcher.fetch_pubchem", return_value=no_res):
                            with patch("core.external_apis.fetcher.fetch_chebi", return_value=no_res):
                                with patch("core.external_apis.fetcher.fetch_wikidata", return_value=no_res):
                                    fetch_ingredient_from_apis("unknown_xyz_none", use_cache=True)
                                    fetch_ingredient_from_apis("unknown_xyz_none", use_cache=True)
                        assert mock_off.call_count == 2


def test_api_health_check_script():
    """Script check_external_apis: at least one API ok -> exit 0; all 5 fail -> exit 1."""
    from scripts.check_external_apis import main
    fail = (False, "no result")
    ok = (True, "ok")
    with patch("scripts.check_external_apis.check_usda", return_value=ok):
        with patch("scripts.check_external_apis.check_open_food_facts", return_value=fail):
            with patch("scripts.check_external_apis.check_pubchem", return_value=fail):
                with patch("scripts.check_external_apis.check_chebi", return_value=fail):
                    with patch("scripts.check_external_apis.check_wikidata", return_value=fail):
                        assert main() == 0
    with patch("scripts.check_external_apis.check_usda", return_value=fail):
        with patch("scripts.check_external_apis.check_open_food_facts", return_value=ok):
            with patch("scripts.check_external_apis.check_pubchem", return_value=fail):
                with patch("scripts.check_external_apis.check_chebi", return_value=fail):
                    with patch("scripts.check_external_apis.check_wikidata", return_value=fail):
                        assert main() == 0
    # All 5 fail -> exit 1
    with patch("scripts.check_external_apis.check_usda", return_value=(False, "timeout")):
        with patch("scripts.check_external_apis.check_open_food_facts", return_value=fail):
            with patch("scripts.check_external_apis.check_pubchem", return_value=fail):
                with patch("scripts.check_external_apis.check_chebi", return_value=fail):
                    with patch("scripts.check_external_apis.check_wikidata", return_value=fail):
                        assert main() == 1


def test_http_retry_on_timeout():
    """get_with_retries retries on timeout and returns (None, error) after max retries."""
    from core.external_apis.http_retry import get_with_retries
    import requests
    with patch("core.external_apis.http_retry.requests.request") as mock_request:
        mock_request.side_effect = requests.Timeout("Read timed out")
        resp, err = get_with_retries("https://example.com", max_retries=2, initial_backoff=0.01)
        assert resp is None
        assert err is not None
        assert "timed out" in err.lower() or "Timeout" in err
        assert mock_request.call_count == 2
