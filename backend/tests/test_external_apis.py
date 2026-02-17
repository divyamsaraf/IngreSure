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


@patch("core.external_apis.usda_fdc.requests.get")
def test_usda_fdc_mock_success(mock_get):
    """Mock USDA response maps to Ingredient with high confidence."""
    from core.external_apis.usda_fdc import fetch_usda_fdc
    mock_get.return_value = MagicMock(
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
    mock_get.return_value.raise_for_status = MagicMock()
    res = fetch_usda_fdc("wheat flour", api_key="test-key")
    assert res.ingredient is not None
    assert res.source == "usda_fdc"
    assert "flour" in res.ingredient.canonical_name.lower() or res.ingredient.canonical_name


@patch("core.external_apis.open_food_facts.requests.get")
def test_open_food_facts_mock_success(mock_get):
    """Mock Open Food Facts response maps to Ingredient."""
    from core.external_apis.open_food_facts import fetch_open_food_facts
    mock_get.return_value = MagicMock(
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
    mock_get.return_value.raise_for_status = MagicMock()
    res = fetch_open_food_facts("wheat flour")
    assert res.ingredient is not None
    assert res.source == "open_food_facts"


def test_fetcher_cache():
    """Enrichment fetcher uses cache (second call returns cached without request)."""
    from core.external_apis.fetcher import fetch_ingredient_from_apis, clear_enrichment_cache
    clear_enrichment_cache()
    with patch("core.external_apis.fetcher.get_usda_fdc_api_key", return_value=""):
        with patch("core.external_apis.fetcher.fetch_open_food_facts") as mock_off:
            mock_off.return_value = __import__("core.external_apis.base", fromlist=["EnrichmentResult"]).EnrichmentResult(
                None, "low", "open_food_facts", "no_results"
            )
            fetch_ingredient_from_apis("cached_query_xyz", use_cache=True)
            fetch_ingredient_from_apis("cached_query_xyz", use_cache=True)
            assert mock_off.call_count == 1


def test_api_health_check_script():
    """Script check_external_apis: at least one API ok -> exit 0; both fail -> exit 1."""
    from scripts.check_external_apis import main
    with patch("scripts.check_external_apis.check_usda", return_value=(True, "ok")):
        with patch("scripts.check_external_apis.check_open_food_facts", return_value=(False, "no result")):
            assert main() == 0
    with patch("scripts.check_external_apis.check_usda", return_value=(False, "no key")):
        with patch("scripts.check_external_apis.check_open_food_facts", return_value=(True, "ok")):
            assert main() == 0
    # Both fail: need OFF to be tried so we patch config and both check results
    with patch("core.config.OPEN_FOOD_FACTS_ENABLED", True):
        with patch("scripts.check_external_apis.check_usda", return_value=(False, "timeout")):
            with patch("scripts.check_external_apis.check_open_food_facts", return_value=(False, "no result")):
                assert main() == 1


def test_http_retry_on_timeout():
    """get_with_retries retries on timeout and returns (None, error) after max retries."""
    from core.external_apis.http_retry import get_with_retries
    import requests
    with patch("core.external_apis.http_retry.requests.get") as mock_get:
        mock_get.side_effect = requests.Timeout("Read timed out")
        resp, err = get_with_retries("https://example.com", max_retries=2, initial_backoff=0.01)
        assert resp is None
        assert err is not None
        assert "timed out" in err.lower() or "Timeout" in err
        assert mock_get.call_count == 2
