import json
from pathlib import Path

from core.knowledge.ike2.etl.bulk_inject import inject, load_dump
from tests.ike2.test_etl_bulk_inject import FakeWriter

_REPO = Path(__file__).resolve().parents[3]
_LAYER1 = _REPO / "data" / "layer1_e_numbers.json"


def test_layer1_e_numbers_dry_run_inject():
    assert _LAYER1.exists(), "run generate_ike2_e_numbers.py first"
    source, records = load_dump(str(_LAYER1))
    assert source is None
    assert len(records) == 330

    w = FakeWriter()
    stats = inject(records[:5], "e_number_catalog", w)
    assert stats.inserted == 5
    assert stats.rejected == 0
    e_aliases = {a[0] for a in w.aliases if a[0].startswith("e")}
    assert e_aliases, "expected e_number alias_type rows"

    sample = next(iter(w.groups.values()))
    assert sample.get("knowledge_state") in ("LOCKED", "AUTO_CLASSIFIED")


def test_layer1_e_numbers_json_shape():
    data = json.loads(_LAYER1.read_text(encoding="utf-8"))
    records = data if isinstance(data, list) else data.get("ingredients", [])
    assert len(records) == 330
    first = records[0]
    assert "aliases_meta" in first
    assert any(a.get("alias_type") == "e_number" for a in first["aliases_meta"])
