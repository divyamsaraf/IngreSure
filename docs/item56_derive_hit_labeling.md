# Item 56 — Derive-hit hand labeling

CI keeps a 300-row golden CSV with **empty** `label` cells. That is
intentional. Precision is computed only after the owner fills labels.

## Files

- Golden set: `backend/tests/ike2/golden/derive_hit_labels.csv`
- Export: `python scripts/export_derive_hit_sample.py` (from `backend/`)
- Score: `python scripts/score_derive_hit_precision.py`

Columns: `atom`, `flag`, `context`, `language`, `label`.

## How the owner fills labels

1. Open the golden CSV.
2. For each row, decide whether the derive hit is correct for that atom:
   - `tp` or `correct` — true positive (atom really belongs to that family)
   - `fp` or `incorrect` — false positive (derive should not have fired)
   - leave blank to skip (still valid in CI)
3. Commit the labeled CSV.
4. Run `python scripts/score_derive_hit_precision.py` to print precision per
   family (`dairy_source`, `gluten_source`, …).

Empty labels do not fail CI. A family with no labels is omitted from the
precision report. Re-exporting with the same `--seed 56` refreshes the
unlabeled sample; do not re-export after labeling unless you intend to
relabel.
