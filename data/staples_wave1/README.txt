L5 staples Wave 1 — review artifacts (no ingest)
================================================

Spec: docs/l5_staples_spec.md (merged PR #31).

Do not ingest. These CSVs are offline review drafts. They are not applied
to Supabase, ike2_ingredient_groups, ontology JSON, or Layer-1 dumps.
verified and class_trusted are always false. No reviewer is set.
seed_prod.py does not read this directory.

Regenerate:

    PYTHONPATH=backend python3 data/staples_wave1/generate_wave1_review.py

Files: review_global.csv, review_india.csv, review_usa.csv,
batch_001_owner_accept.csv (200), audit_sample_300.csv (ungraded human
sample; an LLM must not grade it).

No AE / JP rows. Completeness is 0: unevaluated flags stay empty, not
invented falses. A later ingest PR may mint only after owner accept,
CHECKs, and a human audit that finds zero wrong hazard flags.
