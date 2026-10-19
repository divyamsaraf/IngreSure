"""Produce catalog SourceAdapter (Item 1.1 / Prompt 5).

Reads a small curated CC0 seed — does not scrape licensed grocery dumps.
Emission goes through ``emit_layer1_records`` (central license gate).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.knowledge.ike2.etl.license_check import license_check

_DEFAULT_SEED = Path(__file__).resolve().parent / "seeds" / "produce_catalog_seed.json"

# Flags produce rows must never invent (plant-forward contract).
_FORBIDDEN_ANIMALISH = (
    "animal_origin",
    "dairy_source",
    "egg_source",
    "fish_source",
    "shellfish_source",
    "insect_derived",
    "bee_product",
    "enzyme_animal_source",
)


@dataclass
class ProduceCatalogAdapter:
    """Curated fresh-produce / plant commodity → Layer-1 records."""

    name: str = "produce_catalog"
    license_spdx: str = "CC0-1.0"
    seed_path: Path = field(default_factory=lambda: _DEFAULT_SEED)

    def license_ok(self) -> bool:
        return bool(license_check(self.name, self.license_spdx))

    def to_layer1_records(self) -> list[dict]:
        raw = json.loads(self.seed_path.read_text(encoding="utf-8"))
        # Prefer SPDX from seed metadata when present.
        meta_spdx = (raw.get("license_spdx") or "").strip()
        if meta_spdx:
            self.license_spdx = meta_spdx
        ingredients = raw.get("ingredients") or []
        out: list[dict] = []
        for item in ingredients:
            rec = _normalize_produce_record(item)
            if rec is not None:
                out.append(rec)
        return out


def _normalize_produce_record(item: dict[str, Any]) -> dict[str, Any] | None:
    name = str(item.get("canonical_name") or "").strip()
    if not name:
        return None
    rec: dict[str, Any] = {
        "canonical_name": name,
        "aliases": list(item.get("aliases") or []),
        "plant_origin": True,
        "animal_origin": False,
        "regions": list(item.get("regions") or ["Global"]),
    }
    # Optional plant diet flags from seed (never force animalish).
    for flag in (
        "root_vegetable",
        "onion_source",
        "garlic_source",
        "soy_source",
        "gluten_source",
        "sesame_source",
        "peanut_source",
        "tree_nut_source",
        "fungal",
        "fermented",
    ):
        if item.get(flag):
            rec[flag] = True
    # Do not emit animalish=False keys — full false blocks are the asserted_flags
    # pollution signature. Defaults stay false after adapt; only assert trues.
    for bad in _FORBIDDEN_ANIMALISH:
        if bad == "animal_origin":
            continue  # already set False above as the plant-forward decision
        rec.pop(bad, None)
    return rec


def write_layer1_dump(
    path: Path,
    *,
    adapter: ProduceCatalogAdapter | None = None,
) -> list[dict]:
    """Emit Layer-1 JSON via the shared license gate (operator / test helper)."""
    from core.knowledge.ike2.etl.adapters.protocol import emit_layer1_records

    ad = adapter or ProduceCatalogAdapter()
    rows = emit_layer1_records(ad)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows
