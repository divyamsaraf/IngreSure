from __future__ import annotations

from typing import Any

ALLERGEN_ADJACENT_FLAGS: frozenset[str] = frozenset({
    "peanut_source", "tree_nut_source", "sesame_source", "soy_source",
    "gluten_source", "mustard_source", "celery_source", "lupin_source",
    "sulphite_source", "fish_source", "shellfish_source",
})
MOLLUSC_SPECIES: frozenset[str] = frozenset({"mollusk", "mollusc"})
ANIMALISH_FLAGS: frozenset[str] = frozenset({
    "animal_origin", "egg_source", "fish_source", "shellfish_source",
    "insect_derived", "bee_product", "dairy_source",
})


def is_allergen_adjacent(flags: dict[str, Any] | None) -> bool:
    f = flags or {}
    if any(f.get(k) for k in ALLERGEN_ADJACENT_FLAGS):
        return True
    species = str(f.get("animal_species") or "").lower().strip()
    return species in MOLLUSC_SPECIES


def is_animalish(flags: dict[str, Any] | None) -> bool:
    f = flags or {}
    if any(f.get(k) for k in ANIMALISH_FLAGS):
        return True
    species = str(f.get("animal_species") or "").lower().strip()
    return bool(species) and species not in ("", "none")
