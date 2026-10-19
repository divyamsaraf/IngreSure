"""Asserted false legal only on reviewed-negatives registry; post-reconcile too."""
from types import SimpleNamespace

from core.knowledge.ike2.etl.reconcile import reconcile
from core.knowledge.ike2.etl.validate import merged_row_for_validate, validate_rows
from core.knowledge.ike2.reviewed_negatives import asserted_false_allowed


def test_registry_includes_frozen_usda_clear():
    assert asserted_false_allowed("butter without salt", "egg_source")


def test_unreviewed_asserted_false_quarantined():
    row = {
        "canonical_name": "mystery dairy",
        "animal_origin": True,
        "dairy_source": True,
        "egg_source": False,
        "asserted_flags": ["animal_origin", "dairy_source", "egg_source"],
    }
    ok, rejects = validate_rows([row])
    assert ok == []
    assert rejects[0]["violated_constraint"] == "asserted_flags_unreviewed_negative"


def test_merged_after_reconcile_rejects_stale_unreviewed_false():
    """Sticky union of asserted keys must not write unreviewed negatives."""
    existing = {
        "canonical_name": "ghee",
        "id": "x",
        "animal_origin": True,
        "dairy_source": True,
        "plant_origin": False,
        "egg_source": False,
        "fish_source": False,
        "shellfish_source": False,
        "synthetic": False,
        "asserted_flags": [
            "animal_origin",
            "dairy_source",
            "egg_source",
            "fish_source",
            "shellfish_source",
            "synthetic",
        ],
        "knowledge_state": "AUTO_CLASSIFIED",
        "source": "ontology",
    }
    incoming = {
        "animal_origin": True,
        "dairy_source": True,
        "plant_origin": False,
        "egg_source": False,
        "fish_source": False,
        "shellfish_source": False,
        "synthetic": False,
    }
    result = reconcile(
        SimpleNamespace(**existing),
        incoming,
        "ontology",
        incoming_asserted=["animal_origin", "dairy_source"],
        incoming_knowledge_state="AUTO_CLASSIFIED",
    )
    merged = merged_row_for_validate(existing, result)
    ok, rejects = validate_rows([merged])
    assert ok == []
    assert rejects[0]["violated_constraint"] == "asserted_flags_unreviewed_negative"
