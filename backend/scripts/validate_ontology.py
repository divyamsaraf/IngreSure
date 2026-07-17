#!/usr/bin/env python3
"""Validate data/ontology.json structure and semantic consistency before seeding Supabase."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent.parent
_BACKEND = _REPO / "backend"
sys.path.insert(0, str(_BACKEND))

from core.config import get_ontology_path

_BOOLEAN_FLAGS = (
    "animal_origin", "plant_origin", "synthetic", "fungal", "insect_derived",
    "egg_source", "dairy_source", "gluten_source", "soy_source", "sesame_source",
    "root_vegetable", "onion_source", "garlic_source", "fermented",
)
_VALID_KNOWLEDGE_STATES = frozenset({"UNKNOWN", "DISCOVERED", "AUTO_CLASSIFIED", "VERIFIED", "LOCKED"})
_ORIGIN_FLAGS = ("animal_origin", "plant_origin", "synthetic", "fungal")


def _norm_name(value: str) -> str:
    return (value or "").strip().lower()


def validate_schema(ingredients: list[dict]) -> list[str]:
    """Structural / schema checks (original validate logic)."""
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

        keys = list(ing.get("aliases") or []) + [ing.get("canonical_name", "")]
        for alias in keys:
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


def _all_origin_false(entry: dict[str, Any]) -> bool:
    return not any(entry.get(flag) for flag in _ORIGIN_FLAGS)


def _entry_names(entry: dict[str, Any]) -> set[str]:
    names = {_norm_name(entry.get("canonical_name", "")), _norm_name(entry.get("id", ""))}
    names.update(_norm_name(a) for a in (entry.get("aliases") or []) if a)
    names.discard("")
    return names


def find_entries_by_term(ingredients: list[dict], term: str) -> list[dict]:
    needle = _norm_name(term)
    if not needle:
        return []
    return [ing for ing in ingredients if needle in _entry_names(ing)]


def validate_semantic(ingredients: list[dict]) -> list[str]:
    """Semantic consistency checks — HIGH tier."""
    errors: list[str] = []

    for ing in ingredients:
        name = ing.get("canonical_name") or ing.get("id") or "?"

        if ing.get("insect_derived") and not ing.get("animal_origin"):
            errors.append(f"insect_derived=true but animal_origin=false: {name}")

        if ing.get("egg_source") and not ing.get("animal_origin"):
            errors.append(f"egg_source=true but animal_origin=false: {name}")

        if ing.get("dairy_source") and not ing.get("animal_origin"):
            errors.append(f"dairy_source=true but animal_origin=false: {name}")

        if ing.get("animal_origin") and ing.get("plant_origin"):
            flags = ing.get("uncertainty_flags") or []
            if "animal_or_plant_source_unspecified" not in flags:
                errors.append(f"dual animal+plant without uncertainty flag: {name}")

        if _all_origin_false(ing):
            flags = ing.get("uncertainty_flags") or []
            if not flags:
                errors.append(f"all origin flags false with no uncertainty flag: {name}")

    return errors


def check_truth(
    ingredients: list[dict],
    term: str,
    field: str,
    expected: bool | str,
) -> list[str]:
    """Known-truth field check — CRITICAL tier."""
    matches = find_entries_by_term(ingredients, term)
    if not matches:
        return [f"CRITICAL: no entry found for truth check {term!r}"]

    errors: list[str] = []
    for ing in matches:
        actual = ing.get(field)
        name = ing.get("canonical_name") or ing.get("id")
        if actual != expected:
            errors.append(
                f"CRITICAL: {term!r} ({name}) expected {field}={expected!r}, got {actual!r}"
            )
    return errors


def check_has_flag(ingredients: list[dict], term: str, flag: str) -> list[str]:
    """Known-truth uncertainty flag check — CRITICAL tier."""
    matches = find_entries_by_term(ingredients, term)
    if not matches:
        return [f"CRITICAL: no entry found for flag check {term!r}"]

    errors: list[str] = []
    for ing in matches:
        flags = ing.get("uncertainty_flags") or []
        name = ing.get("canonical_name") or ing.get("id")
        if flag not in flags:
            errors.append(
                f"CRITICAL: {term!r} ({name}) missing uncertainty_flag {flag!r}; has {flags!r}"
            )
    return errors


def validate_known_truth(ingredients: list[dict]) -> list[str]:
    """Known-truth checks — CRITICAL tier."""
    errors: list[str] = []

    truth_checks: list[tuple[str, str, bool | str]] = [
        # Must be animal_origin: true
        ("gelatin", "animal_origin", True),
        ("lard", "animal_origin", True),
        ("tallow", "animal_origin", True),
        ("beeswax", "insect_derived", True),
        ("carmine", "insect_derived", True),
        ("shellac", "insect_derived", True),
        ("ghee", "dairy_source", True),
        ("ghee", "animal_origin", True),
        ("paneer", "dairy_source", True),
        ("whey", "dairy_source", True),
        ("casein", "dairy_source", True),
        ("lactose", "dairy_source", True),
        ("honey", "animal_origin", True),
        # Must be plant_origin: true
        ("agar", "plant_origin", True),
        ("carrageenan", "plant_origin", True),
        ("pectin", "plant_origin", True),
        # Must NOT be animal_origin
        ("cocoa butter", "animal_origin", False),
        ("coconut milk", "animal_origin", False),
        ("peanut butter", "animal_origin", False),
        # Allergen flags
        ("peanut", "nut_source", "peanut"),
        ("wheat", "gluten_source", True),
        ("sesame", "sesame_source", True),
        ("soybean", "soy_source", True),
        ("milk", "dairy_source", True),
        ("egg", "egg_source", True),
        # India-specific
        ("asafoetida", "root_vegetable", True),
        ("asafoetida", "gluten_source", True),
        ("besan", "gluten_source", False),
        ("rice flour", "gluten_source", False),
    ]

    for term, field, expected in truth_checks:
        errors.extend(check_truth(ingredients, term, field, expected))

    flag_checks: list[tuple[str, str]] = [
        ("natural flavors", "may_contain_animal_derivatives"),
        ("mono and diglycerides", "animal_or_plant_source_unspecified"),
        ("lecithin", "soy_or_egg_or_sunflower_source_unspecified"),
    ]

    for term, flag in flag_checks:
        errors.extend(check_has_flag(ingredients, term, flag))

    return errors


def _print_errors(label: str, errors: list[str], limit: int = 20) -> None:
    print(f"  {label}: {len(errors)}")
    if errors:
        print(f"\n{label} (first {min(limit, len(errors))}):")
        for err in errors[:limit]:
            print(f"  - {err}")
        if len(errors) > limit:
            print(f"  ... and {len(errors) - limit} more")


def main() -> int:
    path = get_ontology_path()
    if not path.exists():
        print(f"ERROR: ontology not found at {path}")
        return 1

    data = json.loads(path.read_text(encoding="utf-8"))
    ingredients = data.get("ingredients") or []

    schema_errors = validate_schema(ingredients)
    high_errors = validate_semantic(ingredients)
    critical_errors = validate_known_truth(ingredients)

    all_false = sum(1 for e in ingredients if _all_origin_false(e))
    dual = sum(1 for e in ingredients if e.get("animal_origin") and e.get("plant_origin"))
    empty_aliases = sum(1 for e in ingredients if not e.get("aliases"))

    print(f"Ontology: {path}")
    print(f"  Entries: {len(ingredients)}")
    print()
    print("INFO (statistics):")
    print(f"  All origin flags false: {all_false}")
    print(f"  Dual animal+plant: {dual}")
    print(f"  Empty aliases: {empty_aliases}")
    print()
    print("VALIDATION SUMMARY:")
    _print_errors("Schema errors", schema_errors)
    _print_errors("CRITICAL errors (known truth failures)", critical_errors)
    _print_errors("HIGH errors (semantic consistency)", high_errors)

    critical_count = len(critical_errors)
    high_count = len(high_errors)
    schema_count = len(schema_errors)

    print()
    if schema_count == 0 and critical_count == 0 and high_count == 0:
        print("OVERALL: PASS (exit 0)")
        return 0

    print("OVERALL: FAIL (exit 1)")
    if schema_count:
        print(f"  Schema errors: {schema_count}")
    if critical_count:
        print(f"  CRITICAL errors: {critical_count}")
    if high_count:
        print(f"  HIGH errors: {high_count}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
