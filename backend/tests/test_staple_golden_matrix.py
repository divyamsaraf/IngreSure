"""L1 staple × restriction golden matrix.

Hand-written expectations for class-level L1 staples against the 15 pilot
restrictions. Firm SAFE where the table says hazard or uncertain fails.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import rules as rules_module
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.verdict import to_external

# Pilot set: 9 allergen/medical + 6 diet/religious.
MATRIX_RESTRICTIONS = (
    "peanut_allergy",
    "tree_nut_allergy",
    "soy_allergy",
    "sesame_allergy",
    "fish_allergy",
    "shellfish_allergy",
    "gluten_free",
    "dairy_free",
    "egg_free",
    "vegan",
    "jain",
    "halal",
    "hindu_vegetarian",
    "vegetarian",
    "kosher",
)

# Severity: medical for allergy/medical; preference/religious for diets.
_SEVERITY = {
    **{r: "medical" for r in MATRIX_RESTRICTIONS if r.endswith("_allergy") or r in (
        "gluten_free", "dairy_free", "egg_free",
    )},
    "vegan": "preference",
    "vegetarian": "preference",
    "jain": "religious",
    "halal": "religious",
    "hindu_vegetarian": "religious",
    "kosher": "religious",
}


def _cell(atom: str, rid: str) -> str:
    cache.clear()
    rules = rules_module.seeded_rules()
    ci = to_compliance_input(resolve(atom, None), query_atom=atom)
    return to_external(
        evaluate(
            [ci],
            SimpleNamespace(restrictions={rid: _SEVERITY[rid]}),
            rules,
        ).verdict
    )


def _safe_row(**overrides: str) -> dict[str, str]:
    row = {r: "SAFE" for r in MATRIX_RESTRICTIONS}
    row.update(overrides)
    return row


# Hand table. Keys are query atoms (aliases resolve to the L1 canonical).
# Sugar: plant SAFE for vegan/jain/halal; bone-char is process ambiguity
# surfaced as informational_ingredients (see test_sugar_bone_char_informational).
EXPECTATIONS: dict[str, dict[str, str]] = {
    "flour": _safe_row(gluten_free="NOT_SAFE"),
    "flours": _safe_row(gluten_free="NOT_SAFE"),
    "wheatberries": _safe_row(gluten_free="NOT_SAFE"),
    "yeast": _safe_row(jain="NOT_SAFE"),
    "yeast extract": _safe_row(jain="NOT_SAFE"),
    "sugar": _safe_row(),
    "cane sugar": _safe_row(),
    "beet sugar": _safe_row(),
    "vegetable oil": _safe_row(
        peanut_allergy="UNCERTAIN",
        sesame_allergy="UNCERTAIN",
        soy_allergy="UNCERTAIN",
        tree_nut_allergy="UNCERTAIN",
    ),
    "sunflower oil": _safe_row(),
    "rapeseed oil": _safe_row(),
    "soybean oil": _safe_row(soy_allergy="NOT_SAFE"),
    "almond oil": _safe_row(tree_nut_allergy="NOT_SAFE"),
    "walnut oil": _safe_row(tree_nut_allergy="NOT_SAFE"),
    "sesame oil": _safe_row(sesame_allergy="NOT_SAFE"),
    # Origin uncertainty_flags also ceiling dairy_free/egg_free (engine rule).
    "vitamin b2": _safe_row(
        vegan="UNCERTAIN",
        jain="UNCERTAIN",
        halal="UNCERTAIN",
        hindu_vegetarian="UNCERTAIN",
        vegetarian="UNCERTAIN",
        kosher="UNCERTAIN",
        dairy_free="UNCERTAIN",
        egg_free="UNCERTAIN",
    ),
    "vitamin d3": _safe_row(
        vegan="UNCERTAIN",
        jain="UNCERTAIN",
        halal="UNCERTAIN",
        hindu_vegetarian="UNCERTAIN",
        vegetarian="UNCERTAIN",
        kosher="UNCERTAIN",
        dairy_free="UNCERTAIN",
        egg_free="UNCERTAIN",
    ),
    "vitamin a palmitate": _safe_row(
        vegan="UNCERTAIN",
        jain="UNCERTAIN",
        halal="UNCERTAIN",
        hindu_vegetarian="UNCERTAIN",
        vegetarian="UNCERTAIN",
        kosher="UNCERTAIN",
        dairy_free="UNCERTAIN",
        egg_free="UNCERTAIN",
    ),
    "vitamin b12": _safe_row(),
    "vitamin d2": _safe_row(),
    "water": _safe_row(),
    "iodised salt": _safe_row(),
    "brown rice": _safe_row(),
    "glucose syrup": _safe_row(),
    "invert sugar": _safe_row(),
    "potato": _safe_row(jain="NOT_SAFE"),  # root vegetable
}


@pytest.mark.parametrize("atom", sorted(EXPECTATIONS))
def test_staple_golden_matrix_no_false_safe(atom: str):
    """Firm SAFE where the table says hazard/uncertain is a failure."""
    for rid, expected in EXPECTATIONS[atom].items():
        got = _cell(atom, rid)
        if expected in ("NOT_SAFE", "UNCERTAIN"):
            assert got != "SAFE", f"{atom!r} × {rid}: expected {expected}, got SAFE"
            if expected == "NOT_SAFE":
                assert got == "NOT_SAFE", f"{atom!r} × {rid}: expected NOT_SAFE, got {got}"
        else:
            assert got == "SAFE", f"{atom!r} × {rid}: expected SAFE, got {got}"


def test_flour_and_flours_are_gluten_l1():
    cache.clear()
    for atom in ("flour", "flours"):
        r = resolve(atom, None)
        assert r.resolution_layer.startswith("L1")
        assert r.group.flags.get("gluten_source") is True


def test_yeast_is_fungal_for_jain():
    cache.clear()
    r = resolve("yeast", None)
    assert r.group.flags.get("fungal") is True
    assert _cell("yeast", "jain") == "NOT_SAFE"
