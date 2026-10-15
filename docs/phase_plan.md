# IngreSure — Phase Plan (locked sequence)

**Purpose:** Single place for *what runs next*.  
**Companion:** architecture tracker (titles authoritative) · `docs/system_state_audit.md` · `docs/phase2_gap_analysis.md`

**Last locked:** 2026-09-28 (Item **33** core complete; Prompt 7 deferred; hand-vs-catalog agreement test on)

---

## Spec-writing batches (do not run all eleven at once)

| Batch | Items | Status |
|-------|-------|--------|
| **1 — Trust core** | **4**, **4.1**, **3.1** | **Closed** (+ Item **34** FAIL-stands fix). |
| **2 — B2B API** | **9**, **10.1** | Prompts 1–4 done (2026-09-30). |
| **3 — Ops / quality** | **5**, **6**, **7** | **Closed** (2026-10-07): 5 closeout + 6 LLM harden + 7 never-SAFE/DB-rule parity |
| **4 — Platform** | **12**, **13**, **14** | Held with batch 2 — no more paper ahead of 1/2 |
| Separate | **8**, **33✓** (P7 optional), **34✓**, **11**, **18+23✓**, **29** | **34 done**; **1✓** / **2✓** / **18+23✓** / **33** core complete; **batch 2** prompts done |

---

## Sequence (execution)

