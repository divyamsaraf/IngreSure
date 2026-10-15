# IngreSure documentation

Central index for architecture, deployment, and implementation status.

## Quick links

| Doc | Purpose |
|-----|---------|
| [../README.md](../README.md) | Repo overview, quick start, Docker, tests |
| [../backend/README.md](../backend/README.md) | Backend modules, IKE-2, ontology pipeline, verification |
| [../data/README.md](../data/README.md) | Data files, Layer 1 sources, ingest commands |
| [item16_legacy_cutover_spec.md](item16_legacy_cutover_spec.md) | IKE-2 cutover — **closed** (Item 16 local); historical body + stage log |
| [item29_remote_ike2_seed_plan.md](item29_remote_ike2_seed_plan.md) | Remote IKE-2 schema-vs-data population plan |
| [phase2_gap_analysis.md](phase2_gap_analysis.md) | Phase 2 gap analysis (Items 3–14) |
| [phase_plan.md](phase_plan.md) | Locked execution sequence |
| [item1_item2_gap_report.md](item1_item2_gap_report.md) | Items 1–2 intent vs reality gap |
| [item1_ingestion_spec.md](item1_ingestion_spec.md) | Revised ingestion build spec (strangler-fig) |
| [item2_entity_resolution_spec.md](item2_entity_resolution_spec.md) | Revised entity resolution + compound flags spec |
| [item5_human_review_closeout.md](item5_human_review_closeout.md) | Item 5 — satisfied by CLI force-human (no UI build) |
| [trust_promotion_engine.md](trust_promotion_engine.md) | Item 4 operator guide (Coverage OS + rules; L3 no-op) |
| [item3_1_framework_subvariants_spec.md](item3_1_framework_subvariants_spec.md) | Item 3.1 — fermentation/enzyme/fungal sub-variants |
| [item3_1_p2_backlog_koji_family.md](item3_1_p2_backlog_koji_family.md) | Item 3.1 P2 — koji/miso/tamari/natto Jain firm Avoid |
| [item4_trust_promotion_engine_spec.md](item4_trust_promotion_engine_spec.md) | Item 4 — Trust & Promotion Engine |
| [item4_1_temporal_confidence_decay_spec.md](item4_1_temporal_confidence_decay_spec.md) | Item 4.1 — Temporal confidence decay |
| [item5_6_10_1_12_investigation.md](item5_6_10_1_12_investigation.md) | Targeted look: Items 5, 6, 10.1, 12 |
| [item9_b2b_api_spec.md](item9_b2b_api_spec.md) | Item 9 — B2B API (prompts 1–4 done) |
| [item10_1_multi_restriction_spec.md](item10_1_multi_restriction_spec.md) | Item 10.1 — multi-restriction policy and breakdown |
| [item11_regional_gap_analysis.md](item11_regional_gap_analysis.md) | Item 11 — regional coverage gap (investigate only; spec not written) |
| [item33_dual_resolve_engines.md](item33_dual_resolve_engines.md) | Dual resolve engines (legacy HTTP resolve vs IKE-2) — core complete |
| [item34_fail_stands_despite_low_ks.md](item34_fail_stands_despite_low_ks.md) | Item 34 — triggered FAIL must stand despite low knowledge_state |
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

## Current status (September 2026 — post Item 16)

**IKE-2 is the only served compliance engine** for chat (`/chat/grocery`) and `/api/v1/evaluate-*`. Legacy `ComplianceEngine` and `IKE2_MODE` were removed (Prompt 7). Fail-closed to `UNCERTAIN` on IKE-2 failure. `comparator.compare` + `ike2_shadow_diffs` remain as reusable cutover infrastructure (no current serve-path caller).

**Stage of record:** [item16_legacy_cutover_spec.md](item16_legacy_cutover_spec.md) + architecture tracker (Item 16 **Resolved** locally). Remote Tier-3 data population is **Item 29** (separate).

**Universal label pipeline:** Phases 1–5 **complete** — unified `label_decomposer`, L3 ontology seed, may-contain handling, label corpus + CI shadow gate, OCR/multi-block/regional intent hardening.

**CI gates** (`.github/workflows/ci.yml`): E-number catalog verify, artifact drift, label corpus drift, shadow match ≥85% with **zero false-Safe**, full pytest.

**Stress testing:** `backend/scripts/stress_test_long_label.py` — 200+ ingredient labels with junk text. See [superpowers/plans/2026-06-17-universal-label-input-pipeline.md](superpowers/plans/2026-06-17-universal-label-input-pipeline.md#verification-june-2026).

**Production readiness:** Local cutover verified. A backend pointed at hosted Supabase still needs Item 29 (remote `ike2_*` data) before treating remote as production-ready.

## Historical / analysis reports

These snapshots predate Item 16 closure; prefer **Current status** above and [item16_legacy_cutover_spec.md](item16_legacy_cutover_spec.md) for what shipped.

- [FULL_CODEBASE_ANALYSIS_AND_IMPROVEMENT_REPORT.md](FULL_CODEBASE_ANALYSIS_AND_IMPROVEMENT_REPORT.md)
- [DEEP_ANALYSIS_AND_DEPLOYMENT.md](DEEP_ANALYSIS_AND_DEPLOYMENT.md)
- [BACKEND_AND_FRONTEND_ANALYSIS_REPORT.md](BACKEND_AND_FRONTEND_ANALYSIS_REPORT.md)
