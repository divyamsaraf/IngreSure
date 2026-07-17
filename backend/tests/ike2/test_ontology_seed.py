"""Tests for ontology -> IKE-2 bulk inject (Phase 2)."""
import json
from pathlib import Path

import pytest

from core.knowledge.ike2.etl.bulk_inject import inject
from core.knowledge.ike2.etl.load_ontology import load_ontology_records
from tests.ike2.test_etl_bulk_inject import FakeWriter

ONTOLOGY = Path(__file__).resolve().parents[3] / "data" / "ontology.json"


@pytest.mark.skipif(not ONTOLOGY.is_file(), reason="ontology.json missing")
def test_load_ontology_records_includes_staples():
    records = load_ontology_records(ONTOLOGY)
    names = {r["canonical_name"] for r in records}
    assert "water" in names
    assert "niacin" in names
    assert len(records) >= 500


def test_inject_insect_derived_sets_animal_origin():
    sample = [
        {
            "canonical_name": "carmine",
            "aliases": [],
            "insect_derived": True,
            "regions": [],
        },
    ]
    w = FakeWriter()
    stats = inject(sample, "ontology", w)
    assert stats.rejected == 0
    assert w.get_group("carmine")["animal_origin"] is True


def test_inject_ontology_sample_via_fake_writer():
    sample = [
        {
            "canonical_name": "niacin",
            "aliases": ["vitamin b3"],
            "plant_origin": False,
            "synthetic": True,
            "regions": [],
        },
        {
            "canonical_name": "extra virgin olive oil",
            "aliases": ["olive oil"],
            "plant_origin": True,
            "regions": [],
        },
    ]
    w = FakeWriter()
    stats = inject(sample, "ontology", w)
    assert stats.inserted == 2
    assert stats.rejected == 0
    assert w.get_group("niacin") is not None
    assert w.get_group("extra virgin olive oil")["plant_origin"] is True


@pytest.mark.skipif(not ONTOLOGY.is_file(), reason="ontology.json missing")
def test_inject_real_ontology_water_is_idempotent():
    records = [r for r in load_ontology_records(ONTOLOGY) if r["canonical_name"] == "water"]
    assert len(records) == 1
    w = FakeWriter()
    first = inject(records, "ontology", w)
    second = inject(records, "ontology", w)
    assert first.inserted == 1
    assert second.inserted == 0
    assert second.updated == 1
