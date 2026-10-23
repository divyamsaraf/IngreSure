# L3 local / CI-only safety suites

Operator notes. Never point these at production. Never paste production
service-role keys. Local Supabase (`supabase start`) or a throwaway
`pgvector/pgvector:pg17` container only.

## Restore dump drill

Custom-format (`pg_dump -F c`) restore into an isolated container, then
compare `public` + `ike2_staging` row counts and the dump SHA-256.

```bash
python scripts/restore_dump_drill.py \
  --dump ~/Documents/IngreSure-backups/gcufjqokqqmcuuayaybu-full-role-postgres-20261022T2354Z.dump \
  --counts /path/to/counts.json \
  --checksum-file /path/to/dump.sha256
```

`--dump` defaults to that backup path if present. The script does **not**
delete the dump. Exit non-zero on checksum or count mismatch. Counts JSON
is `{"schema.table": row_count, ...}`.

## Chaos (pytest, skip without local DB)

From `backend/`:

```bash
python -m pytest tests/test_l3_chaos.py -q
```

- DB down → resolve records degraded and stays `UNCERTAIN` (never `SAFE`);
  `GET /health` exposes `db_reachable` + `ike2_status=UNCERTAIN` via
  `core.knowledge.ike2.audit_health.db_health`.
- Alias view missing `source` or `asserted_flags` → malformed Tier-3 row
  is `UNCERTAIN` and `core.degraded.record` increments.

## evaluate-product contract

`tests/test_evaluate_product_l3_contract.py`: empty `restriction_ids` → 422;
unknown atom → `UNCERTAIN`; peanuts + `peanut_allergy` → `NOT_SAFE`.

## RLS (anon key)

After `supabase start`, copy `ANON_KEY` into `SUPABASE_ANON_KEY` (never
invent keys). `tests/test_l3_rls_anon.py` selects every `ike2_*` relation
as anon and expects empty or error.

Expected policy: RLS enabled, no policies, grants revoked for
`anon`/`authenticated` (migration `20261023120000_ike2_revoke_anon.sql`).
`ike2_v_alias_resolution` is `security_invoker` so it cannot bypass table RLS.

## Dependency audit (non-blocking)

```bash
python scripts/audit_deps.py --out backend/.local_reports/dep_audit.json
```

Default exit 0 even with historical CVEs (`--strict` to fail). CI runs
pip-audit and npm audit with `continue-on-error: true`.

## Soak stub (not in CI)

```bash
python scripts/soak_local.py --cap 8          # local http://127.0.0.1:8000
python scripts/soak_local.py --in-process --cap 3
```

Refuses non-local base URLs.
