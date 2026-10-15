# Item 42 — Inferred-positive trust gate (fix)

**Status:** code landed 2026-10-13  
**Companion:** [`item42_inferred_positive_uncertainty.md`](item42_inferred_positive_uncertainty.md) · [`item42_safe_inferred_26.md`](item42_safe_inferred_26.md) · [`item42_kind_and_capstone.md`](item42_kind_and_capstone.md)

## Code change

In `compliance._verdict_for`: when `trusted=False`, do **not** blank the verdict to UNCERTAIN if the rule is allergy/medical **and** triggered. Clean passes still return UNCERTAIN. Lifestyle/religious stay fail-closed.

`_ALLERGY_MEDICAL` mirrors the seeded safety/medical restriction set.

## Tests

- `tests/ike2/test_item42_inferred_fail_stands.py` — FAIL stands with inferred; clean inferred caps UNCERTAIN; vegan stays UNCERTAIN.
- `tests/ike2/test_safety_invariants.py` — INV-2 updated: untrusted never SAFE; FAIL only for medical restrictions.
- `tests/ike2/test_usda_fish_shellfish_infer.py` — Layer-1 emits `food_category` and splits `usda_fdc_category_derived` / `usda_fdc_name_inferred`.

## USDA transform

`transform_usda_fdc_bulk.py` keeps `food_category`, splits fish/shellfish markers, and always keeps a row-level `*inferred*` SAFE ceiling beside `usda_fdc_category_derived`. Asserted clears are enumerated in `data/usda_reviewed_asserted_clears.json` only. Dump re-transformed and re-injected 2026-10-13 (see `item42_verification.md`, `item42_trust_clears_lexicon_followup.md`).