| When | What |
|------|------|
| **Done** | Phase 2 gap + remapping + batch 1 trust core + Item 34 |
| **Done** | **Items 1 & 2** core (P0/P1 prompts). Item 1 P8/P9 and Item 2 P8 remain optional P2. |
| **Done** | **Items 18+23** (2026-09-23): IKE-2 resolver L5 miss → fire-and-forget upsert into `ike2_unknown_queue` (`core/knowledge/ike2/unknown_queue.py`); worker `enrich_unknown_batch` drains the queue and writes `ike2_*` via adapt→validate→reconcile as source `enrichment_api` (DISCOVERED on greenfield insert, tier 1; rows exhaust after 5 failed attempts); legacy-only fields live in `enrichment` jsonb; one-shot `scripts/ike2_migrate_unknown_queue.py` carried `wheat flour` only (junk `a`/`b`/`zyzzx…` skipped); Beat hourly, embedded (`worker -B`) in the compose `worker` (cache profile). **Live closeout:** `run_enrich_unknown_once.py` → USDA FDC high-confidence hit on `wheat flour`; queue `pending`→`resolved` (excluded from retries); merge into existing ontology `AUTO_CLASSIFIED` row kept trust (no spurious demotion on flag agreement); `trust_refreshed_at` bumped (Item 4.1 decay clock). Greenfield isolated-group path unit-tested; first novel live miss still to be watched. |
| **Done** | **Item 33 through Prompt 4** (2026-09-27), plus the cache/catalog batch found while wiring resolve. HTTP `POST /resolve-ingredient` and `GET /ingredient/{name}` serve IKE-2 via `map_ike2_to_resolved_response` (full IKE-2 flags, not `Ingredient.to_dict()`). `try_api` / `log_unknown` are no-ops. `unknown_log.record` enqueues `ike2_unknown_queue`; `upsert_unknown_ingredient` no longer writes. Cache seed keeps the higher `knowledge_state` and does not drop a lower row’s uncertainty or missing `verdict_cap`. Catalog checker source-ambiguity tokens include yeast/tapioca/corn/microbial/fermentation/bacterial (live hits E626/E630/E631 only; those rows were not edited). Cross-source scan: 13 shared keys, 9 agree. Of 4 disagreements: bone phosphate/E542 and disodium inosinate/E631 kept on the cache merge; **l-cysteine** hand anchor dropped unconditional `animal_origin` and took the catalog hedge so `l-cysteine` / `cysteine` / `E920` / `E910` share one vegan verdict (WARN → user-facing UNCERTAIN); soy lecithin/E322 left as a named-form subset of an ambiguous generic code. |
| **Done** | **Item 33 core** (2026-09-27, Prompts 1–6). HTTP resolve is IKE-2. `unknown_ingredients` is no longer written. Redis resolve cache, `lifecycle.py`, and `CanonicalResolver` are deleted. Full suite 1849 passed, 4 skipped, 0 failed. `IngredientRegistry` remains for ontology tests and `verify_ingredient_flow.py` (optional Prompt 7). |
| **Done** | Hand-vs-catalog agreement test (`tests/ike2/test_hand_catalog_agreement.py`). A new disagreeing pair fails until it is reviewed. |
| **Done** | **Items 9 and 10.1** (2026-09-30). `/api/v1` requires a known key when `ENVIRONMENT=production`. Evaluate keeps `verdict` and adds `ike2` (`schema_version`, per-restriction breakdown, optional matrix). Key `rpm` overrides the tier. Vegan + pescatarian is 400 on profile and evaluate. Full suite **1858 passed, 4 skipped, 0 failed**. |
| **Done** | **Item 11 Phase 1** (2026-10-01). Live groups: `ifct` 324, `fssai` 755, `usda` 3,439, all AUTO_CLASSIFIED. USDA quarantined 136 `dairy_implies_animal` rows. Alias region `India` retagged to `IN`. Learned regional junk cleared off the enrichment lookup path. |
| **Done** | **Item 11 INFOODS AnFooD2.0** (2026-10-05). Live: `infoods` 521 new AUTO_CLASSIFIED (100 merges onto existing; 0 rejects; 0 demotions). Preceded by true-only repair of 1,698 ontology `asserted_flags` full-block pollution. Deliberate full-table `asserted_flags` audit note in `item11_asserted_flags_design.md` §9 — do not rely on the next source to rediscover that signature. |
| **Done** | **Item 11 JECFA/INS investigation** (2026-10-06). Report only: `docs/item11_jecfa_investigation.md`. No official bulk feed; CC BY-NC-SA / WHO permission gate fails allowlist; coverage largely alias/metadata vs `e_number_catalog` + FSSAI INS. **Do not register / do not build** until license + slice reopened. |
| **Done** | **Item 6 LLM harden** (2026-10-07). Spec `docs/item6_llm_pipeline_spec.md`. No pipeline abstraction. Stale scan-LLM docs retired; dead `llm_compose_profile_update` removed; classify/English-hint timeouts in config; IKE-2↔LLM import boundary + enrichment DISCOVERED tests. Full suite **1891 passed, 4 skipped, 0 failed**. |
| **Done** | **Item 7 Testing & QA** (2026-10-07). Spec `docs/item7_testing_qa_spec.md`. DB-rule-parity gate (seed ≡ migration-replayed rules on never-SAFE); corpus **120→147** thin-restriction expansion; CI Must-never-Safe step includes parity test. Fuzz/soak remain P2. |
| **Done** | **Item 7 / 37 sulfite + stem triage** (2026-10-07). Reports `docs/item7_sulfite_underflag_investigation.md`, `docs/item37_part_abc_closeout.md`. E220–E228 catalog/ontology/derive/hand + live reconcile backfill + L3-bypass 0 SAFE; same-day gluten/lupin/sesame/shellfish; derive dairy/lupin/mustard/celery; orthographic SAFE≠NOT_SAFE gate; catalog allergen-default audit. |
| **Deferred** | 15, 30; koji firm-Avoid (Item 3.1 P2); Redis-for-IKE-2; Item 29 no urgency. **Religious `min_knowledge_state`:** stored as `DISCOVERED` (same as lifestyle; allergy/medical are `AUTO_CLASSIFIED`). `evaluate()` does not read `rule.min_knowledge_state` after Item 34, so changing the stored value does not change a live Halal, Kosher, or Jain verdict. Reopening the bar is a rule-engine question, not an Item 9/10.1 label change. |
| **Carry to Item 12** | Failed queue writes are verdict-silent but only logged (`IKE2_UNKNOWN_QUEUE_WRITE_FAILED`); wire into miss_class / Sentry telemetry. If queue attempts/last-attempt need frequent filtering, promote them from jsonb to columns. The resolve metrics writer was deleted in Item 33 Prompt 5, so IKE-2 resolution telemetry starts from zero. Once Item 12 observability exists: scheduled Supabase Beat full-table scan that **reports** if the `asserted_flags` full-block pollution signature reappears (hang on telemetry; see `item11_asserted_flags_design.md` §9). |
| **Carry to Item 33** | Prompt 7 deferred: `IngredientRegistry` stays for ontology tests and `verify_ingredient_flow.py`; unused `record_resolution_metric` stays with it. |

---

## Decisions that stay locked

See `docs/phase2_gap_analysis.md` §1 (including Items 5/6/10.1/12). Highlights: CLI review end-state; one immediate-commit pattern; Item 6 harden-not-abstract; 10.1 no evaluate rewrite + reject contradictory diets at profile-set; 12 productize stores + Sentry; Beat→`ike2_unknown_queue` with 18.
