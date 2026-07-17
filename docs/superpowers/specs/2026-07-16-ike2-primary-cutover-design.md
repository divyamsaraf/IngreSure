# IKE-2 Primary Cutover Design

**Date:** 2026-07-16  
**Status:** Approved  
**Branch:** `feat/ike2-engine`

## Goal

Make IKE-2 the only user-facing compliance engine for `/chat`. Legacy `ComplianceEngine` runs only as a non-blocking comparison (diff log). Collapse `IKE2_MODE` to `primary` only. Keep the existing `/chat` response schema via `ComplianceVerdict` mapping. Do **not** expose `response.assemble` (b2c/b2b) in this phase.

## Non-goals

- No `response.assemble` on `/chat` (future B2B roadmap).
- No rename/migration of Supabase table `ike2_shadow_diffs` (keep table; rename code/log field labels).
- No edits to README / QUICKSTART / PHASES / PROJECT_DETAILS / backend README in this PR (flagged stale only).
- Do not commit `backend/.env` (local `IKE2_MODE=shadow` coerces at import time).

---

## 1. Config

**File:** `backend/core/config.py`

- Valid value going forward: **`primary` only**.
- Unset, or set to `off` / `shadow` / `fallback` / any other string → **silently coerce** to `primary`.
- **No warning, no log line, no special-casing** for deprecated values — treat any non-`primary` value the same as unset.
- Default when unset: `primary`.

Coercion happens once at module import (process boot). Callers read the already-coerced `IKE2_MODE` module attribute; they must not re-parse env per request.

---

## 2. Bridge request flow

**File:** `backend/core/bridge.py` — rewrite `run_new_engine_chat`.

```
ingredients + restriction_ids (+ optional prepared_decomposed)
  → IKE-2 pipeline (parse/atoms → resolve → seam → rules → evaluate)
  → map_ike2_to_compliance_verdict(...)
  → schedule legacy diff (background, non-blocking, with timeout)
  → return mapped ComplianceVerdict to caller
```

### User-facing path (IKE-2)

1. Build restriction profile the same way as today (`restriction_ids` / profile maps).
2. Run IKE-2 end-to-end (reuse pipeline pieces already used by `ike2_external_verdict` / shadow runner: `input_layer` or `prepared_decomposed`, `resolver.resolve`, `to_compliance_input`, `rules.load_rules`, `compliance.evaluate`).
3. Map result with `map_ike2_to_compliance_verdict`.
4. Return that `ComplianceVerdict`. **No code path may return a legacy verdict to `/chat`.**

### Fail-closed IKE-2 errors

If IKE-2 raises or cannot produce a result:

- Return `ComplianceVerdict(status=VerdictStatus.UNCERTAIN, …)` (empty trigger lists OK).
- Log with enough context to debug: **input hash** (hash of normalized ingredient list / atoms; respect `LOG_REDACT_PII` — do not dump raw PII when redaction is on), exception, timestamp, `restriction_ids`.
- **Never** substitute a legacy SAFE / NOT_SAFE / UNCERTAIN as the user response.

### Legacy diff — non-blocking (amendment)

- After the IKE-2 `ComplianceVerdict` is ready to return, schedule legacy evaluation + diff logging as a **background task** (fire-and-forget).
- **Response latency = IKE-2 only.** Do not await legacy before returning.
- Implementation fit for sync `run_new_engine_chat` called from async FastAPI: `concurrent.futures.ThreadPoolExecutor` (or equivalent daemon thread) with an explicit **timeout** on the legacy work. On timeout or exception: log and drop; never affect the returned verdict.
- Prefer a small shared executor (module-level) over unbounded thread spawn; YAGNI — one small helper is enough.
- Pass already-known IKE-2 external status string into the diff logger so the background job does not need to re-run IKE-2.

---

## 3. Mapper: `map_ike2_to_compliance_verdict`

**Suggested location:** `backend/core/bridge.py` or small helper module under `backend/core/knowledge/ike2/` if bridge grows too large — prefer bridge-adjacent unless file size forces a split.

**Signature (conceptual):**

```python
def map_ike2_to_compliance_verdict(
    result,  # ike2.compliance.ComplianceResult
    inputs,  # list[ComplianceInput] (or equivalent atom context)
    *,
    ontology_version: str = "",
) -> ComplianceVerdict
```

### Field mapping

Reuse existing `ComplianceVerdict` fields exactly — no schema change:

| Field | Source |
|--------|--------|
| `status` | `VerdictStatus(to_external(result.verdict))` — **inherit** `to_external`; do not reimplement severity tables |
| `triggered_restrictions` | Distinct restrictions from `result.breakdown` / caution / matched rows where the rule fired |
| `triggered_ingredients` | Prefer `matched_contains` (major); include display names when available |
| `uncertain_ingredients` | Inputs with unresolved / UNCLASSIFIED / untrusted / external UNCERTAIN contribution |
| `informational_ingredients` | Trace / may_contain minors that should not drive headline confidence (align with legacy semantics where cheap) |
| `triggered_ingredient_to_input` | Map canonical → raw input when decomposition metadata is available |
| `confidence_score` | Conservative: lower when any uncertain/untrusted atoms; do not invent a new scoring system — keep simple and fail-closed |
| `ontology_version` | Pass-through optional string (empty OK) |

