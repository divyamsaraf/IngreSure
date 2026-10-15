# IngreSure — Build Specification: Item 16
## Legacy vs IKE-2 Consolidation & Cutover

**Status:** Live migration — **stage `primary`**. Deliberate chat + API primary soaks both clean (`0` false_safe). Prompt 7 (legacy removal) authorized on verification criteria; execute when ready.
**Companion files:** `ingresure_architecture_tracker.xlsx` (Master Task List, row ID "16") · `docs/system_state_audit.md` (source of every fact referenced below)

---

## 0. How to use this document

This is the highest-priority item in the entire tracker right now — higher than continuing Items 1–2, 3, or anything else. Every fact in Sections 1 and 4 comes directly from the system state audit dated 2026-08-06 — do not re-derive or assume anything about the current state that isn't sourced from there. Where this document says "identify" or "confirm" rather than stating a fact outright, that's deliberate: the audit didn't capture full function signatures, and guessing at them here would be exactly the kind of hallucination this whole documentation discipline exists to prevent. Investigate first, then implement.

Keep this at `docs/item16_legacy_cutover_spec.md` in the repo.

---

## 1. Current state (confirmed by audit — do not re-verify, act on this)

- Chat flow (`bridge.run_new_engine_chat` → `_run_ike2_compliance`) already treats IKE-2 as primary, with fail-closed to `UNCERTAIN` on failure and no legacy fallback for the user-facing verdict.
- `POST /api/v1/evaluate-compliance` and `POST /api/v1/evaluate-product` still call the legacy `ComplianceEngine` (`core/evaluation/compliance_engine.py`) directly and exclusively.
- `IKE2_MODE=shadow` is set in `.env` but is **never read by any application code** — it is dead configuration, not an active gate.
- The legacy shadow-diff mechanism already exists and works: `core/knowledge/ike2/shadow/comparator.py` (`compare(legacy, ike2, raw_input) → match, false_safe_regression`) and `runner.py` (`run_legacy_diff`), writing mismatches to `ike2_shadow_diffs`, triggered by `bridge._schedule_legacy_diff` after every chat compliance run.
- Stage / cutover status is recorded in the architecture tracker and this file — not a separate `PHASES.md` (dropped; recreating it would reintroduce doc-reality drift).

---

## 2. Purpose of this component

Make `IKE2_MODE` a real, functioning control again, use it to move `/api/v1/evaluate-compliance` and `/api/v1/evaluate-product` through a verified, reversible cutover from legacy to IKE-2, and then actually delete the legacy compliance path once the verification window confirms it's safe — closing the exact kind of documentation/reality gap that made the full system audit necessary in the first place.

---

## 3. Scope

### In scope
- Reviving `IKE2_MODE` as a real three-value control read by application code
- Migrating both legacy-only endpoints to route through IKE-2
- Extending the existing shadow-diff mechanism to cover these two endpoints during the transition window
- A test migration plan for the legacy-specific test coverage identified in the audit
- A concrete, checked-off removal of legacy compliance code once the window closes

### Explicitly out of scope
- Any change to the chat flow's existing IKE-2-primary behavior — it's already correct, leave it alone
- Resolving the dual unknown-ingredient-queue problem (Item 18) — related, but a separate task
- Any new data ingestion or entity resolution work (Items 1, 2, 17)
- Deleting the `ike2_shadow_diffs` table or shadow mechanism itself — it stays permanently as reusable cutover infrastructure for future migrations, not just this one

---

## 4. Target design: reviving `IKE2_MODE`

```python
# core/config.py — must actually be read this time
IKE2_MODE: Literal["legacy", "shadow", "primary"] = os.environ.get("IKE2_MODE", "shadow")
```

