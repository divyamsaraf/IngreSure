"""
Unit tests for enrichment: unknown log, dynamic ontology.
Run from backend: python -m pytest tests/test_enrichment.py -v
"""
import json
import tempfile
import pytest
from pathlib import Path


def test_unknown_log_record_and_save():
    """Unknown ingredients log records and persists."""
    from core.enrichment.unknown_log import UnknownIngredientsLog
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "unknowns.json"
        log = UnknownIngredientsLog(path=path)
        log.record("Wheat Flour", "wheat flour", restriction_ids=["vegan"], persist=True)
        log.record("Wheat Flour", "wheat flour", persist=True)
        entries = log.get_entries()
        assert "wheat flour" in entries
        assert entries["wheat flour"]["frequency"] == 2
        assert path.exists()
        data = json.loads(path.read_text())
        assert "unknown_ingredients" in data


def test_unknown_log_keys_for_enrichment():
    """get_keys_for_enrichment returns keys above min_frequency."""
    from core.enrichment.unknown_log import UnknownIngredientsLog
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "unknowns.json"
        log = UnknownIngredientsLog(path=path)
        log.record("a", "a", persist=True)
        log.record("a", "a", persist=True)
        log.record("b", "b", persist=True)
        keys = log.get_keys_for_enrichment(min_frequency=2)
        assert "a" in keys
        assert "b" not in keys


def test_dynamic_ontology_append():
    """Dynamic ontology appends ingredient with source/confidence."""
    from core.enrichment.dynamic_ontology import DynamicOntology
    from core.ontology.ingredient_schema import Ingredient
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "dynamic_ontology.json"
        dyn = DynamicOntology(path=path)
        ing = Ingredient(
            id="test_custom_1",
            canonical_name="custom flour",
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
            gluten_source=True,
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
        dyn.append(ing, source="test", confidence="high", persist=True)
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data["ingredients"]) == 1
        assert data["ingredients"][0]["canonical_name"] == "custom flour"
        assert data["ingredients"][0].get("_enrichment_source") == "test"


def test_dynamic_ontology_dedupe_by_id():
    """Appending same id again does not duplicate."""
    from core.enrichment.dynamic_ontology import DynamicOntology
    from core.ontology.ingredient_schema import Ingredient
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "dynamic_ontology.json"
        dyn = DynamicOntology(path=path)
        ing = Ingredient(
            id="dedupe_id",
            canonical_name="one",
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
        dyn.append(ing, source="test", confidence="high", persist=True)
        dyn.append(ing, source="test", confidence="high", persist=True)
        data = json.loads(path.read_text())
        assert len(data["ingredients"]) == 1
