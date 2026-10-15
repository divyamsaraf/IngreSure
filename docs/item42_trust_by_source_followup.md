# Item 42 — trust-by-source SAFE ceiling

## Verdict

Firm SAFE is a property of the **source**, not of marker presence. Bulk groups
(USDA, INFOODS, IFCT, FSSAI, OFF, …) never return `trusted=True` for compliance,
even when every allergen flag is false/absent.

## Live counts (local Supabase, 6913 groups)

| source   | groups | trusted (new) |
|----------|--------|---------------|
| usda     | 3575   | 0             |
| ontology | 1738   | 1738          |
| fssai    | 755    | 0             |
| infoods  | 521    | 0             |
| ifct     | 324    | 0             |

Marker-only policy would still have trusted **929** bulk clean-flag rows
(174 USDA + 755 FSSAI). Those are the uncapped “clean passes” the lexicon never
saw.

## Alias-view hole (fixed)

`ike2_v_alias_resolution` was created with `g.*` before `source` existed;
Postgres does not refresh `*` views on `ALTER TABLE ADD COLUMN`. L3 alias hits
therefore had `source=None` and skipped the ceiling.

Fixes:
- Migration `20261014000000_ike2_alias_view_include_source.sql` recreates the view.
- `is_trusted_for_compliance` also parses `classification_method` `bulk:<src>`.

## 47-name / remaining-11 rerun

The 11 FSSAI phrasing-noise rows that previously reported `trusted=True` + firm
SAFE are now all **UNCERTAIN** / `trusted=False`. USDA firm-SAFE+trusted among
them: **0**.

Artifacts: [`item42_trust_by_source_recount.json`](item42_trust_by_source_recount.json).

## Assertion changelog — alcohol lifestyle (2026-10-15)

`test_etl_adapt_safety.test_alcohol_ingredient_is_never_safe_for_alcohol_restriction`
changed from expecting `Verdict.FAIL` to `Verdict.UNCERTAIN`.

**Why:** USDA bulk rows are untrusted under the source SAFE ceiling. An inferred
alcohol flag on an untrusted group no longer firm-Avoids for lifestyle/religious
profiles (halal alcohol restriction). FAIL stands only for allergy/medical
(Item 42 inferred-positive policy). Lifestyle alcohol on bulk therefore
caps at UNCERTAIN — matching `test_item42_inferred_fail_stands` and the
trust-by-source design.
