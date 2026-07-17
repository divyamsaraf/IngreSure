"""Registry + display guards for enrichment species mismatch."""
from unittest.mock import patch

from core.external_apis.base import EnrichmentResult
from core.external_apis.enrichment_relevance import enrichment_species_mismatch
from core.response_composer import format_audit_item_name


def test_format_audit_item_name_hides_mismatched_canonical():
    raw = "mechanically separated chicken"
    canon = "Lamb, variety meats and by-products, mechanically separated, raw"
    assert enrichment_species_mismatch(raw, canon)
    display = format_audit_item_name(raw, canon)
    assert "lamb" not in display.lower()
    assert "chicken" in display.lower()
    assert "·" not in display


def test_registry_rejects_stored_dynamic_species_mismatch():
    from core.ontology.ingredient_registry import IngredientRegistry
    from pathlib import Path
    import tempfile
    import json

    bad = {
        "ingredients": [
            {
                "id": "usda_lamb_test",
                "canonical_name": "Lamb, variety meats and by-products, mechanically separated, raw",
                "aliases": ["mechanically separated chicken"],
                "derived_from": [],
                "contains": [],
                "may_contain": [],
                "animal_origin": True,
                "plant_origin": False,
                "synthetic": False,
                "fungal": False,
                "insect_derived": False,
                "animal_species": "lamb",
                "egg_source": False,
                "dairy_source": False,
                "gluten_source": False,
                "nut_source": None,
                "soy_source": False,
                "sesame_source": False,
                "alcohol_content": None,
                "root_vegetable": False,
                "onion_source": False,
                "garlic_source": False,
                "fermented": False,
                "uncertainty_flags": [],
                "regions": [],
            }
        ]
    }
    with tempfile.TemporaryDirectory() as tmp:
        dyn_path = Path(tmp) / "dynamic.json"
        dyn_path.write_text(json.dumps(bad), encoding="utf-8")
        reg = IngredientRegistry(
            ontology_path=Path("/nonexistent/ontology.json"),
            dynamic_ontology_path=dyn_path,
            load_dynamic=True,
        )
        with patch(
            "core.external_apis.fetcher.enrich_unknown_ingredient",
            return_value=EnrichmentResult(None, "low", "usda_fdc", "no_results"),
        ):
            ing, source, level = reg.resolve_with_fallback(
                "mechanically separated chicken",
                try_api=True,
                log_unknown=False,
            )
        assert ing is None
        assert level == "low"
