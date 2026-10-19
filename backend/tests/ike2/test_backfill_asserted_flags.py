"""Item 11 §5 / §8.4: true-only asserted_flags backfill."""
from core.knowledge.ike2.etl.backfill_asserted_flags import (
    backfill_asserted_flags_on_row,
    backfill_ontology_ingredients,
)


def test_true_only_backfill_marks_trues_not_falses():
    row = {
        "canonical_name": "gelatin",
        "animal_origin": True,
        "dairy_source": False,
        "synthetic": False,
    }
    out = backfill_asserted_flags_on_row(row)
    assert out["asserted_flags"] == ["animal_origin"]
    assert "dairy_source" not in out["asserted_flags"]
    assert "synthetic" not in out["asserted_flags"]


def test_true_only_backfill_reads_nested_flags():
    row = {
        "canonical_name": "broccoli",
        "flags": {"plant_origin": True, "animal_origin": False},
        "plant_origin": True,
    }
    out = backfill_asserted_flags_on_row(row)
    assert out["asserted_flags"] == ["plant_origin"]


def test_true_only_backfill_idempotent():
    row = {"canonical_name": "x", "plant_origin": True, "synthetic": False}
    once = backfill_asserted_flags_on_row(row)
    twice = backfill_asserted_flags_on_row(once)
    assert once["asserted_flags"] == twice["asserted_flags"] == ["plant_origin"]


def test_true_only_backfill_preserves_prior_asserted_including_false():
    """Forward writers may assert a false; backfill must not strip that."""
    row = {
        "canonical_name": "x",
        "synthetic": False,
        "plant_origin": True,
        "asserted_flags": ["synthetic"],
    }
    out = backfill_asserted_flags_on_row(row)
    assert out["asserted_flags"] == ["plant_origin", "synthetic"]


def test_backfill_ontology_ingredients_batch():
    rows = [
        {"canonical_name": "a", "plant_origin": True},
        {"canonical_name": "b", "animal_origin": False},
    ]
    out = backfill_ontology_ingredients(rows)
    assert out[0]["asserted_flags"] == ["plant_origin"]
    assert out[1]["asserted_flags"] == []
