"""Item 1 Prompt 6: animal_catalog SourceAdapter + seed dry-run."""
from __future__ import annotations

import json
from pathlib import Path

from core.knowledge.ike2.etl.adapt import map_record
from core.knowledge.ike2.etl.adapters import SourceAdapter, emit_layer1_records
from core.knowledge.ike2.etl.adapters.animal import AnimalCatalogAdapter
from core.knowledge.ike2.etl.bulk_inject import inject, load_dump
from core.knowledge.ike2.etl.reconcile import _SOURCE_TIER, _tier
from core.knowledge.ike2.etl.sources import default_knowledge_state
from core.knowledge.ike2.etl.validate import validate_rows
from tests.ike2.test_etl_bulk_inject import FakeWriter

_REPO = Path(__file__).resolve().parents[2].parent
_LAYER1 = _REPO / "data" / "layer1_animal_catalog.json"
_SEED = (
    Path(__file__).resolve().parents[2]
    / "core"
    / "knowledge"
    / "ike2"
    / "etl"
    / "adapters"
    / "seeds"
    / "animal_catalog_seed.json"
)


def test_animal_adapter_is_source_adapter():
    assert isinstance(AnimalCatalogAdapter(), SourceAdapter)


def test_animal_adapter_license_ok_for_cc0():
    assert AnimalCatalogAdapter().license_ok() is True


def test_animal_seed_emits_animal_origin_and_species():
    rows = emit_layer1_records(AnimalCatalogAdapter(seed_path=_SEED))
    assert len(rows) >= 5
    by_name = {r["canonical_name"]: r for r in rows}

    milk = by_name["milk"]
    assert milk["animal_origin"] is True
    assert milk["dairy_source"] is True
    assert milk.get("animal_species") == "mammal"

    egg = by_name["egg"]
    assert egg["animal_origin"] is True
    assert egg["egg_source"] is True
    assert egg.get("animal_species") == "bird"

    salmon = by_name["salmon"]
    assert salmon["animal_origin"] is True
    assert salmon["fish_source"] is True
    assert salmon.get("animal_species") == "fish"

    shrimp = by_name["shrimp"]
    assert shrimp["animal_origin"] is True
    assert shrimp["shellfish_source"] is True

    chicken = by_name["chicken"]
    assert chicken["animal_origin"] is True
    assert chicken.get("animal_species") == "bird"
    assert chicken.get("plant_origin") is not True


def test_animal_records_pass_validate_and_land_discovered():
    adapter = AnimalCatalogAdapter(seed_path=_SEED)
    raw_rows = emit_layer1_records(adapter)
    mapped = []
    for raw in raw_rows:
        row, _aliases = map_record(
            raw, adapter.name, default_knowledge_state(adapter.name)
        )
        mapped.append(row)
    ok, rejects = validate_rows(mapped)
    assert rejects == []
    assert len(ok) == len(raw_rows)
    assert all(r["knowledge_state"] == "DISCOVERED" for r in ok)
    assert all(r["classification_method"] == "bulk:animal_catalog" for r in ok)
    # Implication closure: dairy/egg/fish/shellfish ⇒ animal_origin
    for r in ok:
        if any(
            r.get(f)
            for f in (
                "dairy_source",
                "egg_source",
                "fish_source",
                "shellfish_source",
                "bee_product",
            )
        ):
            assert r["animal_origin"] is True, r["canonical_name"]


def test_animal_catalog_registered_discovered_tier2():
    assert default_knowledge_state("animal_catalog") == "DISCOVERED"
    assert _tier("animal_catalog") == 2
    assert "animal_catalog" in _SOURCE_TIER


def test_layer1_animal_catalog_dry_run_inject_zero_rejects():
    assert _LAYER1.is_file(), "emit layer1_animal_catalog.json from animal adapter seed"
    source, records = load_dump(str(_LAYER1))
    assert source is None
    assert len(records) >= 5
    w = FakeWriter()
    stats = inject(records, "animal_catalog", w)
    assert stats.rejected == 0
    assert stats.inserted == len(records)
    sample = next(iter(w.groups.values()))
    assert sample["animal_origin"] is True
    assert sample["knowledge_state"] == "DISCOVERED"


def test_layer1_animal_matches_adapter_emission():
    adapter_rows = emit_layer1_records(AnimalCatalogAdapter(seed_path=_SEED))
    dump = json.loads(_LAYER1.read_text(encoding="utf-8"))
    assert [r["canonical_name"] for r in dump] == [
        r["canonical_name"] for r in adapter_rows
    ]
