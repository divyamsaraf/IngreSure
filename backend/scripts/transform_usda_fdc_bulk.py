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

from core.external_apis.usda_fdc import (
    REVIEWED_ASSERTED_CLEARS,
    _FISH_NAME,
    _SHELLFISH_FALSE_FRIEND,
    _SHELLFISH_NAME,
    _infer_flags_from_text,
    asserted_clear_allowed,
    is_shellfish_false_friend,
)
from core.normalization.normalizer import normalize_ingredient_key

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


def _name_kind_hit(description: str) -> bool:
    t = (description or "").lower()
    if _SHELLFISH_FALSE_FRIEND.search(t):
        return False
    if re.search(r"\bseafood\b", t):
        return True
    if _SHELLFISH_NAME.search(t):
        return True
    return bool(_FISH_NAME.search(t))


def _uncertainty_for_row(
    description: str, category: str, *, kind_true: bool
) -> list[str]:
    """Split fish/shellfish markers; keep a group-level SAFE ceiling.

    ``usda_fdc_category_derived`` records kind evidence. It is not full
    allergen coverage (breaded/battered/creamed rows), so a row-level
    ``*inferred*`` token always stays alongside it. Item 42 lets allergy
    FAIL stand when untrusted; clean passes stay capped.
    """
    cat = (category or "").lower()
    in_fs = "finfish" in cat or "shellfish" in cat
    if kind_true:
        out: list[str] = []
        if in_fs:
            out.append("usda_fdc_category_derived")
        if _name_kind_hit(description):
            out.append("usda_fdc_name_inferred")
        else:
            out.append("usda_fdc_bulk_inferred")
        return out or ["usda_fdc_bulk_inferred"]
    return ["usda_fdc_bulk_inferred"]


def _food_to_layer1_row(food: dict[str, Any], *, strict: bool) -> dict[str, Any] | None:
    description = (food.get("description") or "").strip()
    if not description:
        return None
    if strict and not _sr_legacy_description_ok(description):
        return None

    category = _food_category_str(food)
    flags = _infer_flags_from_text(description, category=category)
    kind_true = bool(flags.get("fish_source") or flags.get("shellfish_source"))
    unc = _uncertainty_for_row(description, category, kind_true=kind_true)

    aliases = _aliases_from_food(food, description)
    canon_norm = normalize_ingredient_key(description)
    aliases = [a for a in aliases if normalize_ingredient_key(a) != canon_norm]

    # True-only emit by default (sparse falses trip asserted_flags_false_pollution).
    # Deliberate clears for Item-42 false friends / dairy↔egg disambiguation are
    # emitted as asserted falses (≤3) so sticky OR can be corrected on re-inject.
    row: dict[str, Any] = {
        "canonical_name": description,
        "aliases": aliases[:20],
        "source": "usda_fdc",
        "uncertainty_flags": unc,
    }
    if category:
        row["food_category"] = category
    for key in (
        "animal_origin",
        "plant_origin",
        "dairy_source",
        "egg_source",
        "fish_source",
        "shellfish_source",
        "gluten_source",
        "soy_source",
        "sesame_source",
        "tree_nut_source",
        "peanut_source",
        "root_vegetable",
        "onion_source",
        "garlic_source",
    ):
        if flags.get(key):
            row[key] = True
    if flags.get("nut_source"):
        row["nut_source"] = flags["nut_source"]
    # Prefer explicit peanut bit when nut_source says peanut.
    if flags.get("nut_source") == "peanut":
        row["peanut_source"] = True
        row.pop("tree_nut_source", None)
    if flags.get("alcohol_content") is not None:
        row["alcohol_content"] = flags["alcohol_content"]
    if flags.get("fish_source") and not flags.get("shellfish_source"):
        row["animal_species"] = "fish"
    elif flags.get("shellfish_source"):
        row["animal_species"] = "shellfish"

    # Asserted clears are enumerated-only (frozen reviewed list). Inference may
    # omit false keys (true-only emit); sticky OR needs an explicit allow.
    deliberate_false: list[str] = []
    candidates: list[str] = []
    if is_shellfish_false_friend(description):
        candidates.append("shellfish_source")
        if flags.get("plant_origin") and not flags.get("animal_origin"):
            candidates.append("animal_origin")
            row["plant_origin"] = True
    if flags.get("dairy_source") and not flags.get("egg_source"):
        candidates.append("egg_source")
    if flags.get("egg_source") and not flags.get("dairy_source"):
        candidates.append("dairy_source")
    # Any frozen-list clear for this name whose inferred value is false.
    norm = normalize_ingredient_key(description)
    for clear_name, clear_flag in REVIEWED_ASSERTED_CLEARS:
        if clear_name == norm and not flags.get(clear_flag):
            candidates.append(clear_flag)
    for flag in dict.fromkeys(candidates):
        if asserted_clear_allowed(description, flag):
            row[flag] = False
            deliberate_false.append(flag)
    if deliberate_false:
        asserted = {k for k in row if k in (
            "animal_origin", "plant_origin", "dairy_source", "egg_source",
            "fish_source", "shellfish_source", "gluten_source", "soy_source",
            "sesame_source", "tree_nut_source", "peanut_source",
            "root_vegetable", "onion_source", "garlic_source",
        ) and row.get(k)}
        asserted.update(deliberate_false)
        row["asserted_flags"] = sorted(asserted)
    return row


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
