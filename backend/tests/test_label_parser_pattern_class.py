"""Pattern-class tests for label parser (not user-specific one-offs).

Covers design-spec classes A–K as composable patterns, not individual user pastes.
"""
from __future__ import annotations

import pytest

from core.parsing.label_decomposer import decompose_label

PATTERN_CASES = [
    # --- Class E: prefix / boilerplate ---
    {
        "id": "prefix_no_colon",
        "raw": "Ingredients Water, salt, sugar",
        "must_include": ["water", "salt", "sugar"],
        "must_not_include": ["ingredients water", "ingredients"],
        "must_not_include_prefix": True,
    },
    {
        "id": "prefix_no_colon_lowercase",
        "raw": "ingredients milk, cream",
        "must_include": ["milk", "cream"],
        "must_not_include": ["ingredients milk"],
        "must_not_include_prefix": True,
    },
    {
        "id": "prefix_dash",
        "raw": "INGREDIENTS - water, salt",
        "must_include": ["water", "salt"],
        "must_not_include_prefix": True,
    },
    {
        "id": "duplicate_ingredients_prefix",
        "raw": "Ingredients Ingredients water, salt",
        "must_include": ["water", "salt"],
        "must_not_include": ["ingredients water", "ingredients ingredients"],
        "must_not_include_prefix": True,
    },
    {
        "id": "composition_eu",
        "raw": "Composition: water; sugar; citric acid",
        "must_include": ["water", "sugar", "citric acid"],
        "must_not_include": ["composition"],
    },
    # --- Class F: semicolon lists ---
    {
        "id": "semicolon_eu_list",
        "raw": "Ingredients: water; sugar; citric acid",
        "must_include": ["water", "sugar", "citric acid"],
    },
    {
        "id": "semicolon_trace_clause",
        "raw": "Ingredients: yeast; Contains 2% or less of: salt, enzymes",
        "must_include": ["yeast", "salt", "enzymes"],
        "must_not_include": ["of salt", "contains 2%"],
        "trace_atoms": ["salt", "enzymes"],
        "non_trace_atoms": ["yeast"],
    },
    # --- Class D: trace / minor % ---
    {
        "id": "trace_inline_contains_2pct_or_less_of",
        "raw": (
            "Ingredients: flour, sugar, leavening (baking soda). "
            "Contains 2% or less of salt, cinnamon, eggs, whey."
        ),
        "must_include": ["flour", "sugar", "baking soda", "salt", "cinnamon", "egg", "whey"],
        "must_not_include": ["of salt", "contains 2%", "less of"],
        "trace_atoms": ["salt", "cinnamon", "egg", "whey"],
        "non_trace_atoms": ["flour", "sugar"],
    },
    {
        "id": "trace_less_than_2pct_of",
        "raw": "Ingredients: water, starch, less than 2% of garlic, onion.",
        "must_include": ["water", "starch", "garlic", "onion"],
        "must_not_include": ["of garlic", "less than 2%"],
        "trace_atoms": ["garlic", "onion"],
    },
    {
        "id": "trace_contains_2pct_or_less_of_colon",
        "raw": "Ingredients: starch, Contains 2% or less of: onions, salt.",
        "must_include": ["starch", "onion", "salt"],
        "must_not_include": ["of onions", "contains 2%", "less of"],
        "trace_atoms": ["onion", "salt"],
    },
    {
        "id": "trace_inline_parenthetical_lt2pct",
        "raw": "Ingredients: flour, salt (<2%), yeast",
        "must_include": ["flour", "salt", "yeast"],
        "must_not_include": ["<2%", "(<2%)"],
        "trace_atoms": ["salt"],
        "non_trace_atoms": ["flour", "yeast"],
    },
    # --- Class B/C: nesting ---
    {
        "id": "nested_folic_acid_no_trailing_paren",
        "raw": "Ingredients: enriched flour (wheat flour, niacin, folic acid), water",
        "must_include": ["folic acid", "water", "niacin", "enriched flour"],
        "must_not_include": ["folic acid)"],
    },
    {
        "id": "nested_brackets_no_trailing_bracket",
        "raw": "Ingredients: vitamin B1 [thiamin mononitrate], water",
        "must_include": ["vitamin b1", "thiamin mononitrate", "water"],
        "must_not_include": ["thiamin mononitrate]", "vitamin b1]"],
    },
    {
        "id": "colors_structural_header",
        "raw": "Ingredients: water, Colors (Red 40, Yellow 5), salt",
        "must_include": ["water", "red 40", "yellow 5", "salt"],
        "must_not_include": ["colors ("],
    },
    {
        "id": "preservatives_structural_header",
        "raw": "Ingredients: flour, Preservatives (Calcium Propionate, Sorbic Acid), yeast",
        "must_include": ["flour", "calcium propionate", "sorbic acid", "yeast"],
        "must_not_include": ["preservatives ("],
    },
    # --- Class G: may contain / allergen ---
    {
        "id": "may_contain_block",
        "raw": "Ingredients: water, flour. May contain: peanuts, tree nuts",
        "must_include": ["water", "flour", "peanut", "tree nut"],
        "may_contain_atoms": ["peanut", "tree nut"],
        "non_may_contain_atoms": ["water", "flour"],
    },
    {
        "id": "may_also_contain_traces",
        "raw": "Ingredients: flour. May also contain traces of: peanuts, tree nuts",
        "must_include": ["flour", "peanut", "tree nut"],
        "may_contain_atoms": ["peanut", "tree nut"],
    },
    {
        "id": "facility_cross_contact",
        "raw": "Ingredients: oats. Produced in a facility that also processes wheat, peanuts",
        "must_include": ["oat", "wheat", "peanut"],
        "may_contain_atoms": ["wheat", "peanut"],
        "non_may_contain_atoms": ["oat"],
    },
    {
        "id": "allergen_contains_block",
        "raw": "Ingredients: whey. CONTAINS: MILK, SOY, WHEAT",
        "must_include": ["whey", "milk", "soy", "wheat"],
        "must_not_include": ["whey contains milk", "contains:"],
        "may_contain_atoms": ["milk", "soy", "wheat"],
    },
    {
        "id": "allergen_contains_no_colon",
        "raw": "Ingredients: flour. CONTAINS WHEAT, MILK AND SOY",
        "must_include": ["flour", "wheat", "milk", "soy"],
        "must_not_include": ["flour contains wheat", "milk and soy"],
        "may_contain_atoms": ["wheat", "milk", "soy"],
    },
    # --- Class K: multi-subsection / frozen meals ---
    {
        "id": "vitamins_minerals_section",
        "raw": (
            "Ingredients: water, soy lecithin. "
            "Vitamins and Minerals: calcium carbonate, iron, vitamin B12."
        ),
        "must_include": ["water", "soy lecithin", "calcium carbonate", "iron", "vitamin b12"],
        "must_not_include": ["vitamins and minerals", "soy lecithin vitamins"],
    },
    {
        "id": "product_subsection_all_caps_header",
        "raw": "Ingredients COOKED SALISBURY STEAK: Mechanically Separated Chicken, Water, Pork",
        "must_include": ["mechanically separated chicken", "water", "pork"],
        "must_not_include": ["cooked salisbury steak", "ingredients cooked"],
    },
    {
        "id": "gravy_subsection_clause_split",
        "raw": (
            "Ingredients: chicken, salt, citric acid. "
            "GRAVY: water, modified corn starch, onion."
        ),
        "must_include": ["chicken", "salt", "citric acid", "water", "modified corn starch", "onion"],
        "must_not_include": ["citric acid gravy", "gravy water"],
    },
    {
        "id": "title_case_subsections",
        "raw": (
            "Ingredients: Cookie Filling: sugar, flour. "
            "Icing: corn syrup, water"
        ),
        "must_include": ["sugar", "flour", "corn syrup", "water"],
        "must_not_include": ["cookie filling sugar", "icing corn"],
    },
    {
        "id": "composite_cereal_style",
        "raw": (
            "Ingredients Water, enriched flour (wheat flour, niacin, reduced iron, "
            "vitamin B1 [thiamin mononitrate], vitamin B2 [riboflavin], folic acid), "
            "sugar, fructose, vegetable oil (soybean, palm, canola and/or cottonseed), "
            "leavening (baking soda, sodium aluminum phosphate, monocalcium phosphate), "
            "contains 2% or less of salt, cinnamon, eggs, whey, soy lecithin. "
            "Vitamins and Minerals: Calcium carbonate, iron, vitamin A palmitate, "
            "vitamin B6 (pyridoxine hydrochloride), vitamin B12."
        ),
        "must_include": [
            "water", "folic acid", "salt", "cinnamon", "egg", "whey", "soy lecithin",
            "calcium carbonate", "pyridoxine hydrochloride", "vitamin b12",
        ],
        "must_not_include": [
            "ingredients water", "folic acid)", "of salt", "contains 2%",
            "soy lecithin vitamins",
        ],
        "trace_atoms": ["salt", "cinnamon", "egg", "whey"],
        "non_trace_atoms": ["water", "sugar", "fructose"],
    },
    {
        "id": "frozen_meal_multi_subsection",
        "raw": (
            "Ingredients Ingredients COOKED SALISBURY STEAK: Mechanically Separated Chicken, "
            "Water, Pork, Beef, Breader (Enriched Bleached Wheat Flour [Bleached Wheat Flour, "
            "Niacin, Reduced Iron, Thiamine Mononitrate, Riboflavin, Folic Acid], Durum Flour, "
            "Leavening [Sodium Bicarbonate, Sodium Acid Pyrophosphate], Yeast), "
            "Textured Vegetable Protein (Soy Flour, Caramel Color), Soy Protein Concentrate, "
            "Less Than 2% Of: Dried Onion, Salt, Flavorings, Caramel Color, Potassium Phosphates, "
            "Dextrose, Potassium Salt, Citric Acid. GRAVY: Water, Modified Corn Starch, "
            "Contains 2% or less of: Onions, Salt, Flavorings, Monosodium Glutamate, "
            "Caramel Color, Corn Syrup Solids, Beef Base (Beef Flavor [Autolyzed Yeast Extract, "
            "Disodium Inosinate And Disodium Guanylate, Xanthan Gum], Salt, Hydrolyzed Soy Protein, "
            "Sugar, Monosodium Glutamate, Flavor, Propylene Glycol, Caramel Color, "
            "Vegetable Juice Concentrates [Celery, Carrot, Onion And Leek], "
            "Extractives Of Paprika), Whey. CONTAINS: MILK, SOY, WHEAT"
        ),
        "must_include": [
            "mechanically separated chicken", "pork", "beef", "citric acid", "water",
            "modified corn starch", "onion", "beef base", "whey", "milk", "soy", "wheat",
            "extractives of paprika",
        ],
        "must_not_include": [
            "cooked salisbury steak", "citric acid gravy", "of onions",
            "whey contains milk", "ingredients cooked",
        ],
        "trace_atoms": ["dried onion", "onion"],
    },
    # --- Class I/K: separators ---
    {
        "id": "newline_ingredient_list",
        "raw": "Ingredients:\nwater\nsalt\nsugar",
        "must_include": ["water", "salt", "sugar"],
        "must_not_include": ["water salt"],
    },
    {
        "id": "bullet_separators",
        "raw": "Ingredients: water • salt • sugar",
        "must_include": ["water", "salt", "sugar"],
        "must_not_include": ["•"],
    },
    {
        "id": "and_separator_list",
        "raw": "Ingredients: eggs and milk and flour",
        "must_include": ["egg", "milk", "flour"],
        "must_not_include": ["eggs and milk"],
    },
]


