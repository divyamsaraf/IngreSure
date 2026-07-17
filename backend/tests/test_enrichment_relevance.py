"""Pattern-class tests for enrichment relevance (species mismatch guards)."""
from core.external_apis.enrichment_relevance import (
    enrichment_species_mismatch,
    score_usda_candidate,
    species_groups_in_text,
)


def test_species_groups_chicken_query():
    assert "poultry" in species_groups_in_text("mechanically separated chicken")


def test_species_groups_lamb_result():
    assert "lamb" in species_groups_in_text(
        "Lamb, variety meats and by-products, mechanically separated, raw"
    )


def test_chicken_lamb_is_species_mismatch():
    assert enrichment_species_mismatch(
        "mechanically separated chicken",
        "Lamb, variety meats and by-products, mechanically separated, raw",
    )


def test_pork_pork_not_mismatch():
    assert not enrichment_species_mismatch("pork", "Pork, fresh, variety meats and by-products")


def test_flour_has_no_species_groups():
    assert species_groups_in_text("wheat flour") == frozenset()


def test_usda_score_prefers_matching_species():
    lamb = "Lamb, variety meats and by-products, mechanically separated, raw"
    chicken = "Chicken, mechanically separated, raw"
    query = "mechanically separated chicken"
    assert score_usda_candidate(query, lamb) < 0
    assert score_usda_candidate(query, chicken) > score_usda_candidate(query, lamb)
