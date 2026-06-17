from core.knowledge.ike2.etl.sources import (
    canonical_source,
    default_knowledge_state,
)


def test_dump_source_names_canonicalize():
    assert canonical_source("open_food_facts") == "openfoodfacts"
    assert canonical_source("usda_fdc") == "usda"
    assert canonical_source("WIKIDATA") == "wikidata"


def test_unknown_source_passes_through_lowercased():
    assert canonical_source("Some-New-Source") == "some-new-source"


def test_default_state_reflects_trust_tier():
    # curated / regulatory bulk lands auto-classified
    assert default_knowledge_state("usda") == "AUTO_CLASSIFIED"
    # crowd / low-trust bulk lands as merely discovered (cannot drive a verdict
    # until promoted), never VERIFIED
    assert default_knowledge_state("openfoodfacts") == "DISCOVERED"
    assert default_knowledge_state("wikidata") == "DISCOVERED"
    # totally unknown source is the most conservative
    assert default_knowledge_state("mystery") == "UNCLASSIFIED"