| Mode | Behavior for the two endpoints |
|---|---|
| `legacy` | Legacy `ComplianceEngine` result is served. IKE-2 is not computed. This is the instant-rollback state — use it only if something goes wrong in `shadow` or `primary`. |
| `shadow` | **Starting state for this migration.** Legacy result is served to the caller (no behavior change visible externally). IKE-2 is computed in parallel and diffed via the existing `comparator.compare()` function, logged to `ike2_shadow_diffs` exactly as chat already does. |
| `primary` | IKE-2 result is served to the caller. Legacy is still computed in the background purely for comparison logging, same pattern as chat's current behavior. |

**Rule: never skip a stage.** `legacy → shadow → primary → removed` in that order, each stage held for a deliberate verification window (length is your call — a fixed number of requests or a fixed time period, whichever you can actually observe results against) before advancing.

---

## 5. Endpoint migration plan

**Step 1 — identify, don't assume.** Before touching either endpoint, locate the actual function `_run_ike2_compliance` (or whatever the real core IKE-2 evaluation function is called) in `core/knowledge/ike2/`, and document its exact input/output signature. Confirm whether it expects free-text + profile context (as chat provides) or can accept a structured ingredient list — this determines how much adaptation each endpoint needs.

**Step 2 — `/api/v1/evaluate-compliance`.** Currently takes an ingredient list plus `restriction_ids` and calls legacy `ComplianceEngine`. Wire this to call the real IKE-2 evaluation function identified in Step 1, mapping `restriction_ids` to whatever IKE-2's `ike2_restriction_rules` lookup expects. If the input shapes don't line up cleanly, write a thin adapter function specific to this endpoint rather than changing IKE-2's core function to accommodate it.

**Step 3 — `/api/v1/evaluate-product`.** Currently parses label text, then evaluates via legacy `ComplianceEngine`. Reuse the existing label-parsing code unchanged, then route the parsed ingredient list through the same IKE-2 path built in Step 2 rather than duplicating logic.

**Step 4 — response contract check.** Confirm what these endpoints' actual callers (frontend BFF routes, or any external consumer) expect in the response shape. If the legacy response shape is depended on downstream, wrap IKE-2's output to match it rather than breaking callers — a contract change, if needed, is a separate decision from the engine cutover itself.

---

## 6. Verification windows

### Shadow stage (before `primary`)

Before advancing from `shadow` to `primary`:
- Zero `false_safe_regression=true` rows in `ike2_shadow_diffs` for these two endpoints over the verification window. Any occurrence blocks advancement — investigate and fix before moving on, no exceptions, since a false-safe regression is the single worst failure mode this whole trust architecture exists to prevent.
- A reviewed sample of `match=false` (non-regression) diffs — mismatches that aren't false-safe are still worth understanding, since they may reveal a case IKE-2 handles differently (possibly correctly, possibly not) from legacy.

### Primary stage (before Prompt 7 / legacy removal) — **same bar, not a lighter one**

- **Chat:** ~7 days of organic post-primary traffic, then:
  `python scripts/ike2_shadow_soak_report.py --since <primary_flip> --source-route chat --fail-on-regression`
- **API:** organic traffic may stay thin — re-run a deliberate corpus batch under `IKE2_MODE=primary` (same approach as shadow) and confirm `0` `false_safe_regression` on `api_evaluate_compliance` and `api_evaluate_product`.
- Spot-check reviewed `match=false` samples the same way as shadow (fail-closed softer cases OK; `legacy=NOT_SAFE`→`ike2=SAFE` is not).

---

## 7. Test migration plan

- Audit-identified legacy-focused tests (compliance engine, restrictions, evaluate-* routes) stay in place and passing through the `legacy` and `shadow` stages — they're your regression safety net while nothing user-facing has changed yet.
- Before advancing to `primary`, add equivalent tests asserting the IKE-2 path for both endpoints, covering the same scenarios the legacy tests cover — don't advance on faith that IKE-2 "probably handles it."
- Only after Stage 3 (legacy code removed) do the legacy-specific tests get deleted — not before, and not as part of the same commit that removes the code, so there's a clean point where "legacy tests still pass against legacy code" is provably true right up until removal.

