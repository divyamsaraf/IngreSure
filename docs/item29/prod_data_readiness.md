# Item 29 — Production data readiness (local report)

**Track:** F (`feat/prod-data-readiness`)  
**Scope:** report + local scripts only. No remote migrate, no remote seed, no production calls.  
**Date of record:** 2026-10-21 (worktree at `main` merge `5b85c6a` plus these docs/scripts).

This is not a privacy policy. Allergy and diet profiles are health-related; counsel reviews before any pilot (see [Privacy note](#privacy-note-not-a-policy)).

---

## 1. Which Supabase project the API will read

Record **project refs only**. Never copy keys.

| Surface | Ref / value | Notes |
|---------|-------------|--------|
| Intended production project | `gcufjqokqqmcuuayaybu` | Named in `deploy/oci_api_deploy_runbook.txt` and the older `docs/item29_remote_ike2_seed_plan.md` as the linked remote the API should read. |
| Production API host | `ingresure-api.gleeze.com` | Caddy → `127.0.0.1:8000`. Backend env name: `SUPABASE_URL`. |
| How to confirm on the host | Host portion of `SUPABASE_URL` | Operator records the ref (example: `gcufjqokqqmcuuayaybu`). Do not print the service-role key. |
| `.env.example` placeholder | `https://your-project.supabase.co` | No production ref is hardcoded in the example. |
| Local CLI | `project_id = "ingresure"` in `supabase/config.toml` | Docker/local only (`http://127.0.0.1:54321`). Not the hosted project. |
| Frontend | no service-role | API reads `ike2_*` via backend `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`. |

**Operator check (names only):** on the OCI host, `grep -E '^(SUPABASE_URL)=' backend/.env` and keep the project-ref hostname. If that host is not `gcufjqokqqmcuuayaybu`, treat the box as option B in the OCI runbook (legacy / other Postgres) and do not assume Item 29 counts.

### Separate staging project

Use a **new** hosted Supabase project (suggested name `ingresure-staging`). Do **not** reuse `gcufjqokqqmcuuayaybu` for dry-runs, L3 experiments, or soak.

| Environment | Project | Seed |
|-------------|---------|------|
| Local | CLI `ingresure` (`127.0.0.1`) | Ontology + optional L3 bulk |
| Staging | **new** project, new ref | Same migrations + ontology seed as prod; L3 bulk only after a snapshot |
| Production | `gcufjqokqqmcuuayaybu` (if operator confirms `SUPABASE_URL`) | Ontology seed first. L3 bulk is later and additive. |

Point a staging API (`ENVIRONMENT` ≠ production, or a distinct hostname) at the staging ref. Never point the production hostname at staging, and never point staging scripts at the production ref.

---

## 2. Migration list (last applied → HEAD)

Repo migrations live in `supabase/migrations/` (22 files). Remote state in the Item 29 seed plan (2026-09-16) plus the OCI runbook: IKE-2 schema is on `gcufjqokqqmcuuayaybu`, but **`20260918*`–`20261014*` are not applied**.

**Last applied (documented remote):** `20260808000000_ike2_shadow_diffs_route_context.sql`

**Pending to HEAD (do not apply from this track):**

| Stamp | File | Why it matters |
|-------|------|----------------|
| `20260918000000` | `ike2_trust_refreshed_at.sql` | Decay clock on `ike2_ingredient_groups`. |
| `20260918010000` | `ike2_enzyme_origin_flags.sql` | `enzyme_animal_source` / `enzyme_microbial_source`. |
| `20260919000000` | `ike2_group_provenance_source.sql` | Adds `ike2_ingredient_groups.source`. |
| `20261003000000` | `ike2_asserted_flags.sql` | `asserted_flags text[]` for deliberate true/false. |
| `20261014000000` | `ike2_alias_view_include_source.sql` | Recreates `ike2_v_alias_resolution` so `g.*` includes `source`. |

Operator must re-confirm with `supabase migration list --linked` before any apply. This track does not run that against production.

### Already on remote (per 2026-09-16 plan), listed for context

`20240101000000` init → `20260808000000` shadow route context, including IKE-2 schema (`20260616000000`), restriction-rule seed (`20260617000000`, expect 52 rules), bee/insect/honey/pescatarian rule patches, and legacy `ingredients.source` CHECKs for `fda_gras` / `foodex2` / `fssai` / `nin` (`20260613000000`, `20260613010000`).

---

## 3. Ontology seed command

Production L3 starts as the **ontology seed**, not the local bulk corpus.

```bash
# local or staging only — never from this track against production
cd backend
python scripts/seed_ike2_ontology.py --dry-run          # in-memory validate
python scripts/seed_ike2_ontology.py                    # writes ike2_* from data/ontology.json
```

- Input: `data/ontology.json` (1,857 ingredients in this tree).
- Entry point: `backend/scripts/seed_ike2_ontology.py` → `bulk_inject.inject(..., "ontology", writer)`.
- Confirm `ike2_restriction_rules` is 52 (migration seed) before/after.
- Do **not** copy `ike2_shadow_diffs`.
- L1 `truth_anchor` and L2 `data/ontology.json` also ship with the app binary; empty L3 only hurts DB-only atoms.

---

## 4. Does `ike2_v_alias_resolution` expose `source`?

**Yes — after `20261014000000`.** Until that migration is applied on the project the API reads, the live view does **not** expose `source`.

- Original view (`20260616000000`) selected `g.*` from `ike2_ingredient_groups`.
- `source` was added later (`20260919000000`). Postgres expands `g.*` at `CREATE VIEW` time; `ALTER TABLE ADD COLUMN` does not refresh the view.
- `20261014000000_ike2_alias_view_include_source.sql` `CREATE OR REPLACE`s the view with the same `g.*` join so `source` is projected. Resolver/tests (`test_ike2_view_schema_parity.py`) require that column.

```sql
create or replace view public.ike2_v_alias_resolution as
select
  a.normalized_alias,
  a.alias_type,
  a.region,
  a.match_confidence,
  i.id as ingredient_id,
  i.normalized_name,
  g.*
from public.ike2_aliases a
join public.ike2_ingredients i
  on i.id = a.ingredient_id and i.superseded_by is null
join public.ike2_ingredient_groups g
  on g.id = i.group_id
  and g.superseded_by is null
  and g.knowledge_state <> 'DEPRECATED';
```

---

## Privacy note (not a policy)

Allergy and diet fields (`allergies`, `diet_type`, lifestyle preferences) are **health-related personal data**. They persist in `data/profiles.json` by default, or in `public.users` when `USE_PROFILE_DB` is on. Chat and `/api/v1/evaluate-*` collect restriction ids that imply medical/religious diets.

Before a pilot: counsel reviews collection, retention, subprocessors (Supabase, OCI, Vercel), and any cross-border transfer. This repository must not ship a privacy policy drafted by engineering.

---

## Scripts added by this track

| Path | Role |
|------|------|
| `backend/scripts/item29_dry_run_l3_sources.py` | Count-check + in-memory ontology/live replays for FDA GRAS, NIN, FoodEx2 |
| `backend/scripts/seed_same_seed_reference.py` | Same-seed recipe; points at PR #17 flags without editing that script |
| `docs/item29/l3_bulk_plan.md` | L3 sources, order, replay proof, rollback |
| `docs/item29/same_seed_reference.md` | Local reference-run recipe |
| `docs/item29/dry_run_outcomes.md` | Human-readable dry-run summary |
| `docs/item29/reports/l3_dry_run.json` | Dry-run output |
| `deploy/item29_operator_notes.txt` | Short operator pointer (no secrets) |
