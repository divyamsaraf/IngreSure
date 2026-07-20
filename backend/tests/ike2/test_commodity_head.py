"""Commodity-head extraction + Tier-2 auto-index (coverage productization)."""
from core.knowledge.ike2.commodity_head import simple_commodity_head
from core.knowledge.ike2.resolution_cache import clear
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.stores import local_ontology


def test_simple_head_from_usda_style_name():
    assert simple_commodity_head("Broccoli, raw") == "broccoli"
    assert simple_commodity_head("Spices, cumin seed") == "cumin seed"


def test_normalized_space_prep_form_extracts_head():
    # Key-normalize strips commas; head extraction must still work.
    assert simple_commodity_head("broccoli raw") == "broccoli"
    assert simple_commodity_head("cabbage bok choy raw") == "cabbage bok choy"


def test_multi_comma_name_is_not_auto_headed():
    # Would wrongly become "cabbage" if we naively split on first comma.
    assert simple_commodity_head("Cabbage, bok choy, raw") is None


def test_tier2_indexes_auto_head_from_dump_style_canonical(monkeypatch):
    rows = [
        {
            "canonical_name": "broccolini, raw",
            "aliases": [],
            "plant_origin": True,
            "animal_origin": False,
            "knowledge_state": "AUTO_CLASSIFIED",
        }
    ]
    monkeypatch.setattr(local_ontology, "load_ontology_records", lambda path=None: rows)
    local_ontology.reset_cache()
    clear()
    try:
        assert local_ontology.lookup("broccolini") is not None
        assert local_ontology.lookup("broccolini, raw") is not None
        assert local_ontology.lookup("broccolini raw") is not None
    finally:
        local_ontology.reset_cache()
        clear()


def test_auto_head_never_overwrites_canonical(monkeypatch):
    """Canonical ownership wins: dump-style head must not steal an existing key."""
    rows = [
        {
            "canonical_name": "amaranth",
            "aliases": [],
            "plant_origin": True,
            "animal_origin": False,
            "knowledge_state": "AUTO_CLASSIFIED",
        },
        {
            "canonical_name": "amaranth, raw",
            "aliases": [],
            "plant_origin": True,
            "animal_origin": False,
            "animal_species": "fish",  # deliberately wrong — must not win the key
            "knowledge_state": "AUTO_CLASSIFIED",
        },
    ]
    monkeypatch.setattr(local_ontology, "load_ontology_records", lambda path=None: rows)
    local_ontology.reset_cache()
    clear()
    try:
        hit = local_ontology.lookup("amaranth")
        assert hit is not None
        assert hit.canonical_name == "amaranth"
        assert hit.flags.get("animal_species") != "fish"
    finally:
        local_ontology.reset_cache()
        clear()


def test_resolver_retries_dump_style_query_as_head(monkeypatch):
    """Normalized 'X raw' still resolves when only short head is indexed."""
    rows = [
        {
            "canonical_name": "romanesco",
            "aliases": [],
            "plant_origin": True,
            "animal_origin": False,
            "knowledge_state": "AUTO_CLASSIFIED",
        }
    ]
    monkeypatch.setattr(local_ontology, "load_ontology_records", lambda path=None: rows)
    monkeypatch.setattr("core.knowledge.ike2.truth_anchor.lookup", lambda _k: None)
    monkeypatch.setattr("core.knowledge.ike2.stores.db.disambiguate", lambda *_a, **_k: None)
    monkeypatch.setattr("core.knowledge.ike2.stores.db.resolve_alias", lambda *_a, **_k: None)
    local_ontology.reset_cache()
    clear()
    try:
        r = resolve("Romanesco, raw", None)
        assert r.status == "resolved"
        assert r.group.canonical_name == "romanesco"
    finally:
        local_ontology.reset_cache()
        clear()
