# Item 29 — Same-seed local reference recipe

Production’s database holds the **ontology seed**. A local box with ~6,800 bulk groups will disagree for data reasons and must not be used as the 95% bar.

PR #17 owns `backend/scripts/item44_prod_parity.py`. Item 29 does not edit it. The flags to use, once that PR is on the tree:

| Flag | Role |
|------|------|
| `--write-reference PATH` | Write local TestClient verdicts (ontology-seed DB only) |
| `--reference-json PATH` | Score a candidate against that file |
| `--same-seed` | Turns on the 95% agreement gate |

Hard gates (always, with or without `--same-seed`):

- zero candidate-SAFE where the reference is NOT_SAFE or UNCERTAIN
- zero 5xx

Wrapper (this track):

```bash
cd backend
python scripts/seed_same_seed_reference.py --emit-recipe
# after PR #17 lands, and only against a local ontology-seed DB:
python scripts/seed_same_seed_reference.py --invoke-write-reference
```

The wrapper refuses `PROD_API_BASE` / `SUPABASE_URL` values that look like production (`ingresure-api.gleeze.com` or `*.supabase.co`).

---

## Local recipe

Assume local Supabase (`http://127.0.0.1:54321`), migrations through `20261014000000`, empty `ike2_*` groups.

```bash
# 1. Ontology only — this is the production seed
cd backend
python scripts/seed_ike2_ontology.py

# 2. Write the reference (PR #17)
python scripts/item44_prod_parity.py \
  --write-reference .local_reports/item44_same_seed_reference.json \
  --limit 0

# 3. Score a candidate that shares that seed (local blue, not production)
PROD_API_BASE=http://127.0.0.1:8001 \
  python scripts/item44_prod_parity.py \
  --reference-json .local_reports/item44_same_seed_reference.json \
  --same-seed --sleep 1.2
```

On this worktree (off `main` at `5b85c6a`) the three flags are **not** in `item44_prod_parity.py` yet. That is expected: PR #17 adds them. Re-run the wrapper after that merge; do not patch the parity script here.

Held-out input: `data/item44_off_product_ids.json` × profiles vegan / gluten_free / peanut_allergy. Cache: `backend/.local_reports/item44_off_product_cache.json`.
