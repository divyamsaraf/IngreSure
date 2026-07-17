#!/usr/bin/env python3
"""Generate IKE-2 E-number artifacts from e_number_catalog.json.

Outputs:
  - backend/core/knowledge/ike2/truth_anchor_e_numbers.json
  - data/layer1_e_numbers.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
sys.path.insert(0, str(_backend))

from core.knowledge.ike2.e_number_catalog import (  # noqa: E402
    build_anchor_facts,
    layer1_records,
    load_catalog,
)

DEFAULT_CATALOG = _repo / "data" / "e_number_catalog.json"
TRUTH_ANCHOR_OUT = _backend / "core" / "knowledge" / "ike2" / "truth_anchor_e_numbers.json"
LAYER1_OUT = _repo / "data" / "layer1_e_numbers.json"


def _upgrade_catalog_entries(entries: list[dict]) -> list[dict]:
    """Add IKE-2 optional fields with safe defaults."""
    upgraded = []
    for entry in entries:
        row = dict(entry)
        for flag in (
            "peanut_source", "tree_nut_source", "fish_source", "shellfish_source",
            "mustard_source", "celery_source", "lupin_source", "sulphite_source",
        ):
            row.setdefault(flag, False)
        tier = "B" if (row.get("uncertainty_flags") or []) else "A"
        row.setdefault("ike2_tier", tier)
        row.setdefault("verdict_cap", "WARN" if tier == "B" else None)
        row.setdefault("alcohol_role", None)
        row.setdefault(
            "primary_source_url",
            "https://ec.europa.eu/food/safety/food-improvement-agents/additives-database_en",
        )
        row.setdefault("sources", ["e_number_catalog"])
        upgraded.append(row)
    return upgraded


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate IKE-2 E-number artifacts")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--upgrade-catalog", action="store_true", default=True)
    parser.add_argument("--no-upgrade-catalog", dest="upgrade_catalog", action="store_false")
    args = parser.parse_args(argv)

    with open(args.catalog, encoding="utf-8") as fh:
        catalog = json.load(fh)
    entries = catalog.get("entries", [])
    if args.upgrade_catalog:
        entries = _upgrade_catalog_entries(entries)
        catalog["entries"] = entries
        args.catalog.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    anchor_map = build_anchor_facts(entries)
    layer1 = layer1_records(entries)

    TRUTH_ANCHOR_OUT.write_text(json.dumps(anchor_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LAYER1_OUT.write_text(json.dumps(layer1, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "truth_anchor_keys": len(anchor_map),
        "layer1_groups": len(layer1),
        "catalog_entries": len(entries),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
