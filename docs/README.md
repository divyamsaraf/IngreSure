# IngreSure documentation

Central index for architecture, deployment, and implementation status.

## Quick links

| Doc | Purpose |
|-----|---------|
| [../README.md](../README.md) | Repo overview, quick start, Docker, tests |
| [../backend/README.md](../backend/README.md) | Backend modules, IKE-2, ontology pipeline, verification |
| [../data/README.md](../data/README.md) | Data files, Layer 1 sources, ingest commands |
| [item16_legacy_cutover_spec.md](item16_legacy_cutover_spec.md) | IKE-2 cutover / stage of record (replaces PHASES.md) |
| [../DEPLOY.md](../DEPLOY.md) | Production topology (Vercel + OCI) |

## API & frontend

| Doc | Purpose |
|-----|---------|
| [stream-protocol.md](stream-protocol.md) | Chat stream tags (`<<<INGREDIENT_AUDIT>>>`) |
| [api-v1-and-frontend-endpoints.md](api-v1-and-frontend-endpoints.md) | BFF vs `/api/v1/*` |
| [auth-and-identity.md](auth-and-identity.md) | Anonymous sessions, `user_id` |
| [diet-and-restriction-ids.md](diet-and-restriction-ids.md) | Adding diets and restrictions |

## Architecture & operations

| Doc | Purpose |
|-----|---------|
| [SERVICES_OVERVIEW.md](SERVICES_OVERVIEW.md) | What runs in Docker vs host |
| [unknown-ingredients-and-external-apis.md](unknown-ingredients-and-external-apis.md) | Resolution order, API testing, audit payload |
| [redis-for-speed-and-ux.md](redis-for-speed-and-ux.md) | Resolution cache + Celery |
| [SUPABASE_TABLES.md](SUPABASE_TABLES.md) | Schema reference |

## IKE-2 & universal label pipeline (June 2026)

| Doc | Purpose |
|-----|---------|
| [superpowers/specs/2026-06-16-ike2-design.md](superpowers/specs/2026-06-16-ike2-design.md) | IKE-2 design, correctness contract, cutover gates |
| [superpowers/plans/2026-06-16-ike2-implementation.md](superpowers/plans/2026-06-16-ike2-implementation.md) | Build tasks + activation hardening status |
| [superpowers/specs/2026-06-17-universal-label-input-pipeline-design.md](superpowers/specs/2026-06-17-universal-label-input-pipeline-design.md) | Unified label decomposer, phases A–K |
| [superpowers/plans/2026-06-17-universal-label-input-pipeline.md](superpowers/plans/2026-06-17-universal-label-input-pipeline.md) | Phase 1–5 completion + verification |
| [superpowers/specs/2026-06-17-ike2-e-number-expansion-design.md](superpowers/specs/2026-06-17-ike2-e-number-expansion-design.md) | E-number catalog + compliance tiers |

## Current status (June 2026)

**Legacy engine:** Production path for user-facing verdicts. **1193** backend tests collected; full suite passes when local Supabase is running (7 DB integration tests skip or error without it).

**IKE-2:** Implemented under `backend/core/knowledge/ike2/`. Rollout via `IKE2_MODE` in `backend/.env`:

| Mode | Behavior |
|------|----------|
| `off` (default) | IKE-2 not run on live traffic |
| `shadow` | IKE-2 runs in parallel; divergences logged to `ike2_shadow_diffs`; **legacy verdict unchanged** |
| `primary` / `fallback` | **Not wired yet** — cutover blocked on soak gates (see IKE-2 spec §8) |

**Universal label pipeline:** Phases 1–5 **complete** — unified `label_decomposer`, L3 ontology seed, may-contain handling, 457-row label corpus + CI shadow gate, OCR/multi-block/regional intent hardening.

**CI gates** (`.github/workflows/ci.yml`): E-number catalog verify, artifact drift, label corpus drift, shadow match ≥85% with **zero false-Safe**, full pytest.

**Stress testing:** `backend/scripts/stress_test_long_label.py` — 200+ ingredient labels with junk text; legacy vs IKE-2 verdict parity and latency. See [superpowers/plans/2026-06-17-universal-label-input-pipeline.md](superpowers/plans/2026-06-17-universal-label-input-pipeline.md#verification-june-2026).

**Production readiness:** Safe to deploy legacy + `IKE2_MODE=shadow` for staging soak. Do **not** promote to `primary` until 7-day shadow soak shows `false_safe_regression = 0`.

## Historical / analysis reports

These snapshots predate IKE-2 and the universal pipeline; read the **Current status** section above for what shipped.

- [FULL_CODEBASE_ANALYSIS_AND_IMPROVEMENT_REPORT.md](FULL_CODEBASE_ANALYSIS_AND_IMPROVEMENT_REPORT.md)
- [DEEP_ANALYSIS_AND_DEPLOYMENT.md](DEEP_ANALYSIS_AND_DEPLOYMENT.md)
- [BACKEND_AND_FRONTEND_ANALYSIS_REPORT.md](BACKEND_AND_FRONTEND_ANALYSIS_REPORT.md)
