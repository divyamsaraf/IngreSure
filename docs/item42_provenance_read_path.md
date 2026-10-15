# Provenance on the read path (post Item 42)

## (a) `source=NULL` / missing

`is_trusted_for_compliance` is **fail-closed**:

- Resolution channel `static` (truth anchor / local ontology) → trusted.
- Group `source` in the bulk ceiling set → untrusted.
- Group `source` missing/NULL/empty/unknown → **untrusted** (not treated as curated).
- Only allowlisted group sources may firm-SAFE on the DB path: `ontology`, `human`, `e_number_catalog`, `truth_anchor`.
- `classification_method` `bulk:<src>` remains a belt when the view omits `source`; it does **not** grant trust when both are absent.

## (b) Live view test

`tests/ike2/test_ike2_view_schema_parity.py::test_live_alias_view_exposes_source_and_bulk_uncapped` resolves a bulk FSSAI alias through `ike2_v_alias_resolution`, asserts `source` non-null, `trusted=False`, verdict ≠ SAFE.

## (c) Schema-parity CI

Same module: every migration that `ADD COLUMN` on `ike2_ingredient_groups` must be followed (by stamp) by a `CREATE OR REPLACE VIEW` of each group-exposing view. Latest view DDL must use `g.*` or list resolver-read columns.

## (d) Inventory (local Postgres)

| Object | Kind | Notes |
|--------|------|-------|
| `ike2_v_alias_resolution` | view | **Only** view over `ike2_ingredient_groups`. After `20261014000000` recreate, columns match the table (incl. `source`, `asserted_flags`). |
| (none) | function | No SQL functions depend on `ike2_ingredient_groups`. |

Product consequence: only curated allowlisted provenance can firm-SAFE (~1,738 ontology today). ~5k Item 11 bulk groups add Avoid power, never clearance. Next coverage metric: real label lists — ~200 OFF (ODbL) lists × 6 profiles, SAFE/UNCERTAIN/NOT_SAFE rates + top-50 UNCERTAIN by frequency (deferred until 37–42 closed).
