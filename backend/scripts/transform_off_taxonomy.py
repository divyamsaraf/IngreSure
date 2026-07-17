#!/usr/bin/env python3
"""
Transform Open Food Facts ingredients taxonomy → Layer 1 ingest JSON.

Input:  data/raw/off_ingredients_taxonomy.json (CC0)
Output: data/layer1_off_taxonomy.json

Run from repo root:
  python backend/scripts/transform_off_taxonomy.py
  python backend/scripts/transform_off_taxonomy.py --input data/raw/off_ingredients_taxonomy.json --output data/layer1_off_taxonomy.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
sys.path.insert(0, str(_backend))

from core.normalization.normalizer import normalize_ingredient_key, is_plausible_e_number_code

_DEFAULT_INPUT = _repo / "data" / "raw" / "off_ingredients_taxonomy.json"
_DEFAULT_OUTPUT = _repo / "data" / "layer1_off_taxonomy.json"

_ALLERGEN_MAP = {
    "en:gluten": "gluten",
    "en:milk": "dairy",
    "en:soybeans": "soy",
    "en:eggs": "egg",
    "en:fish": "fish",
    "en:crustaceans": "shellfish",
    "en:peanuts": "peanut",
    "en:nuts": "tree_nut",
    "en:sesame-seeds": "sesame",
    "en:mustard": "mustard",
}

_PLANT_PARENT_HINTS = frozenset({
    "cereal", "vegetable", "fruit", "legume", "pulse", "nut", "seed", "spice", "herb",
    "plant", "mushroom", "algae", "seaweed", "grain", "oil", "starch", "flour",
    "sugar", "honey", "cocoa", "coffee", "tea",
})

_ANIMAL_PARENT_HINTS = frozenset({
    "meat", "fish", "poultry", "seafood", "shellfish", "dairy", "egg", "milk", "cheese",
    "honey",  # debated; OFF often marks separately
})


def _lang_val(field: Any, lang: str = "en") -> str | None:
    if field is None:
        return None
    if isinstance(field, dict):
        v = field.get(lang) or field.get("en")
        return str(v).strip() if v else None
    s = str(field).strip()
    return s or None


def _slug_from_taxonomy_key(key: str) -> str:
    if ":" in key:
        return key.split(":", 1)[1].replace("-", " ")
    return key.replace("-", " ")


def _collect_aliases(entry: dict[str, Any], taxonomy_key: str) -> list[str]:
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

    names = entry.get("name") or {}
    if isinstance(names, dict):
        for _lang, val in names.items():
            add(val if isinstance(val, str) else None)

    e_num = entry.get("e_number") or {}
    if isinstance(e_num, dict):
        add(_lang_val(e_num))

    add(_slug_from_taxonomy_key(taxonomy_key))
    return aliases


def _flags_from_off(entry: dict[str, Any]) -> dict[str, Any]:
    vegan = _lang_val(entry.get("vegan"))
    vegetarian = _lang_val(entry.get("vegetarian"))
    uncertainty: list[str] = []

    if vegan == "maybe":
        uncertainty.append("off_maybe_vegan")
    if vegetarian == "maybe":
        uncertainty.append("off_maybe_vegetarian")

    plant_origin = False
    animal_origin = False
    dairy_source = False
    egg_source = False
    gluten_source = False
    soy_source = False
    sesame_source = False
    nut_source: str | None = None
    animal_species: str | None = None
    insect_derived = False

    if vegan == "yes":
        plant_origin, animal_origin = True, False
    elif vegan == "no":
        animal_origin = True
    elif vegetarian == "no" and vegan != "yes":
        animal_origin = True

    allergen_field = entry.get("allergens")
    allergen_tokens: list[str] = []
    if isinstance(allergen_field, dict):
        for v in allergen_field.values():
            if v:
                allergen_tokens.append(str(v).strip().lower())
    elif allergen_field:
        allergen_tokens.append(str(allergen_field).strip().lower())

    for token in allergen_tokens:
        for prefix, kind in _ALLERGEN_MAP.items():
            if prefix in token or kind in token:
                if kind == "gluten":
                    gluten_source = True
                elif kind == "dairy":
                    dairy_source = True
                    animal_origin = True
                elif kind == "soy":
                    soy_source = True
                elif kind == "egg":
                    egg_source = True
                    animal_origin = True
                elif kind == "fish":
                    animal_origin = True
                    animal_species = "fish"
                elif kind == "shellfish":
                    animal_origin = True
                    animal_species = "shellfish"
                elif kind == "peanut":
                    nut_source = "peanut"
                elif kind == "tree_nut":
                    nut_source = nut_source or "tree_nut"
                elif kind == "sesame":
                    sesame_source = True

    comment = _lang_val(entry.get("comment")) or ""
    if "does not contain gluten" in comment.lower():
        gluten_source = False

    if insect_derived or "insect" in (_lang_val(entry.get("description")) or "").lower():
        insect_derived = "carmine" in (_lang_val(entry.get("name")) or "").lower() or "cochineal" in comment.lower()

    parents = entry.get("parents") or []
    derived_from: list[str] = []
    parent_slugs: list[str] = []
    for p in parents:
        if isinstance(p, str):
            slug = _slug_from_taxonomy_key(p)
            derived_from.append(slug)
            parent_slugs.append(slug)

    if not plant_origin and not animal_origin and vegan not in ("yes", "no", "maybe"):
        for slug in parent_slugs:
            tokens = set(slug.replace(",", " ").split())
            if tokens & _PLANT_PARENT_HINTS or any(h in slug for h in _PLANT_PARENT_HINTS):
                plant_origin = True
                break
            if tokens & _ANIMAL_PARENT_HINTS or any(h in slug for h in _ANIMAL_PARENT_HINTS):
                animal_origin = True
                if "dairy" in slug or "milk" in slug or "cheese" in slug:
                    dairy_source = True
                if "egg" in slug:
                    egg_source = True
                break

    return {
        "plant_origin": plant_origin,
        "animal_origin": animal_origin,
        "dairy_source": dairy_source,
        "egg_source": egg_source,
        "gluten_source": gluten_source,
        "soy_source": soy_source,
        "sesame_source": sesame_source,
        "nut_source": nut_source,
        "animal_species": animal_species,
        "insect_derived": insect_derived,
        "synthetic": bool(entry.get("e_number")),
        "uncertainty_flags": uncertainty,
        "derived_from": derived_from,
    }


def _should_include(entry: dict[str, Any], taxonomy_key: str, canonical: str) -> bool:
    if not canonical:
        return False
    if entry.get("e_number") or taxonomy_key.startswith("en:e"):
        return is_plausible_e_number_code(canonical) or canonical.upper().startswith("E")
    if _lang_val(entry.get("vegan")) or _lang_val(entry.get("vegetarian")):
        return True
    if entry.get("allergens"):
        return True
    if len(canonical) > 120 or len(canonical.split()) > 8:
        return False
    return taxonomy_key.startswith("en:")


def transform_off_taxonomy(taxonomy: dict[str, Any]) -> list[dict[str, Any]]:
    """Build Layer 1 rows keyed by English canonical name."""
    by_canon: dict[str, dict[str, Any]] = {}

    for key, entry in taxonomy.items():
        if not isinstance(entry, dict):
            continue
        canonical = _lang_val(entry.get("name"))
        if not canonical:
            continue
        if not _should_include(entry, key, canonical):
            continue

        norm = normalize_ingredient_key(canonical)
        if not norm:
            continue

        aliases = _collect_aliases(entry, key)
        flags = _flags_from_off(entry)

        if norm not in by_canon:
            by_canon[norm] = {
                "canonical_name": canonical,
                "aliases": [],
                "source": "open_food_facts",
                **flags,
            }
        row = by_canon[norm]
        existing_norms = {normalize_ingredient_key(a) for a in row["aliases"]}
        for a in aliases:
            an = normalize_ingredient_key(a)
            if an and an not in existing_norms and an != norm:
                row["aliases"].append(a)
                existing_norms.add(an)
        for uf in flags.get("uncertainty_flags") or []:
            if uf not in row["uncertainty_flags"]:
                row["uncertainty_flags"].append(uf)

    # Second pass: attach regional-only entries as aliases on English parent
    for key, entry in taxonomy.items():
        if not isinstance(entry, dict):
            continue
        if _lang_val(entry.get("name")):
            continue
        parents = entry.get("parents") or []
        parent_canon: str | None = None
        for p in parents:
            if not isinstance(p, str) or not p.startswith("en:"):
                continue
            parent_entry = taxonomy.get(p)
            if isinstance(parent_entry, dict):
                parent_canon = _lang_val(parent_entry.get("name"))
                if parent_canon:
                    break
        if not parent_canon:
            continue
        pn = normalize_ingredient_key(parent_canon)
        if pn not in by_canon:
            continue
        for a in _collect_aliases(entry, key):
            existing = {normalize_ingredient_key(x) for x in by_canon[pn]["aliases"]}
            an = normalize_ingredient_key(a)
            if an and an not in existing and an != pn:
                by_canon[pn]["aliases"].append(a)

    rows = sorted(by_canon.values(), key=lambda r: r["canonical_name"].lower())
    for row in rows:
        row["aliases"] = row["aliases"][:50]
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Transform OFF taxonomy to Layer 1 JSON")
    parser.add_argument("--input", type=Path, default=_DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input not found: {args.input}", file=sys.stderr)
        print("Run: ./scripts/download_tier1_data.sh", file=sys.stderr)
        return 1

    taxonomy = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(taxonomy, dict):
        print("Expected taxonomy JSON object", file=sys.stderr)
        return 1

    rows = transform_off_taxonomy(taxonomy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(rows)} groups to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
