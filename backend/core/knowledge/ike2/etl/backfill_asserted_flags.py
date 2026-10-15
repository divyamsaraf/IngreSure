"""True-only asserted_flags backfill for ontology ingredient rows (Item 11 §5).

A stored ``true`` cannot come from the dataclass default, so marking it asserted
is honest. A stored ``false`` stays unasserted — guessing would invent curation.
"""
from __future__ import annotations

from typing import Any


# Boolean columns that appear flat on ontology rows and/or under nested ``flags``.
_ONTOLOGY_BOOL_FLAGS = (
    "animal_origin",
    "plant_origin",
    "synthetic",
    "fungal",
    "insect_derived",
    "bee_product",
    "egg_source",
    "dairy_source",
    "gluten_source",
    "soy_source",
    "sesame_source",
    "peanut_source",
    "tree_nut_source",
    "fish_source",
    "shellfish_source",
    "mustard_source",
    "celery_source",
    "lupin_source",
    "sulphite_source",
    "root_vegetable",
    "onion_source",
    "garlic_source",
    "fermented",
    "enzyme_animal_source",
    "enzyme_microbial_source",
)


def true_flags_on_row(row: dict[str, Any]) -> set[str]:
    """Names of boolean columns whose stored value is True (flat or nested flags)."""
    found: set[str] = set()
    nested = row.get("flags")
    nested = nested if isinstance(nested, dict) else {}
    for name in _ONTOLOGY_BOOL_FLAGS:
        if row.get(name) is True or nested.get(name) is True:
            found.add(name)
    return found


def backfill_asserted_flags_on_row(row: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``row`` with asserted_flags unioned with all true bools.

    Idempotent: re-running does not add falses or duplicate names.
    Never marks a false as asserted.
    """
    out = dict(row)
    prior = set(out.get("asserted_flags") or [])
    trues = true_flags_on_row(out)
    # Do not treat prior asserted falses specially here — we only add trues.
    out["asserted_flags"] = sorted(prior | trues)
    return out


def backfill_ontology_ingredients(ingredients: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [backfill_asserted_flags_on_row(row) for row in ingredients]