def _names_and_flags(raw: str):
    items = decompose_label(raw)
    names = [i.name for i in items]
    by_trace = {i.name: i.trace for i in items}
    by_may_contain = {i.name: i.may_contain for i in items}
    return names, by_trace, by_may_contain


@pytest.mark.parametrize("case", PATTERN_CASES, ids=lambda c: c["id"])
def test_label_parser_pattern_class(case: dict):
    names, by_trace, by_may_contain = _names_and_flags(case["raw"])

    for token in case.get("must_include", []):
        assert any(token in n for n in names), f"{case['id']}: missing {token!r} in {names}"

    for token in case.get("must_not_include", []):
        assert not any(token in n for n in names), f"{case['id']}: unwanted {token!r} in {names}"

    if case.get("must_not_include_prefix"):
        assert not any(n.startswith("ingredients") for n in names), names

    for atom in case.get("trace_atoms", []):
        match = next((n for n in names if atom in n), None)
        assert match is not None, f"{case['id']}: trace atom {atom!r} missing"
        assert by_trace.get(match) is True, f"{case['id']}: {match} should be trace"

    for atom in case.get("non_trace_atoms", []):
        match = next((n for n in names if atom in n), None)
        assert match is not None, f"{case['id']}: atom {atom!r} missing"
        assert by_trace.get(match) is False, f"{case['id']}: {match} should not be trace"

    for atom in case.get("may_contain_atoms", []):
        match = next((n for n in names if atom in n), None)
        assert match is not None, f"{case['id']}: may_contain atom {atom!r} missing"
        assert by_may_contain.get(match) is True, f"{case['id']}: {match} should be may_contain"

    for atom in case.get("non_may_contain_atoms", []):
        match = next((n for n in names if atom in n), None)
        assert match is not None, f"{case['id']}: atom {atom!r} missing"
        assert by_may_contain.get(match) is False, f"{case['id']}: {match} should not be may_contain"
