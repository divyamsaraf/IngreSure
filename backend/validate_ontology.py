#!/usr/bin/env python3
"""Validate data/ontology.json structure before seeding Supabase."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent
sys.path.insert(0, str(_backend))

from core.config import get_ontology_path

_BOOLEAN_FLAGS = (
    "animal_origin", "plant_origin", "synthetic", "fungal", "insect_derived",
    "egg_source", "dairy_source", "gluten_source", "soy_source", "sesame_source",
    "root_vegetable", "onion_source", "garlic_source", "fermented",
)
_VALID_KNOWLEDGE_STATES = frozenset({"UNKNOWN", "DISCOVERED", "AUTO_CLASSIFIED", "VERIFIED", "LOCKED"})


def _norm_name(value: str) -> str:
    return (value or "").strip().lower()


def validate(ingredients: list[dict]) -> list[str]:
    errors: list[str] = []
    seen_ids: dict[str, str] = {}
    seen_canonical: dict[str, str] = {}
    alias_owner: dict[str, str] = {}

    for ing in ingredients:
        entry_id = ing.get("id") or ""
        canonical = _norm_name(ing.get("canonical_name") or "")

        if not entry_id:
            errors.append("Entry missing id")
            continue
        if entry_id in seen_ids:
            errors.append(f"Duplicate id {entry_id!r} ({seen_ids[entry_id]} and {canonical})")
        else:
            seen_ids[entry_id] = canonical

        if not canonical:
            errors.append(f"Entry {entry_id!r} missing canonical_name")
        elif canonical in seen_canonical:
            errors.append(
                f"Duplicate canonical_name {canonical!r} "
                f"({seen_canonical[canonical]} and {entry_id})"
            )
        else:
            seen_canonical[canonical] = entry_id

        state = ing.get("knowledge_state")
        if state and state not in _VALID_KNOWLEDGE_STATES:
            errors.append(f"Entry {entry_id!r} invalid knowledge_state: {state!r}")

        for flag in _BOOLEAN_FLAGS:
            val = ing.get(flag)
            if val is not None and not isinstance(val, bool):
                errors.append(f"Entry {entry_id!r} field {flag} is not bool: {val!r}")

        for alias in ing.get("aliases") or []:
            alias_norm = _norm_name(alias)
            if not alias_norm:
                continue
            if alias_norm in alias_owner and alias_owner[alias_norm] != entry_id:
                errors.append(
                    f"Alias {alias!r} shared by {alias_owner[alias_norm]!r} and {entry_id!r}"
                )
            else:
                alias_owner[alias_norm] = entry_id

    return errors


def main() -> int:
    path = get_ontology_path()
    if not path.exists():
        print(f"ERROR: ontology not found at {path}")
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    ingredients = data.get("ingredients") or []
    errors = validate(ingredients)

    all_false = sum(
        1 for e in ingredients
        if not any([e.get("animal_origin"), e.get("plant_origin"), e.get("synthetic"), e.get("fungal")])
    )
    dual = sum(1 for e in ingredients if e.get("animal_origin") and e.get("plant_origin"))
    empty_aliases = sum(1 for e in ingredients if not e.get("aliases"))

    print(f"Ontology: {path}")
    print(f"  Entries: {len(ingredients)}")
    print(f"  All origin flags false: {all_false}")
    print(f"  Dual animal+plant: {dual}")
    print(f"  Empty aliases: {empty_aliases}")
    print(f"  Validation errors: {len(errors)}")

    if errors:
        print("\nFirst errors:")
        for err in errors[:20]:
            print(f"  - {err}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
