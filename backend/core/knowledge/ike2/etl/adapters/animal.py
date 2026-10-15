"""Animal catalog SourceAdapter (Item 1.2 / Prompt 6).

Curated CC0 seed — lands ``DISCOVERED`` / tier 2 (explicit check-in; does not
inherit produce's AUTO_CLASSIFIED). Emission goes through ``emit_layer1_records``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.knowledge.ike2.etl.license_check import license_check

_DEFAULT_SEED = Path(__file__).resolve().parent / "seeds" / "animal_catalog_seed.json"

# Flags that imply animal_origin (CHECK mirror + adapter contract).
_ANIMALISH_IMPLIERS = (
    "dairy_source",
    "egg_source",
    "fish_source",
    "shellfish_source",
    "insect_derived",
    "bee_product",
    "enzyme_animal_source",
)


@dataclass
class AnimalCatalogAdapter:
    """Curated animal / dairy / egg / fish commodities → Layer-1 records."""

    name: str = "animal_catalog"
    license_spdx: str = "CC0-1.0"
    seed_path: Path = field(default_factory=lambda: _DEFAULT_SEED)

    def license_ok(self) -> bool:
        return bool(license_check(self.name, self.license_spdx))

    def to_layer1_records(self) -> list[dict]:
        raw = json.loads(self.seed_path.read_text(encoding="utf-8"))
        meta_spdx = (raw.get("license_spdx") or "").strip()
        if meta_spdx:
            self.license_spdx = meta_spdx
        out: list[dict] = []
        for item in raw.get("ingredients") or []:
            rec = _normalize_animal_record(item)
            if rec is not None:
                out.append(rec)
        return out


def _normalize_animal_record(item: dict[str, Any]) -> dict[str, Any] | None:
    name = str(item.get("canonical_name") or "").strip()
    if not name:
        return None
    rec: dict[str, Any] = {
        "canonical_name": name,
        "aliases": list(item.get("aliases") or []),
        "plant_origin": False,
        "animal_origin": True,
        "regions": list(item.get("regions") or ["Global"]),
    }
    species = item.get("animal_species")
    if species:
        rec["animal_species"] = str(species).strip()

    for flag in (
        "dairy_source",
        "egg_source",
        "fish_source",
        "shellfish_source",
        "insect_derived",
        "bee_product",
        "enzyme_animal_source",
        "fermented",
        "fungal",
    ):
        if item.get(flag):
            rec[flag] = True

    # Never under-flag: any animalish implication forces animal_origin.
    if any(rec.get(f) for f in _ANIMALISH_IMPLIERS) or rec.get("animal_species"):
        rec["animal_origin"] = True

    # Animal catalog must not invent plant_origin.
    rec["plant_origin"] = False
    return rec


def write_layer1_dump(
    path: Path,
    *,
    adapter: AnimalCatalogAdapter | None = None,
) -> list[dict]:
    """Emit Layer-1 JSON via the shared license gate (operator / test helper)."""
    from core.knowledge.ike2.etl.adapters.protocol import emit_layer1_records

    ad = adapter or AnimalCatalogAdapter()
    rows = emit_layer1_records(ad)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows
