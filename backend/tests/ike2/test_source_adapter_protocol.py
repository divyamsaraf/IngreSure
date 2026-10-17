"""Item 1 Prompt 3–4: SourceAdapter Protocol + license gate."""
from __future__ import annotations

from dataclasses import dataclass, field

from core.knowledge.ike2.etl.adapt import map_record
from core.knowledge.ike2.etl.adapters import SourceAdapter, emit_layer1_records
from core.knowledge.ike2.etl.validate import validate_rows


@dataclass
class FakeAdapter:
    """Minimal SourceAdapter for contract tests (not a production source)."""

    name: str = "ontology"
    license_spdx: str | None = "CC0-1.0"
    _license_ok: bool = True
    records: list[dict] = field(default_factory=list)

    def license_ok(self) -> bool:
        return self._license_ok

    def to_layer1_records(self) -> list[dict]:
        return list(self.records)


def _broccoli_record() -> dict:
    return {
        "canonical_name": "broccoli",
        "aliases": ["broccoli florets"],
        "plant_origin": True,
        "animal_origin": False,
        "regions": ["Global"],
    }


def test_source_adapter_is_runtime_protocol():
    assert isinstance(FakeAdapter(), SourceAdapter)


def test_license_deny_via_adapter_flag_emits_zero_records():
    adapter = FakeAdapter(_license_ok=False, records=[_broccoli_record()])
    assert emit_layer1_records(adapter) == []


def test_missing_spdx_emits_zero_even_if_license_ok():
    adapter = FakeAdapter(
        license_spdx=None,
        _license_ok=True,
        records=[_broccoli_record()],
    )
    assert emit_layer1_records(adapter) == []


def test_disallowed_spdx_emits_zero():
    adapter = FakeAdapter(
        license_spdx="Proprietary-Secret",
        _license_ok=True,
        records=[_broccoli_record()],
    )
    assert emit_layer1_records(adapter) == []


def test_license_allow_emits_records_that_pass_validate():
    adapter = FakeAdapter(_license_ok=True, records=[_broccoli_record()])
    raw_rows = emit_layer1_records(adapter)
    assert len(raw_rows) == 1

    mapped = []
    for raw in raw_rows:
        row, _aliases = map_record(raw, adapter.name, "AUTO_CLASSIFIED")
        mapped.append(row)

    ok, rejects = validate_rows(mapped)
    assert rejects == []
    assert len(ok) == 1
    assert ok[0]["canonical_name"] == "broccoli"
    assert ok[0]["plant_origin"] is True