---

## 8. Removal checklist (Stage 3 — do not skip any line)

- [ ] `shadow` and `primary` verification windows both passed with zero false-safe regressions (primary = 7d chat soak + deliberate API batch; same bar as shadow)
- [ ] IKE-2-equivalent tests exist and pass for both endpoints
- [ ] `core/evaluation/compliance_engine.py` and its legacy-only callers deleted, not just unrouted
- [ ] Legacy-specific tests for the two endpoints removed
- [ ] Cutover stage of record updated in the architecture tracker + this file (do **not** recreate `PHASES.md`)
- [ ] `ike2_shadow_diffs` mechanism explicitly kept — flag in the PR/commit that this stays as reusable infrastructure for Item 18 and any future migration, not removed alongside legacy

---

## 9. Numbered build prompts for Cursor

**Prompt 1** — Investigate and report: locate the real function signature of IKE-2's core compliance evaluation (the one `bridge.run_new_engine_chat` calls via `_run_ike2_compliance`). Report its exact input/output types back before any other work — do not proceed to Prompt 2 until this is confirmed against real code, not assumed.

**Prompt 2** — Implement the three-value `IKE2_MODE` read in `core/config.py` exactly as specified in Section 4. Default to `shadow`. Add a test confirming each of the three modes produces the documented behavior for a stub endpoint.

**Prompt 3** — Migrate `/api/v1/evaluate-compliance` per Section 5, Steps 1–2 and 4. Implement `shadow` mode behavior first: legacy result still served, IKE-2 computed and diffed via the existing `comparator.compare()`, logged to `ike2_shadow_diffs`.

**Prompt 4** — Migrate `/api/v1/evaluate-product` the same way, per Section 5, Step 3.

**Prompt 5** — Add the IKE-2-equivalent test coverage described in Section 7 for both endpoints, run against `shadow` mode without changing served behavior.

**Prompt 6** — Once the verification window in Section 6 has been manually confirmed clean (this is a judgment call for Divyam, not something Cursor decides), flip `IKE2_MODE` to `primary` for both endpoints and confirm response contracts per Section 5 Step 4 are preserved.

**Prompt 7** — After the `primary` window is confirmed stable (Section 6 — same bar as shadow), execute the removal checklist in Section 8 exactly, line by line. Update the architecture tracker + this file; do not recreate `PHASES.md`.

---

## 10. Keeping this file in sync

