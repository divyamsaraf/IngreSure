#!/usr/bin/env python3
"""
Transform USDA FDC bulk JSON downloads → Layer 1 ingest JSON.

Inputs (after ./scripts/download_tier1_data.sh):
  data/raw/foundationDownload.json
  data/raw/FoodData_Central_sr_legacy_food_json_2021-10-28.json

Output: data/layer1_usda_fdc.json

Run from repo root:
  python backend/scripts/transform_usda_fdc_bulk.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
sys.path.insert(0, str(_backend))

from core.normalization.normalizer import normalize_ingredient_key
from core.external_apis.usda_fdc import _infer_flags_from_category, _infer_flags_from_text

_FOUNDATION = _repo / "data" / "raw" / "foundationDownload.json"
_SR_LEGACY = _repo / "data" / "raw" / "FoodData_Central_sr_legacy_food_json_2021-10-28.json"
_DEFAULT_OUTPUT = _repo / "data" / "layer1_usda_fdc.json"

_SR_SKIP_PATTERNS = re.compile(
    r"refrigerated|artificial flavor|artificial flavour|imitation|"
    r"baby food|infant formula|fast food|restaurant|"
    r"supplement|vitamin|capsule|tablet",
    re.I,
)


def _food_category_str(food: dict[str, Any]) -> str:
    cat = food.get("foodCategory")
    if isinstance(cat, dict):
        return (cat.get("description") or "").strip()
    if isinstance(cat, str):
        return cat.strip()
    return ""


def _aliases_from_food(food: dict[str, Any], description: str) -> list[str]:
    aliases: list[str] = []
    seen: set[str] = set()

    def add(raw: str | None) -> None:
        if not raw:
            return
        raw = raw.strip()
        if not raw or len(raw) > 200:
            return
        norm = normalize_ingredient_key(raw)
        if not norm or norm in seen:
            return
        seen.add(norm)
        aliases.append(raw)

    for attr in food.get("foodAttributes") or []:
        if not isinstance(attr, dict):
            continue
        name = (attr.get("name") or "").lower()
        if name in ("common name", "synonym", "scientific name", "display name"):
            val = attr.get("value")
            if isinstance(val, str):
                add(val)
            elif isinstance(val, list):
                for v in val:
                    if isinstance(v, str):
                        add(v)

    sci = food.get("scientificName")
    if isinstance(sci, str):
        add(sci)

    ndb = food.get("ndbNumber")
    if ndb is not None:
        add(f"NDB {ndb}")

    if description:
        add(description)
    return aliases


def _sr_legacy_description_ok(description: str) -> bool:
    if not description or len(description) > 90:
        return False
    if len(description.split()) > 6:
        return False
    if _SR_SKIP_PATTERNS.search(description):
        return False
    return True


def _food_to_layer1_row(food: dict[str, Any], *, strict: bool) -> dict[str, Any] | None:
    description = (food.get("description") or "").strip()
    if not description:
        return None
    if strict and not _sr_legacy_description_ok(description):
        return None

    category = _food_category_str(food)
    flags = _infer_flags_from_text(description, category=category)
    flags["uncertainty_flags"] = ["usda_fdc_bulk_inferred"]

    aliases = _aliases_from_food(food, description)
    canon_norm = normalize_ingredient_key(description)
    aliases = [a for a in aliases if normalize_ingredient_key(a) != canon_norm]

    return {
        "canonical_name": description,
        "aliases": aliases[:20],
        "source": "usda_fdc",
        "animal_origin": flags.get("animal_origin", False),
        "plant_origin": flags.get("plant_origin", False),
        "dairy_source": flags.get("dairy_source", False),
        "egg_source": flags.get("egg_source", False),
        "gluten_source": flags.get("gluten_source", False),
        "soy_source": flags.get("soy_source", False),
        "sesame_source": flags.get("sesame_source", False),
        "nut_source": flags.get("nut_source"),
        "root_vegetable": flags.get("root_vegetable", False),
        "onion_source": flags.get("onion_source", False),
        "garlic_source": flags.get("garlic_source", False),
        "alcohol_content": flags.get("alcohol_content"),
        "uncertainty_flags": flags.get("uncertainty_flags") or [],
    }


def transform_usda_bulk(
    foundation_path: Path,
    sr_legacy_path: Path | None,
    *,
    include_sr_legacy: bool = True,
) -> list[dict[str, Any]]:
    by_norm: dict[str, dict[str, Any]] = {}

    def merge_row(row: dict[str, Any]) -> None:
        norm = normalize_ingredient_key(row["canonical_name"])
        if not norm:
            return
        if norm not in by_norm:
            by_norm[norm] = row
            return
        existing = by_norm[norm]
        seen = {normalize_ingredient_key(a) for a in existing.get("aliases") or []}
        for a in row.get("aliases") or []:
            an = normalize_ingredient_key(a)
            if an and an not in seen:
                existing.setdefault("aliases", []).append(a)
                seen.add(an)

    if foundation_path.exists():
        data = json.loads(foundation_path.read_text(encoding="utf-8"))
        foods = data.get("FoundationFoods") or []
        for food in foods:
            if not isinstance(food, dict):
                continue
            row = _food_to_layer1_row(food, strict=False)
            if row:
                merge_row(row)

    if include_sr_legacy and sr_legacy_path and sr_legacy_path.exists():
        data = json.loads(sr_legacy_path.read_text(encoding="utf-8"))
        foods = data.get("SRLegacyFoods") or []
        for food in foods:
            if not isinstance(food, dict):
                continue
            row = _food_to_layer1_row(food, strict=True)
            if row:
                merge_row(row)

    return sorted(by_norm.values(), key=lambda r: r["canonical_name"].lower())


def main() -> int:
    parser = argparse.ArgumentParser(description="Transform USDA FDC bulk JSON to Layer 1")
    parser.add_argument("--foundation", type=Path, default=_FOUNDATION)
    parser.add_argument("--sr-legacy", type=Path, default=_SR_LEGACY)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--no-sr-legacy", action="store_true", help="Foundation Foods only")
    args = parser.parse_args()

    if not args.foundation.exists():
        print(f"Foundation file not found: {args.foundation}", file=sys.stderr)
        print("Run: ./scripts/download_tier1_data.sh", file=sys.stderr)
        return 1

    rows = transform_usda_bulk(
        args.foundation,
        args.sr_legacy,
        include_sr_legacy=not args.no_sr_legacy,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(rows)} groups to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
