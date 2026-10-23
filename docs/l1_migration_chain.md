# L1.3 Migration chain audit

Branch: `feat/l1-migration-chain` (from `origin/main` @ `21a925e`).
Throwaway Postgres: `pgvector/pgvector:pg17` container `ingresure-l1-migrations-pg` (not the live local Supabase volume).
Local compare target: `supabase_db_ingresure` on `127.0.0.1:54322` (read-only dumps / selects).
No production credentials were used. Repair SQL was written, not applied, and not pushed as a secret.

## 1. Clean apply

All **22** files in `supabase/migrations/` applied in version order inside `--single-transaction` on a fresh Postgres 17 with:

- `create extension vector` / `pg_trgm` (from `20240101000000_init.sql`)
- stub `auth.users` + `auth.uid()` (init references `auth.users`; RLS policies call `auth.uid()`)
- roles `anon`, `authenticated`, `service_role` (for `GRANT` in `20260306000000_enable_rls.sql`)

Result: 22/22 recorded in `supabase_migrations.schema_migrations`. `ike2_restriction_rules` = **58**.

## 2. Schema dump diff

`pg_dump --schema-only --schema=public --schema=ike2_staging --no-owner --no-privileges`:

**Application schema diff is zero.** Tables, views, columns (252), and indexes match. The only `diff` lines were pg_dump `\restrict` / `\unrestrict` tokens (random per dump).

Full-database `--schema-only` is **not** zero. Local Supabase also has platform schemas that the throwaway container does not: `_realtime`, `auth` (full GoTrue), `extensions`, `graphql`, `graphql_public`, `net`, `pgbouncer`, `realtime`, `storage`, `supabase_functions`, `vault`. Those are Supabase runtime, not this chain.

## 3. `schema_migrations` vs files

| Source | Versions |
| --- | --- |
| Files on disk | 22 (through `20261014000000`) |
| Local Supabase tracker | 19 (last `20260918010000`) |
| Throwaway after clean apply | 22 |

Missing local tracker rows (objects already exist):

- `20260919000000` `ike2_group_provenance_source` — column `ike2_ingredient_groups.source`
- `20261003000000` `ike2_asserted_flags` — column `ike2_ingredient_groups.asserted_flags`
- `20261014000000` `ike2_alias_view_include_source` — view `ike2_v_alias_resolution` includes `source` / `asserted_flags`

Repair (expand-only, transactional, not applied here): `deploy/repair_schema_migrations.sql`.

## 4. Idempotence, transactions, expand-only, extensions, RLS

**Transactional.** Each file applied under `--single-transaction`. No `CREATE INDEX CONCURRENTLY`. The chain completed without a mid-file commit.

**Idempotent (later IKE-2 files, yes; early files, no).**

- Re-applying `20260919` / `20261003` / `20261014` on the throwaway succeeded (`IF NOT EXISTS` / `CREATE OR REPLACE VIEW`).
- Seed inserts use `ON CONFLICT (category, field, coalesce(region, 'GLOBAL')) DO NOTHING`.
- `20240101000000_init.sql` uses bare `CREATE TABLE` — not re-runnable.
- `20260306000000_enable_rls.sql` uses bare `CREATE POLICY` — not re-runnable.

**Expand-only (not the whole history).** Forward IKE-2 migrations add columns/indexes/rows or `CREATE OR REPLACE` the alias view. Historical exceptions:

- `20260306100000_drop_restaurant_submissions.sql` drops the grocery-pivot menu tables.
- `20260720*` include `DELETE`/`UPDATE` on already-seeded rule or group rows (data repair, then insert).
- Constraint `DROP CONSTRAINT IF EXISTS` + re-`ADD` appears on CHECK names (same predicate, not a column drop).

**Required extensions:** `vector` (pgvector), `pg_trgm`. `gen_random_uuid()` is built-in on Postgres 13+.

**RLS on new tables.** Every public table created by this chain has RLS enabled (`users`, legacy `ingredient_*`, `request_history`, all `ike2_*`). IKE-2 tables have no policies (service_role only). Staging `ike2_staging.ingredient_groups` and `ike2_staging.stg_rejects` do **not** have RLS.

## 5. Restriction rules: 58 is correct (not 52)

`backend/tests/ike2/test_db_rule_parity.py` **passed** (seed vs migration-replay never-SAFE verdicts match). `test_seed_sql_covers_rule_seed` **passed** (Python `RULE_SEED` == replayed table).

| Counter | Count |
| --- | --- |
| `rules.RULE_SEED` / `seeded_rules()` | **58** |
| Migration replay (insert/delete in file order) | **58** |
| Throwaway DB after full chain | **58** |
| Local Supabase `ike2_restriction_rules` | **58** |
| `20260617000000` seed `INSERT` tuples | 52 |
| Later `INSERT` tuples (gross, includes re-asserts) | 14 |
| Gross `INSERT` tuples | 66 |
| Distinct restriction categories (`SUPPORTED_RESTRICTIONS`) | 31 |

52 is the **original seed file** row count. Net after later files (enzyme-origin rules in `20260918010000`, plus a few ON CONFLICT re-asserts / one delete+reinsert) is **58**. Do not shrink the seed to 52.

The stale deploy note that treated 52 as the live-table expectation was updated in `deploy/oci_api_deploy_runbook.txt`.