Update this file and `ingresure_architecture_tracker.xlsx` (Item 16's Notes column) at each stage transition (`legacy → shadow → primary → removed`) — this is a live migration, and the tracker should always reflect which stage is currently active, not just "done" or "not done."

### Stage log

| When | Stage | Notes |
|------|-------|-------|
| 2026-08-07 | **shadow** | `get_ike2_mode()` live; both evaluate endpoints use `core.api.v1_evaluate.evaluate_ingredients`. Default `IKE2_MODE=shadow`. Chat untouched. |
| 2026-08-07 | **shadow (instrument fixed)** | Added `source_route` + `restriction_ids` … Prompt 6 still blocked until a clean **instrumented** window. |
| 2026-08-07 | **shadow (verification window opened — not complete)** | Instrumentation = Items 26/27 done. **Gate not satisfied yet.** (1) Chat: need 7 days of *post-migration* organic/instrumented `source_route=chat` rows after `2026-08-07T23:40:00Z` — spot-check ≠ window. (2) API: deliberate corpus batch via `scripts/ike2_api_shadow_traffic_batch.py` completed (457×2 HTTP calls, `IKE2_MODE=shadow`); post-migration API soak: **0** `false_safe_regression` on both routes. (3) Human review of match=false/non-reg samples recorded in chat — see representative examples; flag softer IKE-2 cases (`legacy=NOT_SAFE`→`ike2=UNCERTAIN` on jain+enzymes). Prompt 6 remains blocked until chat window completes. Cutover timestamp for `--since`: `2026-08-07T23:40:00+00:00`. |
| 2026-08-07 | **shadow (API §6 complete; chat window still open)** | **API endpoints:** Section 6 both criteria met for deliberate traffic — 0 `false_safe_regression` on `api_evaluate_compliance` / `api_evaluate_product` post-migration, plus reviewed `match=false` sample. Fail-closed softer cases (**not** Prompt-6 blockers): (a) Jain yeast/enzymes `legacy=NOT_SAFE`→`ike2=UNCERTAIN` — likely missing IKE-2 sub-variant fermentation/enzyme coverage (track with Item 3.1, not a false-safe); (b) gluten_free/celiac `SAFE`→`UNCERTAIN` over-pull — precision/UX, lower priority. **Chat:** 7-day post-migration `source_route=chat` window still required before Prompt 6. Item 16 remains In Progress. |
| 2026-08-12 | **shadow (chat soak spot-check)** | Post-migration `source_route=chat` soak: 63 diffs, **0** `false_safe_regression`. All rows from 2026-08-07 burst (not multi-day organic). Tallies: UNCERTAIN→SAFE 33, SAFE→UNCERTAIN 22, UNCERTAIN→NOT_SAFE 8. |
| 2026-09-16 | **primary** | Prompt 6 authorized: `IKE2_MODE=primary` in `backend/.env` + `.env.example`. Both evaluate endpoints serve IKE-2; legacy background-diff retained. Response contract unchanged (`ComplianceVerdict.to_dict()`). `PHASES.md` not present in repo — stage of record is this file. Prompt 7 (removal checklist) still blocked on a stable primary window. |
| 2026-09-16 | **primary (soak run)** | Deliberate primary window since `2026-09-16T21:42:10+00:00`: API batch `--mode primary` → 457×2 HTTP **0 errors**; soak **0** `false_safe_regression` on `chat` / `api_evaluate_compliance` / `api_evaluate_product` (171 mismatch rows logged). Truth anchors served correctly (wheat gluten/gluten_free, gelatin/vegan, milk/dairy_free, egg/egg_free, peanut, pork/halal, beef/hindu_veg, onion/jain, clean vegan → SAFE). Safety tests 25 passed. **Open correctness issue (not caught by comparator):** 5× `legacy=NOT_SAFE`→`ike2=SAFE` all Jain+yeast — plain `yeast` resolves with empty flags so `fungal` FAIL rule never fires; `baker's yeast` correctly `fungal=True`→NOT_SAFE. Track as Item 3.1 / ontology flag gap. Prompt 7 still judgment-gated on that. |
| 2026-09-16 | **primary (fungal root-cause fix + re-soak)** | Fixed class, not one-off: (1) `flag_derive.derive_identity_flags` ORs `fungal` from yeast/mushroom/tempeh/mycoprotein/koji tokens; (2) Tier-1 yeast + yeast-extract anchors with `fungal=True` (empty L1 no longer shadows L2); (3) stopped `tempeh`→soybean+water recipe expansion that stripped fungal identity; (4) ontology yeast extract / tempeh `fungal=true`; aliases for instant/nutritional yeast. Re-soak since `2026-09-16T21:56:05Z`: 914 API OK, **0** false_safe, **0** NOT_SAFE→SAFE; yeast/yeast extract/tempeh/jain → NOT_SAFE. Remaining mismatches are fail-closed or benign UNCERTAIN↔SAFE under unrelated restrictions. |
| 2026-09-16 | **primary (window open — same bar as shadow)** | API deliberate primary batch (post-fungal) satisfied. Chat: wait ~7 days organic traffic after primary flip, then `--since <flip> --source-route chat --fail-on-regression`. `PHASES.md` checklist line dropped — SoT is tracker + this file; README dead link updated. Prompt 7 still blocked on chat window. |
| 2026-09-16 | **primary (chat deliberate batch — window satisfied)** | Replaced passive 7d wait with `scripts/ike2_chat_shadow_traffic_batch.py` through `/chat/grocery` (intent + profile + compliance). 457 corpus + 13 fermentation extras, `IKE2_MODE=primary`, **0** errors. Soak since `2026-09-16T22:15:48Z` `source_route=chat`: **0** `false_safe_regression`, **0** `NOT_SAFE`→`SAFE`. Yeast/yeast extract/tempeh/mushroom/nutritional yeast → Avoid under Jain; koji/miso/tamari/natto → Depends (fail-closed, unresolved — not firm SAFE). Prompt 7 unblocked on verification criteria. |

---

## 11. Prompt 1 findings (investigation — confirmed against code 2026-08-07)

**Do not treat this section as implementation.** Confirmed against `backend/core/bridge.py`, `ike2/compliance.py`, `ike2/seam.py`, `api/v1/schemas.py`.

### Core function used by chat

| Layer | Symbol | Location |
|-------|--------|----------|
| Chat wrapper | `run_new_engine_chat(...)` | `bridge.py` |
| Pipeline runner | `_run_ike2_compliance(...)` | `bridge.py` L420–466 |
| Core evaluator | `ike2_compliance.evaluate(resolved, profile, rules)` | `ike2/compliance.py` L362 |
| Response mapper | `map_ike2_to_compliance_verdict(result, inputs, ...)` | `bridge.py` L271 |

### `_run_ike2_compliance` signature (exact)

```python
def _run_ike2_compliance(
    ingredients: List[str],
    restriction_ids: Optional[List[str]],
    prepared_decomposed: Optional[List[Any]] = None,
    region: Optional[str] = None,
) -> Tuple[Any, List[Any], Dict[str, str]]:
```

**Returns:** `(ComplianceResult, list[ComplianceInput], display_map: dict[str, str])`.

**Input shape:** Accepts a **structured ingredient string list** (`List[str]`), not free-text chat. Optionally accepts pre-decomposed atoms (`prepared_decomposed`). Maps `restriction_ids` → `SimpleNamespace(restrictions={rid: "medical", ...})` via `_profile_from_restriction_ids`. Loads rules via `ike2_rules.load_rules()`, resolves each atom via `ike2_resolver.resolve`, flattens via `to_compliance_input`, then calls `evaluate`.

**Implication for endpoints:** `/api/v1/evaluate-compliance` already takes `ingredients: List[str]` + `restriction_ids` — **aligns cleanly** with `_run_ike2_compliance`. Thin adapter + `map_ike2_to_compliance_verdict` → `ComplianceVerdict.to_dict()` should preserve the response contract. `/api/v1/evaluate-product` keeps `preprocess_ingredients_to_strings`, then same path.

### `ike2.compliance.evaluate` signature (exact)

```python
def evaluate(resolved, profile, rules) -> ComplianceResult:
```

- `resolved`: iterable of `ComplianceInput` (fields: `canonical_name`, `flags`, `knowledge_state`, `trusted`, `alcohol_role`, `verdict_cap`, `trace`, `may_contain`)
- `profile`: object with `.restrictions: dict[str, severity]` (IKE-2 uses `"medical"` default)
- `rules`: loaded restriction rule objects (`SimpleNamespace` from `rules.load_rules()` / DB)

### Response contract

Both endpoints return `verdict: Dict` via `ComplianceVerdict.to_dict()`. Frontend does **not** call `/api/v1/*` (see `docs/api-v1-and-frontend-endpoints.md`). Callers are programmatic.

### Adapter notes (for Prompt 3+)

- Prefer calling `_run_ike2_compliance` + `map_ike2_to_compliance_verdict` over changing `evaluate`.
- Legacy fields `use_api_fallback` / `profile_context` are not consumed by `_run_ike2_compliance`; map `region_scope` → `region` if needed.
- Shadow for endpoints should reuse `comparator.compare` / `run_legacy_diff` patterns; gate on revived `IKE2_MODE`.