### Partial resolution (amendment)

If some ingredients are unknown/unresolved and others are clean, IKE-2 `evaluate` + `aggregate` already degrade away from firm SAFE (unresolved → UNCLASSIFIED / untrusted paths → UNCERTAIN or WARN). The mapper **must** set `status` solely via `to_external(result.verdict)` so mixed/partial resolution cannot be silently upgraded to SAFE by the mapper. Confirm in tests: mixed known+unknown under a restrictive profile is never mapped to SAFE when `to_external` says otherwise.

**Out of scope:** calling `response.assemble`.

---

## 4. Diff logger — roles flipped

**Files:** `backend/core/knowledge/ike2/shadow/runner.py`, `comparator.py` (and call sites).

- Keep table `ike2_shadow_diffs`.
- Rename APIs / variables / log fields so **legacy is explicitly the comparison side**:
  - Prefer names like `run_legacy_diff`, `primary_verdict` (IKE-2), `legacy_verdict`.
  - Insert/log payload may keep DB column names if schema-fixed (`ike2_verdict` / `legacy_verdict`); if columns are fixed as today, map `primary` → existing `ike2_verdict` column and document that in code comments. Do not migrate DB in this PR.
- `false_safe_regression`: still true when **IKE-2 (primary) is SAFE** and **legacy is more severe** (same safety meaning as before cutover).
- Mode gate: drop `IKE2_MODE == "shadow"` checks; under primary-only config, diff scheduling is always attempted from bridge (fail-safe).
- Diff function itself remains sync; bridge wraps it in the background executor + timeout.

### Test (c2) — agreement case

When IKE-2 and legacy external statuses agree: diff records `match=True` and `false_safe_regression=False`.

---

## 5. Codebase sweep

| Area | Action |
|------|--------|
| `config.py` | Coerce to `primary` |
| `bridge.py` | Primary flow + mapper + background legacy |
| `shadow/runner.py`, `comparator.py` | Rename/clarify; always usable as legacy-diff |
| Tests using `IKE2_MODE=off\|shadow` | Update to primary / coercion / new bridge behavior |
| `ike2_shadow_soak_report.py`, label corpus shadow helpers | Update comments + any mode assumptions; flag if behavior change is unclear |
| README / QUICKSTART / PHASES / PROJECT_DETAILS / backend README / database README | **Flag only — do not edit in this PR** |
| `backend/.env` | **Do not commit**; runtime coercion handles local `shadow` |

Anything ambiguous → leave a `FLAG:` comment or note in the PR description; do not guess.

---

## 6. Tests (required)

TDD: write failing tests first for each behavior.

| ID | Behavior |
|----|----------|
| (a) | IKE-2 success → `map_ike2_to_compliance_verdict` produces correct `ComplianceVerdict` fields / status |
| (b) | IKE-2 exception in bridge → `UNCERTAIN`; response is not a legacy verdict (even if legacy would say SAFE/NOT_SAFE) |
| (c) | When IKE-2 and legacy disagree, returned verdict is IKE-2 (mapped); legacy still scheduled for diff |
| (c2) | When they agree, diff log has `false_safe_regression=False` (and match true) |
| (d) | Old `IKE2_MODE` values coerce to `primary` with **no crash** (no warning assertion) |

Also: background/non-blocking — assert return path does not wait on a deliberately slow legacy mock (e.g. legacy sleep longer than a short tolerance, response still returns quickly). Timeout path logs and does not raise into caller.

---

## 7. Error handling summary

| Failure | User result | Side effect |
|---------|-------------|-------------|
| IKE-2 exception | UNCERTAIN | Error log with input hash / exception / timestamp / restriction_ids |
| Legacy background timeout/error | Unchanged IKE-2 response | Warning log; no raise |
| Diff DB insert fail | Unchanged | Existing fail-soft logging |

---

## 8. Success criteria

1. `/chat` never returns a legacy-sourced status.
2. Default/coerced mode is always `primary`.
3. Chat latency dominated by IKE-2; legacy is background + timed out.
4. Existing `ComplianceVerdict` / stream card fields still work without frontend changes.
5. Required tests (a)(b)(c)(c2)(d) + non-blocking check pass.
6. Docs listed above remain unedited in this PR (stale/todo flagged outside the PR).

---

## Stale docs (flag only)

These still describe `IKE2_MODE=off|shadow` and legacy-as-user-facing — **do not edit in this PR**:

- `README.md`
- `QUICKSTART.md`
- `backend/README.md`
- `database/README.md`
- `PHASES.md`
- `PROJECT_DETAILS.md`
