"""Pattern-class L: external enrichment relevance (species, plant/animal, scoring).

Extends universal label pipeline spec classes A–K with enrichment guards.
"""
from __future__ import annotations

import pytest

from core.external_apis.enrichment_relevance import (
    enrichment_plant_animal_mismatch,
    enrichment_species_mismatch,
    is_enrichment_relevant,
    score_enrichment_candidate,
)

# --- L1: exclusive meat species mismatch ---
SPECIES_MISMATCH_CASES = [
    ("mechanically separated chicken", "Lamb, variety meats and by-products, mechanically separated, raw"),
    ("chicken breast", "Beef, ground, 85% lean meat / 15% fat, raw"),
    ("pork sausage", "Lamb, fresh, leg, whole"),
    ("beef base", "Pork, fresh, variety meats and by-products, liver, raw"),
    ("turkey breast", "Chicken, broilers or fryers, breast, meat only, raw"),
    ("salmon fillet", "Shrimp, raw"),
]

SPECIES_MATCH_CASES = [
    ("mechanically separated chicken", "Chicken, mechanically separated, raw"),
    ("pork", "Pork, fresh, variety meats and by-products"),
    ("beef base", "Beef flavor base, paste"),
    ("wheat flour", "Wheat flour, white, all-purpose, enriched"),
]


@pytest.mark.parametrize("query,candidate", SPECIES_MISMATCH_CASES)
def test_species_mismatch_pattern_class(query: str, candidate: str):
    assert enrichment_species_mismatch(query, candidate)
    assert not is_enrichment_relevant(query, candidate)


@pytest.mark.parametrize("query,candidate", SPECIES_MATCH_CASES)
def test_species_match_pattern_class(query: str, candidate: str):
    assert not enrichment_species_mismatch(query, candidate)
    assert is_enrichment_relevant(query, candidate)


# --- L2: plant-named query vs animal API hit ---
PLANT_ANIMAL_MISMATCH_CASES = [
    ("coconut milk", "Milk, whole, 3.25% milkfat"),
    ("almond milk", "Milk, evaporated, canned"),
    ("peanut butter", "Butter, without salt"),
    ("soy milk", "Milk, lowfat, fluid, 1% milkfat"),
]


@pytest.mark.parametrize("query,candidate", PLANT_ANIMAL_MISMATCH_CASES)
def test_plant_query_animal_candidate_rejected(query: str, candidate: str):
    assert enrichment_plant_animal_mismatch(query, candidate)
    assert not is_enrichment_relevant(query, candidate)


def test_plant_query_plant_candidate_allowed():
    assert is_enrichment_relevant("coconut milk", "Coconut milk, canned")
    assert not enrichment_plant_animal_mismatch("coconut milk", "Coconut milk, canned")


# --- L3: shared process terms must not override species ---
def test_shared_process_term_does_not_force_match():
    query = "mechanically separated chicken"
    lamb = "Lamb, variety meats and by-products, mechanically separated, raw"
    chicken = "Chicken, mechanically separated, raw"
    assert score_enrichment_candidate(query, lamb) < 0
    assert score_enrichment_candidate(query, chicken) > score_enrichment_candidate(query, lamb)


# --- L4: no species in query → no species rejection ---
def test_no_species_in_query_allows_candidate():
    assert not enrichment_species_mismatch("flavorings", "Natural flavor, beef type")
    assert is_enrichment_relevant("flavorings", "Natural flavor, beef type")


# --- L5: chemical/non-meat queries skip species guard ---
def test_chemical_query_not_species_blocked():
    assert is_enrichment_relevant("sodium bicarbonate", "Leavening agents, baking soda")
    assert is_enrichment_relevant("propylene glycol", "Propylene glycol")
