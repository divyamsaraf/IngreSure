#!/usr/bin/env python3
"""
Merge E-number catalog into data/ontology.json.

- Existing entries (by id, canonical_name, or alias): merge aliases/flags only.
- merge_into in catalog: add aliases to that ontology id (no duplicate group).
- New substances: append full Ingredient-shaped entry.

Run from repo root:
  python3 scripts/merge_e_numbers_to_ontology.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ONTOLOGY_PATH = REPO / "data" / "ontology.json"
CATALOG_PATH = REPO / "data" / "e_number_catalog.json"

DEFAULT_ENTRY = {
    "derived_from": [],
    "contains": [],
    "may_contain": [],
    "animal_origin": False,
    "plant_origin": False,
    "synthetic": False,
    "fungal": False,
    "insect_derived": False,
    "animal_species": None,
    "egg_source": False,
    "dairy_source": False,
    "gluten_source": False,
    "nut_source": None,
    "soy_source": False,
    "sesame_source": False,
    "alcohol_content": None,
    "root_vegetable": False,
    "onion_source": False,
    "garlic_source": False,
    "fermented": False,
    "uncertainty_flags": [],
    "regions": [],
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _slug(name: str) -> str:
    s = _norm(name)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unknown"


def _e_id(e_code: str) -> str:
    return _norm(e_code).replace(" ", "")


def _build_index(ingredients: list[dict]) -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for ing in ingredients:
        for key in {_norm(ing["id"]), _norm(ing["canonical_name"])}:
            idx.setdefault(key, ing)
        for alias in ing.get("aliases") or []:
            idx.setdefault(_norm(alias), ing)
    return idx


def _merge_flags(existing: dict, incoming: dict) -> None:
    """OR boolean flags; merge lists; prefer incoming animal_species/nut_source if set."""
    for flag in (
        "animal_origin", "plant_origin", "synthetic", "fungal", "insect_derived",
        "egg_source", "dairy_source", "gluten_source", "soy_source", "sesame_source",
        "root_vegetable", "onion_source", "garlic_source", "fermented",
    ):
        if incoming.get(flag):
            existing[flag] = True
    for optional in ("animal_species", "nut_source", "alcohol_content"):
        if incoming.get(optional) is not None:
            existing[optional] = incoming[optional]
    for list_field in ("uncertainty_flags", "regions"):
        merged = list(existing.get(list_field) or [])
        for item in incoming.get(list_field) or []:
            if item not in merged:
                merged.append(item)
        existing[list_field] = merged


def _add_aliases(existing: dict, aliases: list[str]) -> int:
    current = list(existing.get("aliases") or [])
    seen = {_norm(a) for a in current}
    seen.add(_norm(existing["canonical_name"]))
    seen.add(_norm(existing["id"]))
    added = 0
    for alias in aliases:
        if not alias or _norm(alias) in seen:
            continue
        current.append(alias)
        seen.add(_norm(alias))
        added += 1
    existing["aliases"] = current
    return added


def merge_catalog(ontology: dict, catalog: dict) -> dict[str, int]:
    ingredients: list[dict] = ontology["ingredients"]
    by_id = {ing["id"]: ing for ing in ingredients}
    index = _build_index(ingredients)

    stats = {"merged": 0, "created": 0, "aliases_added": 0, "skipped": 0}

    for raw in catalog.get("entries") or []:
        e_code = raw.get("e_code") or ""
        merge_into = raw.get("merge_into")
        aliases = list(raw.get("aliases") or [])
        if e_code and e_code not in aliases:
            aliases.insert(0, e_code)

        target: dict | None = None
        if merge_into and merge_into in by_id:
            target = by_id[merge_into]
        else:
            probe_keys = [_e_id(e_code), _norm(raw.get("canonical_name", ""))]
            probe_keys.extend(_norm(a) for a in aliases[:3])
            for key in probe_keys:
                if key and key in index:
                    target = index[key]
                    break
            if target is None and _e_id(e_code) in by_id:
                target = by_id[_e_id(e_code)]

        incoming = {**DEFAULT_ENTRY, **{k: v for k, v in raw.items() if k not in ("e_code", "merge_into")}}

        if target is not None:
            added = _add_aliases(target, aliases)
            _merge_flags(target, incoming)
            stats["merged"] += 1
            stats["aliases_added"] += added
            continue

        entry_id = _e_id(e_code) if e_code else _slug(raw.get("canonical_name", ""))
        if entry_id in by_id:
            added = _add_aliases(by_id[entry_id], aliases)
            _merge_flags(by_id[entry_id], incoming)
            stats["merged"] += 1
            stats["aliases_added"] += added
            continue

        canonical = _norm(raw.get("canonical_name") or entry_id)
        new_entry = {
            "id": entry_id,
            "canonical_name": canonical,
            "aliases": [],
            **DEFAULT_ENTRY,
            **{k: v for k, v in incoming.items() if k != "canonical_name"},
        }
        _add_aliases(new_entry, aliases)
        ingredients.append(new_entry)
        by_id[entry_id] = new_entry
        for key in {_norm(entry_id), canonical, *(_norm(a) for a in new_entry["aliases"])}:
            index[key] = new_entry
        stats["created"] += 1
        stats["aliases_added"] += len(new_entry["aliases"])

    return stats


def main() -> int:
    if not CATALOG_PATH.exists():
        print(f"Missing catalog: {CATALOG_PATH}", file=sys.stderr)
        return 1
    if not ONTOLOGY_PATH.exists():
        print(f"Missing ontology: {ONTOLOGY_PATH}", file=sys.stderr)
        return 1

    ontology = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    before = len(ontology["ingredients"])
    stats = merge_catalog(ontology, catalog)
    after = len(ontology["ingredients"])

    ontology["ontology_version"] = "1.2"
    ONTOLOGY_PATH.write_text(
        json.dumps(ontology, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Done: {before} -> {after} ingredients | "
        f"created={stats['created']} merged={stats['merged']} "
        f"aliases_added={stats['aliases_added']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
