#!/usr/bin/env python3
"""
Parse USDA FoodData Central bulk JSON → IngreSure staging JSON.

Download manually from https://fdc.nal.usda.gov/download-datasets.html:
  backend/data/usda_foundation_foods.json
  backend/data/usda_sr_legacy_foods.json

Fallback paths (from ./scripts/download_tier1_data.sh):
  data/raw/foundationDownload.json
  data/raw/FoodData_Central_sr_legacy_food_json_2021-10-28.json

Writes: data/usda_staging.json

Uses only Python standard library. Does not modify ontology.json.

Run from repo root:
  python backend/scripts/parse_usda_bulk.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent.parent
_BACKEND_DATA = _REPO / "backend" / "data"
_DEFAULT_FOUNDATION = _BACKEND_DATA / "usda_foundation_foods.json"
_DEFAULT_SR_LEGACY = _BACKEND_DATA / "usda_sr_legacy_foods.json"
_DEFAULT_OUTPUT = _REPO / "data" / "usda_staging.json"
_DEFAULT_OFF_STAGING = _REPO / "data" / "off_staging.json"

_FOUNDATION_FALLBACKS = (
    _REPO / "data" / "usda_foundation_foods.json",
    _REPO / "data" / "raw" / "foundationDownload.json",
)
_SR_LEGACY_FALLBACKS = (
    _REPO / "data" / "usda_sr_legacy_foods.json",
    _REPO / "data" / "raw" / "FoodData_Central_sr_legacy_food_json_2021-10-28.json",
)

# Name-based overrides (same as parse_off_taxonomy.py / EXP-1 Step 4)
_DAIRY_TERMS = (
    "milk", "cream", "butter", "cheese", "whey", "casein", "lactose",
    "ghee", "paneer", "yogurt", "curd",
)
_EGG_TERMS = ("egg", "albumin", "ovalbumin")
_GLUTEN_TERMS = (
    "wheat", "gluten", "flour", "semolina", "durum", "spelt", "barley",
    "rye", "kamut",
)
_SOY_TERMS = ("soy", "soya", "tofu", "tempeh", "edamame", "miso")
_NUT_TERMS = (
    "peanut", "groundnut", "almond", "cashew", "walnut", "pecan",
    "pistachio", "hazelnut", "macadamia", "brazil nut", "pine nut",
)
_SESAME_TERMS = ("sesame", "tahini", "til", "gingelly")
_ANIMAL_OVERRIDE_NAMES = frozenset({
    "gelatin", "gelatine", "lard", "tallow", "suet", "rennet", "carmine",
    "shellac", "beeswax", "lanolin", "l-cysteine", "cysteine",
})
_ROOT_VEGETABLES = frozenset({
    "potato", "carrot", "beetroot", "radish", "turnip", "yam", "taro",
    "sweet potato", "onion", "garlic", "leek", "shallot", "spring onion",
    "scallion", "chive",
})
_ONION_NAMES = frozenset({
    "onion", "shallot", "spring onion", "scallion", "leek",
})
_GARLIC_NAMES = frozenset({"garlic", "chive"})
_ANIMAL_FAT_TERMS = (
    "lard", "tallow", "suet", "beef fat", "chicken fat", "duck fat",
    "goose fat", "animal fat", "fish oil",
)

_SKIP_CATEGORIES = frozenset({
    "Beverages",
    "Baby Foods",
    "Fast Foods",
    "Restaurant Foods",
    "Meals, Entrees, and Side Dishes",
})

_PLANT_CATEGORIES = frozenset({
    "Vegetables and Vegetable Products",
    "Fruits and Fruit Juices",
    "Nut and Seed Products",
    "Legumes and Legume Products",
    "Cereal Grains and Pasta",
})

_ANIMAL_CATEGORIES = frozenset({
    "Poultry Products",
    "Beef Products",
    "Pork Products",
    "Finfish and Shellfish Products",
    "Lamb, Veal, and Game Products",
})

_KNOWN_INGREDIENT_TERMS = (
    _ANIMAL_OVERRIDE_NAMES
    | _ROOT_VEGETABLES
    | {term for group in (_DAIRY_TERMS, _EGG_TERMS, _GLUTEN_TERMS, _SOY_TERMS, _NUT_TERMS, _SESAME_TERMS) for term in group}
    | {
        "honey", "salt", "sugar", "vinegar", "yeast", "cocoa", "coffee", "tea",
        "hummus", "tahini", "molasses", "starch", "gelatin", "gelatine",
    }
)


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unknown"


def _contains_any(text: str, terms: tuple[str, ...] | frozenset[str]) -> bool:
    t = text.lower()
    return any(term in t for term in terms)


def _is_egg_name(text: str) -> bool:
    t = text.lower()
    if "eggplant" in t or "egg plant" in t:
        return False
    return _contains_any(t, _EGG_TERMS) or re.search(r"\begg(?:s)?\b", t) is not None


def _food_category_str(food: dict[str, Any]) -> str:
    cat = food.get("foodCategory")
    if isinstance(cat, dict):
        return (cat.get("description") or "").strip()
    if isinstance(cat, str):
        return cat.strip()
    return ""


def _input_food_synonyms(food: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in food.get("inputFoods") or []:
        if not isinstance(item, dict):
            continue
        desc = (item.get("foodDescription") or "").strip()
        if not desc:
            continue
        key = desc.lower()
        if key not in seen:
            out.append(desc)
            seen.add(key)
    return out


def _apply_special_classifications(ing: dict[str, Any], english_name: str) -> None:
    canon = ing["canonical_name"]
    original = english_name.lower()

    if _contains_any(canon, _DAIRY_TERMS):
        ing["dairy_source"] = True
        ing["animal_origin"] = True

    if _is_egg_name(canon):
        ing["egg_source"] = True
        ing["animal_origin"] = True

    if _contains_any(canon, _GLUTEN_TERMS):
        ing["gluten_source"] = True

    if _contains_any(canon, _SOY_TERMS):
        ing["soy_source"] = True

    for term in _NUT_TERMS:
        if term in canon:
            ing["nut_source"] = canon
            break

    if _contains_any(canon, _SESAME_TERMS):
        ing["sesame_source"] = True

    if canon in _ANIMAL_OVERRIDE_NAMES:
        ing["animal_origin"] = True

    if "fermented" in canon or "fermented" in original:
        ing["fermented"] = True

    if canon in _ROOT_VEGETABLES:
        ing["root_vegetable"] = True
    if canon in _ONION_NAMES:
        ing["onion_source"] = True
    if canon in _GARLIC_NAMES:
        ing["garlic_source"] = True


def _flags_from_category(category: str, description: str) -> dict[str, Any] | None:
    """Return dietary flags from USDA category, or None if category should be skipped."""
    cat = category.strip()
    if cat in _SKIP_CATEGORIES:
        return None

    canon = description.lower().strip()
    flags: dict[str, Any] = {
        "animal_origin": False,
        "plant_origin": False,
        "dairy_source": False,
        "egg_source": False,
    }

    if cat == "Dairy and Egg Products":
        flags["animal_origin"] = True
        if _contains_any(canon, _DAIRY_TERMS):
            flags["dairy_source"] = True
        if _is_egg_name(canon):
            flags["egg_source"] = True
    elif cat in _ANIMAL_CATEGORIES:
        flags["animal_origin"] = True
    elif cat in _PLANT_CATEGORIES:
        flags["plant_origin"] = True
    elif cat == "Fats and Oils":
        flags["plant_origin"] = True
        if _contains_any(canon, _ANIMAL_FAT_TERMS):
            flags["animal_origin"] = True
            flags["plant_origin"] = False

    return flags


def _is_numbers_only(description: str) -> bool:
    cleaned = re.sub(r"[^a-z0-9]", "", description.lower())
    return bool(cleaned) and cleaned.isdigit()


def _description_allowed(description: str, off_single_words: set[str]) -> bool:
    if _is_numbers_only(description):
        return False
    canon = description.lower().strip()
    words = canon.split()
    if len(words) >= 2:
        return True
    if canon in off_single_words:
        return False
    return canon in _KNOWN_INGREDIENT_TERMS


def _load_off_single_words(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    words: set[str] = set()
    for ing in data.get("ingredients") or []:
        if not isinstance(ing, dict):
            continue
        cn = (ing.get("canonical_name") or "").strip().lower()
        if cn and " " not in cn:
            words.add(cn)
    return words


def _resolve_input(path: Path, fallbacks: tuple[Path, ...], label: str) -> Path | None:
    if path.exists():
        return path
    for fallback in fallbacks:
        if fallback.exists():
            print(f"Using {fallback} for {label}", file=sys.stderr)
            return fallback
    print(f"Warning: {label} not found ({path})", file=sys.stderr)
    return None


def _load_foods(path: Path, list_key: str) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    foods = data.get(list_key) or []
    return [f for f in foods if isinstance(f, dict)]


def _build_ingredient(
    food: dict[str, Any],
    category: str,
    dietary: dict[str, Any],
) -> dict[str, Any]:
    description = (food.get("description") or "").strip()
    canonical = description.lower()
    synonyms = _input_food_synonyms(food)

    seen_aliases: set[str] = set()
    aliases: list[str] = []
    for a in [description] + synonyms:
        a = a.strip()
        if not a:
            continue
        key = a.lower()
        if key not in seen_aliases:
            aliases.append(a)
            seen_aliases.add(key)

    ing: dict[str, Any] = {
        "id": slugify(description),
        "canonical_name": canonical,
        "aliases": aliases,
        "animal_origin": dietary["animal_origin"],
        "plant_origin": dietary["plant_origin"],
        "synthetic": False,
        "fungal": False,
        "insect_derived": False,
        "egg_source": dietary["egg_source"],
        "dairy_source": dietary["dairy_source"],
        "gluten_source": False,
        "soy_source": False,
        "sesame_source": False,
        "nut_source": None,
        "alcohol_content": None,
        "root_vegetable": False,
        "onion_source": False,
        "garlic_source": False,
        "fermented": False,
        "uncertainty_flags": [],
        "derived_from": [],
        "contains": [],
        "may_contain": [],
        "regions": ["Global"],
        "_source": "usda_fdc",
        "_fdc_id": food.get("fdcId"),
        "_usda_category": category or None,
    }
    _apply_special_classifications(ing, description)
    return ing


def _merge_ingredient(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    seen = {a.lower() for a in existing.get("aliases") or []}
    for alias in incoming.get("aliases") or []:
        if alias.lower() not in seen:
            existing.setdefault("aliases", []).append(alias)
            seen.add(alias.lower())

    for flag in (
        "animal_origin", "plant_origin", "dairy_source", "egg_source",
        "gluten_source", "soy_source", "sesame_source", "root_vegetable",
        "onion_source", "garlic_source", "fermented",
    ):
        existing[flag] = existing.get(flag) or incoming.get(flag)

    if existing.get("nut_source") is None and incoming.get("nut_source") is not None:
        existing["nut_source"] = incoming["nut_source"]


def parse_usda_bulk(
    foundation_path: Path | None,
    sr_legacy_path: Path | None,
    *,
    off_single_words: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stats: dict[str, Any] = {
        "foundation_foods_processed": 0,
        "sr_legacy_foods_processed": 0,
        "skipped_no_description": 0,
        "skipped_category": 0,
        "skipped_numbers_only": 0,
        "skipped_off_single_word": 0,
        "skipped_single_word_unknown": 0,
        "valid": 0,
        "category_counts": Counter(),
    }

    by_canonical: dict[str, dict[str, Any]] = {}
    seen_ids: dict[str, int] = {}

    def process_food(food: dict[str, Any], *, source_label: str) -> None:
        if source_label == "foundation":
            stats["foundation_foods_processed"] += 1
        else:
            stats["sr_legacy_foods_processed"] += 1

        description = (food.get("description") or "").strip()
        if not description:
            stats["skipped_no_description"] += 1
            return

        category = _food_category_str(food)
        dietary = _flags_from_category(category, description)
        if dietary is None:
            stats["skipped_category"] += 1
            return

        if _is_numbers_only(description):
            stats["skipped_numbers_only"] += 1
            return

        canon = description.lower().strip()
        if len(canon.split()) < 2:
            if canon in off_single_words:
                stats["skipped_off_single_word"] += 1
                return
            if canon not in _KNOWN_INGREDIENT_TERMS:
                stats["skipped_single_word_unknown"] += 1
                return

        ing = _build_ingredient(food, category, dietary)
        base_id = ing["id"]
        if base_id in seen_ids:
            seen_ids[base_id] += 1
            ing["id"] = f"{base_id}_{seen_ids[base_id]}"
        else:
            seen_ids[base_id] = 1

        if canon in by_canonical:
            _merge_ingredient(by_canonical[canon], ing)
        else:
            by_canonical[canon] = ing
            stats["valid"] += 1
            stats["category_counts"][category or "(uncategorized)"] += 1

    if foundation_path:
        for food in _load_foods(foundation_path, "FoundationFoods"):
            process_food(food, source_label="foundation")

    if sr_legacy_path:
        for food in _load_foods(sr_legacy_path, "SRLegacyFoods"):
            process_food(food, source_label="sr_legacy")

    ingredients = sorted(by_canonical.values(), key=lambda i: i["canonical_name"])
    return ingredients, stats


def _print_summary(stats: dict[str, Any]) -> None:
    print(f"Foundation foods processed:    {stats['foundation_foods_processed']}")
    print(f"SR Legacy foods processed:     {stats['sr_legacy_foods_processed']}")
    print(f"Valid ingredients extracted:   {stats['valid']}")
    print(f"Skipped (no description):      {stats['skipped_no_description']}")
    print(f"Skipped (excluded category):   {stats['skipped_category']}")
    print(f"Skipped (numbers only):        {stats['skipped_numbers_only']}")
    print(f"Skipped (OFF-covered single):  {stats['skipped_off_single_word']}")
    print(f"Skipped (unknown single word): {stats['skipped_single_word_unknown']}")
    print("Counts per category:")
    for category, count in stats["category_counts"].most_common():
        print(f"  {category}: {count}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse USDA FDC bulk JSON to IngreSure staging JSON",
    )
    parser.add_argument(
        "--foundation",
        type=Path,
        default=_DEFAULT_FOUNDATION,
        help="USDA Foundation Foods JSON",
    )
    parser.add_argument(
        "--sr-legacy",
        type=Path,
        default=_DEFAULT_SR_LEGACY,
        help="USDA SR Legacy Foods JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help=f"Staging output (default: {_DEFAULT_OUTPUT.relative_to(_REPO)})",
    )
    parser.add_argument(
        "--off-staging",
        type=Path,
        default=_DEFAULT_OFF_STAGING,
        help="OFF staging JSON used to skip generic single-word terms",
    )
    args = parser.parse_args()

    foundation = _resolve_input(args.foundation, _FOUNDATION_FALLBACKS, "Foundation Foods")
    sr_legacy = _resolve_input(args.sr_legacy, _SR_LEGACY_FALLBACKS, "SR Legacy Foods")

    if foundation is None and sr_legacy is None:
        print(
            "No USDA input files found. Download from "
            "https://fdc.nal.usda.gov/download-datasets.html",
            file=sys.stderr,
        )
        print(
            "  backend/data/usda_foundation_foods.json\n"
            "  backend/data/usda_sr_legacy_foods.json",
            file=sys.stderr,
        )
        return 1

    off_single_words = _load_off_single_words(args.off_staging)
    if off_single_words:
        print(f"Loaded {len(off_single_words)} single-word OFF terms for filtering", file=sys.stderr)

    ingredients, stats = parse_usda_bulk(
        foundation,
        sr_legacy,
        off_single_words=off_single_words,
    )

    payload = {
        "source": "usda_fdc",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "total": len(ingredients),
        "ingredients": ingredients,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(ingredients)} ingredients to {args.output}")
    _print_summary(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
