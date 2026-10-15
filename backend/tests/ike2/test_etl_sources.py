"""Item 1 Prompt 2: source registry completeness for all in-repo Layer-1 labels."""
from core.knowledge.ike2.etl.reconcile import _SOURCE_TIER, _tier
from core.knowledge.ike2.etl.sources import (
    _DEFAULT_STATE,
    canonical_source,
    default_knowledge_state,
)

# Every Layer-1 dump label (or CLI --source) that must have explicit tier + state.
_LAYER1_LABELS = (
    "open_food_facts",
    "usda_fdc",
    "fda_gras",
    "fssai",
    "chebi",
    "wikidata",
    "nin",
    "ifct",
    "foodex2",
    "pubchem",
    "e_number_catalog",
    "ontology",
    "produce_catalog",
)


def test_dump_source_names_canonicalize():
    assert canonical_source("open_food_facts") == "openfoodfacts"
    assert canonical_source("usda_fdc") == "usda"
    assert canonical_source("WIKIDATA") == "wikidata"
    assert canonical_source("fda_gras") == "fda"


def test_unknown_source_passes_through_lowercased():
    assert canonical_source("Some-New-Source") == "some-new-source"


def test_default_state_reflects_trust_tier():
    assert default_knowledge_state("usda") == "AUTO_CLASSIFIED"
    assert default_knowledge_state("openfoodfacts") == "DISCOVERED"
    assert default_knowledge_state("wikidata") == "DISCOVERED"
    assert default_knowledge_state("mystery") == "UNCLASSIFIED"
    assert default_knowledge_state("e_number_catalog") == "LOCKED"
    assert default_knowledge_state("nin") == "AUTO_CLASSIFIED"
    assert default_knowledge_state("pubchem") == "DISCOVERED"
    assert default_knowledge_state("produce_catalog") == "AUTO_CLASSIFIED"
    assert default_knowledge_state("animal_catalog") == "DISCOVERED"


def test_every_layer1_source_has_explicit_tier_and_default_state():
    for label in _LAYER1_LABELS:
        canon = canonical_source(label)
        assert canon in _DEFAULT_STATE, f"{label} → {canon} missing _DEFAULT_STATE"
        assert canon in _SOURCE_TIER, f"{label} → {canon} missing _SOURCE_TIER"
        assert default_knowledge_state(canon) != "UNCLASSIFIED"
        assert default_knowledge_state(canon) != "VERIFIED"
        assert _tier(canon) > 0, f"{canon} must not fall through to tier 0"


def test_e_number_catalog_tier_beats_crowd_sources():
    assert _tier("e_number_catalog") > _tier("openfoodfacts")
    assert _tier("e_number_catalog") > _tier("wikidata")


def test_animal_catalog_more_conservative_than_produce():
    """Item 1.2 check-in: DISCOVERED/tier2 vs produce AUTO/tier3."""
    assert default_knowledge_state("animal_catalog") == "DISCOVERED"
    assert default_knowledge_state("produce_catalog") == "AUTO_CLASSIFIED"
    assert _tier("animal_catalog") == 2
    assert _tier("produce_catalog") == 3
    assert _tier("animal_catalog") == _tier("foodex2")
    assert "animal_catalog" in _SOURCE_TIER
    assert "animal_catalog" in _DEFAULT_STATE
