"""Item 1 Prompt 5: produce_catalog SourceAdapter + seed dry-run."""
from __future__ import annotations

import json
from pathlib import Path

from core.knowledge.ike2.etl.adapt import map_record
from core.knowledge.ike2.etl.adapters import SourceAdapter, emit_layer1_records
from core.knowledge.ike2.etl.adapters.produce import ProduceCatalogAdapter
from core.knowledge.ike2.etl.bulk_inject import inject, load_dump
from core.knowledge.ike2.etl.reconcile import _SOURCE_TIER, _tier
from core.knowledge.ike2.etl.sources import default_knowledge_state
from core.knowledge.ike2.etl.validate import validate_rows
from tests.ike2.test_etl_bulk_inject import FakeWriter

_REPO = Path(__file__).resolve().parents[2].parent
_LAYER1 = _REPO / "data" / "layer1_produce_catalog.json"
_SEED = (
    Path(__file__).resolve().parents[2]
    / "core"
    / "knowledge"
    / "ike2"
    / "etl"
    / "adapters"
    / "seeds"
    / "produce_catalog_seed.json"
)


def test_produce_adapter_is_source_adapter():
    assert isinstance(ProduceCatalogAdapter(), SourceAdapter)


def test_produce_adapter_license_ok_for_cc0():
    assert ProduceCatalogAdapter().license_ok() is True


def test_produce_seed_emits_plant_forward_records():
    rows = emit_layer1_records(ProduceCatalogAdapter(seed_path=_SEED))
    assert len(rows) >= 5
    for raw in rows:
        assert raw.get("plant_origin") is True
        assert raw.get("animal_origin") is not True
        assert not raw.get("dairy_source")
        assert not raw.get("egg_source")
        assert not raw.get("fish_source")
        assert raw.get("canonical_name")


def test_produce_records_pass_validate_and_map():
    adapter = ProduceCatalogAdapter(seed_path=_SEED)
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
    assert all(r["knowledge_state"] == "AUTO_CLASSIFIED" for r in ok)
    assert all(r["classification_method"] == "bulk:produce_catalog" for r in ok)


def test_produce_catalog_registered_in_sources():
    assert default_knowledge_state("produce_catalog") == "AUTO_CLASSIFIED"
    assert "produce_catalog" in _SOURCE_TIER
    assert _tier("produce_catalog") > 0


def test_layer1_produce_catalog_dry_run_inject_zero_rejects():
    assert _LAYER1.is_file(), "emit layer1_produce_catalog.json from produce adapter seed"
    source, records = load_dump(str(_LAYER1))
    assert source is None
    assert len(records) >= 5
    w = FakeWriter()
    stats = inject(records, "produce_catalog", w)
    assert stats.rejected == 0
    assert stats.inserted == len(records)
    sample = next(iter(w.groups.values()))
    assert sample["plant_origin"] is True
    assert sample["knowledge_state"] == "AUTO_CLASSIFIED"


def test_layer1_produce_matches_adapter_emission():
    """Committed dump is the adapter output (no hand-edited drift)."""
    adapter_rows = emit_layer1_records(ProduceCatalogAdapter(seed_path=_SEED))
    dump = json.loads(_LAYER1.read_text(encoding="utf-8"))
    assert [r["canonical_name"] for r in dump] == [
        r["canonical_name"] for r in adapter_rows
    ]
