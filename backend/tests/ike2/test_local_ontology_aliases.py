"""Tier-2 local ontology indexes aliases so short chat names resolve."""
from core.knowledge.ike2.stores import local_ontology


def test_local_ontology_resolves_alias_and_short_name(monkeypatch):
    rows = [
        {
            "canonical_name": "broccoli",
            "aliases": ["Broccoli, raw", "broccolis"],
            "plant_origin": True,
            "animal_origin": False,
            "knowledge_state": "AUTO_CLASSIFIED",
        }
    ]
    monkeypatch.setattr(
        local_ontology,
        "load_ontology_records",
        lambda path=None: rows,
    )
    local_ontology.reset_cache()
    try:
        assert local_ontology.lookup("broccoli") is not None
        assert local_ontology.lookup("Broccoli, raw") is not None
        assert local_ontology.lookup("broccolis") is not None
        fact = local_ontology.lookup("broccoli")
        assert fact.flags.get("plant_origin") is True
    finally:
        # Drop the monkeypatched index so later tests see the real ontology.
        local_ontology.reset_cache()
