#!/usr/bin/env python3
"""
Parse Open Food Facts ingredients taxonomy → IngreSure staging JSON.

Reads:  backend/data/off_ingredients_taxonomy.json (or --input)
Writes: data/off_staging.json

Uses only Python standard library. Does not modify ontology.json.

Run from repo root:
  python backend/scripts/parse_off_taxonomy.py
  python backend/scripts/parse_off_taxonomy.py --input data/raw/off_ingredients_taxonomy.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent.parent
_BACKEND_DATA = _REPO / "backend" / "data"
_DEFAULT_INPUT = _BACKEND_DATA / "off_ingredients_taxonomy.json"
_DEFAULT_OUTPUT = _REPO / "data" / "off_staging.json"

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


def _lang_val(field: Any, lang: str = "en") -> str | None:
    if field is None:
        return None
    if isinstance(field, dict):
        v = field.get(lang) or field.get("en")
        return str(v).strip() if v else None
    s = str(field).strip()
    return s or None


def _lang_list(field: Any, lang: str = "en") -> list[str]:
    if not isinstance(field, dict):
        return []
    raw = field.get(lang) or field.get("en")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    s = str(raw).strip()
    return [s] if s else []


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s or "unknown"


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    t = text.lower()
    return any(term in t for term in terms)


def _dietary_flags(vegan: str | None, vegetarian: str | None) -> dict[str, Any]:
    flags: dict[str, Any] = {
        "animal_origin": False,
        "plant_origin": False,
        "uncertainty_flags": [],
        "uncertain": False,
    }
    vegan_l = (vegan or "").strip().lower()
    veg_l = (vegetarian or "").strip().lower()

    if vegan_l == "yes":
        flags["plant_origin"] = True
        flags["animal_origin"] = False
    elif vegan_l == "no":
        flags["animal_origin"] = True
        flags["plant_origin"] = False
    elif vegan_l == "maybe":
        flags["uncertainty_flags"].append("may_contain_animal_derivatives")
        flags["uncertain"] = True

    if veg_l == "no" and vegan_l == "no":
        flags["animal_origin"] = True
        flags["plant_origin"] = False

    if not vegan_l and not veg_l:
        flags["uncertain"] = True
    elif vegan_l not in ("yes", "no", "maybe", "") or veg_l not in ("yes", "no", ""):
        if vegan_l not in ("yes", "no", "maybe"):
            flags["uncertain"] = True
        if veg_l and veg_l not in ("yes", "no"):
            flags["uncertain"] = True

    return flags


def _apply_special_classifications(ing: dict[str, Any], english_name: str) -> None:
    canon = ing["canonical_name"]
    original = english_name.lower()

    if _contains_any(canon, _DAIRY_TERMS):
        ing["dairy_source"] = True
        ing["animal_origin"] = True

    if _contains_any(canon, _EGG_TERMS):
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


def _base_ingredient(
    off_key: str,
    english_name: str,
    aliases: list[str],
    dietary: dict[str, Any],
    wikidata_id: str | None,
) -> dict[str, Any]:
    canonical = english_name.lower().strip()
    seen_aliases: set[str] = set()
    out_aliases: list[str] = []
    for a in [english_name] + aliases:
        a = a.strip()
        if not a:
            continue
        key = a.lower()
        if key not in seen_aliases:
            out_aliases.append(a)
            seen_aliases.add(key)

    ing: dict[str, Any] = {
        "id": slugify(english_name),
        "canonical_name": canonical,
        "aliases": out_aliases,
        "animal_origin": dietary["animal_origin"],
        "plant_origin": dietary["plant_origin"],
        "synthetic": False,
        "fungal": False,
        "insect_derived": False,
        "egg_source": False,
        "dairy_source": False,
        "gluten_source": False,
        "soy_source": False,
        "sesame_source": False,
        "nut_source": None,
        "alcohol_content": None,
        "root_vegetable": False,
        "onion_source": False,
        "garlic_source": False,
        "fermented": False,
        "uncertainty_flags": list(dietary["uncertainty_flags"]),
        "derived_from": [],
        "contains": [],
        "may_contain": [],
        "regions": ["Global"],
        "_source": "open_food_facts",
        "_off_id": off_key,
        "_wikidata": wikidata_id,
    }
    _apply_special_classifications(ing, english_name)
    return ing


def parse_off_taxonomy(taxonomy: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    stats = {
        "total_off_entries": len(taxonomy),
        "skipped_no_english": 0,
        "skipped_category": 0,
        "skipped_too_short": 0,
        "valid": 0,
        "animal_origin": 0,
        "plant_origin": 0,
        "uncertain": 0,
    }
    ingredients: list[dict[str, Any]] = []
    seen_ids: dict[str, int] = {}

    for off_key, entry in taxonomy.items():
        if not isinstance(entry, dict):
            continue
        if off_key.startswith("en:categories:"):
            stats["skipped_category"] += 1
            continue

        english_name = _lang_val(entry.get("name"))
        if not english_name:
            stats["skipped_no_english"] += 1
            continue

        cleaned = re.sub(r"\s+", " ", english_name).strip()
        if len(cleaned) < 3:
            stats["skipped_too_short"] += 1
            continue

        vegan = _lang_val(entry.get("vegan"))
        vegetarian = _lang_val(entry.get("vegetarian"))
        dietary = _dietary_flags(vegan, vegetarian)
        synonyms = _lang_list(entry.get("synonyms"))
        wikidata_id = _lang_val(entry.get("wikidata"))

        ing = _base_ingredient(off_key, cleaned, synonyms, dietary, wikidata_id)

        base_id = ing["id"]
        if base_id in seen_ids:
            seen_ids[base_id] += 1
            ing["id"] = f"{base_id}_{seen_ids[base_id]}"
        else:
            seen_ids[base_id] = 1

        if ing["animal_origin"]:
            stats["animal_origin"] += 1
        if ing["plant_origin"]:
            stats["plant_origin"] += 1
        if dietary["uncertain"]:
            stats["uncertain"] += 1

        ingredients.append(ing)
        stats["valid"] += 1

    return ingredients, stats


def _print_summary(stats: dict[str, int]) -> None:
    print(f"Total OFF entries processed: {stats['total_off_entries']}")
    print(f"Valid ingredients extracted:   {stats['valid']}")
    print(f"Skipped (no English name):     {stats['skipped_no_english']}")
    print(f"Skipped (category, not ingredient): {stats['skipped_category']}")
    print(f"Skipped (name < 3 chars):      {stats['skipped_too_short']}")
    print(f"Animal origin count:           {stats['animal_origin']}")
    print(f"Plant origin count:            {stats['plant_origin']}")
    print(f"Uncertain count:               {stats['uncertain']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse OFF ingredients taxonomy to IngreSure staging JSON",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=_DEFAULT_INPUT,
        help=f"OFF taxonomy JSON (default: {_DEFAULT_INPUT.relative_to(_REPO)})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help=f"Staging output path (default: {_DEFAULT_OUTPUT.relative_to(_REPO)})",
    )
    args = parser.parse_args()

    if not args.input.exists():
        for alt in (
            _REPO / "data" / "off_ingredients_taxonomy.json",
            _REPO / "data" / "raw" / "off_ingredients_taxonomy.json",
        ):
            if alt.exists():
                args.input = alt
                print(f"Using {args.input}", file=sys.stderr)
                break
        else:
            print(f"Input not found: {args.input}", file=sys.stderr)
            print("Download: curl -L ... -o backend/data/off_ingredients_taxonomy.json", file=sys.stderr)
            return 1

    with args.input.open(encoding="utf-8") as f:
        taxonomy = json.load(f)
    if not isinstance(taxonomy, dict):
        print("Expected top-level JSON object (taxonomy dict).", file=sys.stderr)
        return 1

    ingredients, stats = parse_off_taxonomy(taxonomy)
    payload = {
        "source": "open_food_facts",
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
