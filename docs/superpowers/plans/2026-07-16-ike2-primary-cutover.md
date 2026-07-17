# IKE-2 Primary Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. REQUIRED: superpowers:test-driven-development (red → green → refactor). After each task: superpowers:requesting-code-review. When applying review feedback: superpowers:receiving-code-review.

**Goal:** Make IKE-2 the only user-facing chat verdict; run legacy ComplianceEngine only as a timed background diff; collapse `IKE2_MODE` to silent `primary`.

**Architecture:** Coerce config to `primary`. Rewrite `run_new_engine_chat` to run IKE-2 → `map_ike2_to_compliance_verdict` → return; schedule `run_legacy_diff` on a shared thread pool with timeout. Keep `ike2_shadow_diffs` table; clarify field roles in code. No `response.assemble` on `/chat`. No README/docs edits in this PR.

**Tech Stack:** Python 3.11, pytest, FastAPI (async chat calls sync bridge), `concurrent.futures`, existing IKE-2 modules, `ComplianceVerdict`.

**Spec:** `docs/superpowers/specs/2026-07-16-ike2-primary-cutover-design.md`

## Global Constraints

- TDD mandatory: failing test first; no production code before red.
- `/chat` schema unchanged: only `ComplianceVerdict` fields already on `core.models.verdict.ComplianceVerdict`.
- Never return legacy verdict to `/chat`. IKE-2 failure → `UNCERTAIN` only.
- Legacy diff is background + timeout; response latency = IKE-2 only.
- Silent coercion for any non-`primary` `IKE2_MODE`; no warning logs.
- Do not edit README/QUICKSTART/PHASES/PROJECT_DETAILS/backend README/database README.
- Do not commit `backend/.env`.
- Do not call `response.assemble` from bridge/chat.
- Keep Supabase table name `ike2_shadow_diffs` (no migration).
- Tests from `backend/`: `./venv/bin/python -m pytest ...`
- Karpathy: surgical diffs; no speculative abstractions; verify before claiming done.

## File map

| File | Responsibility |
|------|----------------|
| `backend/core/config.py` | Coerce `IKE2_MODE` → `primary` |
| `backend/core/bridge.py` | IKE-2 primary path, mapper, background legacy schedule, fail-closed UNCERTAIN |
| `backend/core/knowledge/ike2/shadow/runner.py` | Rename to legacy-diff semantics; drop shadow-mode gate |
| `backend/core/knowledge/ike2/shadow/comparator.py` | Docstring/role clarity; keep `false_safe_regression` meaning |
| `backend/tests/test_ike2_primary_cutover.py` | New: (a)(b)(c)(c2)(d) + non-blocking |
| `backend/tests/ike2/test_shadow_runner.py` | Update for primary / renamed API |
| `backend/tests/test_chat_ingredients.py` | Drop `IKE2_MODE=shadow` assumptions |
| Soak/corpus scripts | Comment / mode assumption updates only if required for correctness |

---

### Task 1: Config — silent coerce to `primary`

**Files:**
- Modify: `backend/core/config.py`
- Test: `backend/tests/test_ike2_primary_cutover.py` (create)

**Interfaces:**
- Produces: module attr `IKE2_MODE: str` always `"primary"` after import-time coercion helper usable in tests.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ike2_primary_cutover.py
import importlib
import os

import pytest


def _reload_config(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("IKE2_MODE", raising=False)
    else:
        monkeypatch.setenv("IKE2_MODE", value)
    import core.config as config
    return importlib.reload(config)


@pytest.mark.parametrize("raw", [None, "", "off", "shadow", "fallback", "PRIMARY", "garbage"])
def test_ike2_mode_coerces_to_primary(monkeypatch, raw):
    cfg = _reload_config(monkeypatch, raw)
    assert cfg.IKE2_MODE == "primary"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_ike2_primary_cutover.py::test_ike2_mode_coerces_to_primary -v`

Expected: FAIL (still defaults to `off` or leaves `shadow` as-is).

- [ ] **Step 3: Minimal implementation**

In `backend/core/config.py` replace IKE2_MODE block with:

```python
def _coerce_ike2_mode(raw: str | None) -> str:
    v = (raw or "").strip().lower()
    return "primary" if v == "primary" else "primary"

IKE2_MODE: str = _coerce_ike2_mode(os.environ.get("IKE2_MODE"))
```

(Keep the helper so tests can reason about coercion; both branches return `"primary"` — that is intentional silent collapse.)

Simplify further if preferred:

```python
IKE2_MODE: str = "primary"  # only supported mode; env ignored except documented coerce
```

Prefer helper that reads env so `IKE2_MODE=primary` still works and non-primary is silently ignored:

```python
_raw = os.environ.get("IKE2_MODE", "primary")
IKE2_MODE: str = "primary" if (_raw or "").strip().lower() != "primary" else "primary"
# Equivalent always primary — write clearly:

def _coerce_ike2_mode(raw: str | None) -> str:
    # Only "primary" is valid; everything else (including unset) → primary. Silent.
    return "primary"

IKE2_MODE: str = _coerce_ike2_mode(os.environ.get("IKE2_MODE"))
```

Update the comment above it to say primary-only, silent coerce, no logs.

- [ ] **Step 4: Run test to verify it passes**

Run: same pytest command. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/config.py backend/tests/test_ike2_primary_cutover.py
git commit -m "ike2: only primary mode now"
```

---

### Task 2: Mapper `map_ike2_to_compliance_verdict` (TDD)

**Files:**
- Modify: `backend/core/bridge.py` (add function; keep chat runner for later task)
- Test: `backend/tests/test_ike2_primary_cutover.py`

**Interfaces:**
- Consumes: `core.knowledge.ike2.compliance.ComplianceResult`, `list` of `ComplianceInput`, `to_external`
- Produces: `map_ike2_to_compliance_verdict(result, inputs, *, ontology_version="") -> ComplianceVerdict`

- [ ] **Step 1: Write failing tests (a) + partial-resolution**

```python
from types import SimpleNamespace

from core.bridge import map_ike2_to_compliance_verdict
from core.knowledge.ike2.compliance import ComplianceResult
from core.knowledge.ike2.seam import ComplianceInput
from core.knowledge.ike2.verdict import Verdict, to_external
from core.models.verdict import VerdictStatus


def test_map_ike2_fail_to_not_safe():
    inputs = [
        ComplianceInput(
            canonical_name="gelatin",
            flags={"animal_origin": True},
            knowledge_state="LOCKED",
            trusted=True,
            alcohol_role=None,
            verdict_cap=None,
            trace=False,
        )
    ]
    result = ComplianceResult(
        Verdict.FAIL,
        matched_contains=["gelatin"],
        matched_may_contain=[],
        caution_reasons=["vegan:gelatin"],
        breakdown={("gelatin", "vegan"): Verdict.FAIL},
    )
    v = map_ike2_to_compliance_verdict(result, inputs)
    assert v.status == VerdictStatus.NOT_SAFE
    assert v.status.value == to_external(Verdict.FAIL)
    assert "gelatin" in v.triggered_ingredients
    assert "vegan" in v.triggered_restrictions


def test_map_partial_unknown_status_from_to_external_only():
    """Mapper must not upgrade; status comes only from to_external(result.verdict)."""
    inputs = [
        ComplianceInput(
            canonical_name="water",
            flags={},
            knowledge_state="LOCKED",
            trusted=True,
            alcohol_role=None,
            verdict_cap=None,
            trace=False,
        ),
        ComplianceInput(
            canonical_name="",
            flags={},
            knowledge_state="UNCLASSIFIED",
            trusted=False,
            alcohol_role=None,
            verdict_cap=None,
            trace=False,
        ),
    ]
    # Simulate evaluate outcome for mixed list: aggregate UNCERTAIN
    result = ComplianceResult(
        Verdict.UNCERTAIN,
        matched_contains=[],
        matched_may_contain=[],
        caution_reasons=["unverified_knowledge:vegan:"],
        breakdown={},
    )
    v = map_ike2_to_compliance_verdict(result, inputs)
    assert v.status == VerdictStatus.UNCERTAIN
    assert v.status.value == to_external(result.verdict)
    assert v.status != VerdictStatus.SAFE
```

- [ ] **Step 2: Run tests — expect FAIL (import / missing function)**

Run: `cd backend && ./venv/bin/python -m pytest tests/test_ike2_primary_cutover.py::test_map_ike2_fail_to_not_safe tests/test_ike2_primary_cutover.py::test_map_partial_unknown_status_from_to_external_only -v`

- [ ] **Step 3: Minimal mapper implementation**

```python
# in bridge.py
from core.knowledge.ike2.verdict import to_external
from core.models.verdict import ComplianceVerdict, VerdictStatus

def map_ike2_to_compliance_verdict(result, inputs, *, ontology_version: str = "") -> ComplianceVerdict:
    status = VerdictStatus(to_external(result.verdict))
    triggered_ingredients = list(dict.fromkeys(result.matched_contains or []))
    triggered_restrictions = []
    for (_name, restriction), verd in (result.breakdown or {}).items():
        if verd != Verdict.SAFE and restriction not in triggered_restrictions:
            # include restrictions that contributed non-SAFE or were triggered via matched
            pass
    # Prefer: restrictions appearing in breakdown keys where ingredient is in matched_contains
    # or verdict is FAIL/WARN/UNCERTAIN with a match. Keep simple:
    for (_name, restriction), verd in (result.breakdown or {}).items():
        if _name in triggered_ingredients and restriction not in triggered_restrictions:
            triggered_restrictions.append(restriction)
    if not triggered_restrictions:
        for reason in result.caution_reasons or []:
            rid = reason.split(":", 1)[0]
            if rid and rid not in triggered_restrictions and not rid.startswith("uncovered") and ":" in reason:
                # caution format is often "restriction:name" or "caution:restriction:name"
                pass
    # Practical minimal mapping:
    triggered_restrictions = sorted({
        restriction
        for (name, restriction), verd in (result.breakdown or {}).items()
        if name in triggered_ingredients or verd.value >= Verdict.UNCERTAIN  # IntEnum
    })
    # Simpler approach preferred in implementation — extract restriction ids from
    # matched names' breakdown entries only:
    triggered_restrictions = []
    seen = set()
    for (name, restriction), _verd in (result.breakdown or {}).items():
        if name in triggered_ingredients and restriction not in seen:
            seen.add(restriction)
            triggered_restrictions.append(restriction)

    uncertain = []
    for inp in inputs or []:
        if not getattr(inp, "trusted", True) or getattr(inp, "knowledge_state", "") in (
            "UNCLASSIFIED",
            "DISCOVERED",
        ) or not getattr(inp, "canonical_name", ""):
            label = getattr(inp, "canonical_name", "") or "unknown"
            if label not in uncertain:
                uncertain.append(label)

    informational = [
        getattr(inp, "canonical_name", "")
        for inp in (inputs or [])
        if getattr(inp, "canonical_name", "")
        and (getattr(inp, "trace", False) or getattr(inp, "may_contain", False))
    ]

    return ComplianceVerdict(
        status=status,
        triggered_restrictions=triggered_restrictions,
        triggered_ingredients=triggered_ingredients,
        uncertain_ingredients=uncertain,
        informational_ingredients=[x for x in informational if x],
        confidence_score=0.0 if uncertain or status != VerdictStatus.SAFE else 1.0,
        ontology_version=ontology_version or "",
    )
```

Implement the **simplest** version that passes the tests; do not over-engineer confidence.

- [ ] **Step 4: Tests pass**

- [ ] **Step 5: Commit**

```bash
git add backend/core/bridge.py backend/tests/test_ike2_primary_cutover.py
git commit -m "ike2: map compliance result to chat verdict"
```

---

### Task 3: Legacy diff runner rename + always-on API

**Files:**
- Modify: `backend/core/knowledge/ike2/shadow/runner.py`
- Modify: `backend/core/knowledge/ike2/shadow/comparator.py` (docstrings)
- Modify: `backend/tests/ike2/test_shadow_runner.py`
- Modify: `backend/tests/test_chat_ingredients.py` (call sites)

**Interfaces:**
- Produces: `run_legacy_diff(raw_ingredients, restriction_ids, region, primary_verdict, *, decomposed_atoms=None, writer=None)`  
  - `primary_verdict` = IKE-2 external status string  
  - Computes legacy external status inside (or accept a `legacy_verdict` if bridge already ran legacy — prefer runner runs legacy OR bridge passes both; **choose:** bridge background job runs legacy `ComplianceEngine` then calls `compare` + write; runner helper `log_legacy_diff(primary, legacy, raw_input, writer=)` to avoid double engines)
- Keep `compare(legacy_verdict, ike2_verdict, raw_input)` argument order **or** rename params for clarity but keep `false_safe_regression` = primary SAFE while legacy more severe. Update call sites carefully.
- Deprecated alias: `run_shadow = run_legacy_diff` only if needed for one release — YAGNI: update call sites, no alias unless tests need it briefly.

**Recommended split (surgical):**

1. `compare` stays; docstring says first arg is legacy, second is primary (IKE-2); `false_safe_regression` when primary SAFE and legacy more severe.
2. `run_legacy_diff(...)` no longer checks `IKE2_MODE`; always runs comparison when called.
3. Bridge background task: run legacy engine → `compare(legacy_ext, primary_ext, raw)` → insert/log.

- [ ] **Step 1: Failing tests (c2) + rename**

```python
from core.knowledge.ike2.shadow.comparator import compare


def test_compare_agreement_no_regression():
    diff = compare("NOT_SAFE", "NOT_SAFE", "gelatin")
    assert diff["match"] is True
    assert diff["false_safe_regression"] is False


def test_compare_false_safe_when_primary_safe_legacy_worse():
    # primary (ike2) SAFE, legacy NOT_SAFE → regression
    diff = compare("NOT_SAFE", "SAFE", "mystery")
    assert diff["false_safe_regression"] is True
```

Update `test_shadow_runner.py`: remove `IKE2_MODE=off` no-op test; replace with “`run_legacy_diff` runs without mode gate”.

- [ ] **Step 2: Run — red where needed**

- [ ] **Step 3: Implement renames + drop mode gate**

- [ ] **Step 4: Green**

- [ ] **Step 5: Commit**

```bash
git commit -m "ike2: legacy is diff-only now"
```

---

### Task 4: Bridge primary path + fail-closed UNCERTAIN (b)

**Files:**
- Modify: `backend/core/bridge.py` (`run_new_engine_chat`)
- Test: `backend/tests/test_ike2_primary_cutover.py`

**Interfaces:**
- `run_new_engine_chat(...) -> ComplianceVerdict` always from IKE-2 map or UNCERTAIN.

- [ ] **Step 1: Failing tests**

```python
from core.bridge import run_new_engine_chat
from core.models.verdict import VerdictStatus


def test_ike2_exception_returns_uncertain_not_legacy(monkeypatch):
    import core.bridge as bridge

    def boom(*args, **kwargs):
        raise RuntimeError("ike2 down")

    monkeypatch.setattr(bridge, "_run_ike2_compliance", boom)  # extract helper for testability

    # Legacy would say SAFE for water — must not be returned
    v = run_new_engine_chat(["water"], restriction_ids=["vegan"], use_api_fallback=False)
    assert v.status == VerdictStatus.UNCERTAIN


def test_ike2_success_returned_not_legacy(monkeypatch):
    from core.models.verdict import ComplianceVerdict, VerdictStatus
    import core.bridge as bridge

    fake = ComplianceVerdict(
        status=VerdictStatus.NOT_SAFE,
        triggered_restrictions=["vegan"],
        triggered_ingredients=["gelatin"],
    )
    monkeypatch.setattr(
        bridge,
        "_run_ike2_compliance",
        lambda *a, **k: fake,
    )
    # Force legacy to SAFE if it were used
    monkeypatch.setattr(
        bridge,
        "_schedule_legacy_diff",
        lambda *a, **k: None,
    )
    v = run_new_engine_chat(["gelatin"], restriction_ids=["vegan"], use_api_fallback=False)
    assert v is fake or v.status == VerdictStatus.NOT_SAFE
```

Extract `_run_ike2_compliance` and `_schedule_legacy_diff` as thin helpers so tests can monkeypatch without over-mocking.

- [ ] **Step 2: Red**

- [ ] **Step 3: Implement IKE-2-first `run_new_engine_chat`**

Outline:

```python
def _run_ike2_compliance(ingredients, rids, prepared_decomposed, region=None):
    # same pipeline as former ike2_external_verdict but return (ComplianceResult, inputs)
    ...

def run_new_engine_chat(...):
    rids = ...
    try:
        result, inputs = _run_ike2_compliance(...)
        verdict = map_ike2_to_compliance_verdict(result, inputs)
    except Exception:
        logger.exception("IKE-2 primary failed input_hash=%s ...", _input_hash(...))
        verdict = ComplianceVerdict(status=VerdictStatus.UNCERTAIN)
    _schedule_legacy_diff(ingredients, rids, verdict.status.value, prepared_decomposed)
    return verdict
```

- [ ] **Step 4: Green**

- [ ] **Step 5: Commit**

```bash
git commit -m "ike2: chat uses ike2 only"
```

---

### Task 5: Background legacy diff + timeout (non-blocking)

**Files:**
- Modify: `backend/core/bridge.py`
- Test: `backend/tests/test_ike2_primary_cutover.py`

**Interfaces:**
- `_schedule_legacy_diff(...)` submits work to module-level `ThreadPoolExecutor(max_workers=2)` (or similar).
- Worker runs legacy `ComplianceEngine.evaluate` (with `use_api_fallback=False` to keep diff cheap/deterministic — **document this choice**; if product needs API on legacy shadow, set True — default **False** for latency/cost), then `compare` + DB/log writer.
- Timeout: e.g. `LEGACY_DIFF_TIMEOUT_SEC = 5` constant (or env later — YAGNI constant first). Use `Future.result(timeout=...)` **only inside the worker supervisor thread**, not on the request thread. Request thread: `executor.submit(...)` and return immediately.
- On timeout: cancel if possible / log warning; never raise to chat.

- [ ] **Step 1: Failing non-blocking test**

```python
import time
from core.bridge import run_new_engine_chat
from core.models.verdict import VerdictStatus


def test_legacy_diff_does_not_block_response(monkeypatch):
    import core.bridge as bridge

    def slow_legacy(*args, **kwargs):
        time.sleep(2.0)
        return None

    monkeypatch.setattr(bridge, "_run_legacy_diff_job", slow_legacy)
    # Ensure IKE-2 path is fast
    t0 = time.perf_counter()
    v = run_new_engine_chat(["water"], restriction_ids=["vegan"], use_api_fallback=False)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.5  # must not wait for 2s legacy
    assert v.status in (VerdictStatus.SAFE, VerdictStatus.UNCERTAIN, VerdictStatus.NOT_SAFE)
```

- [ ] **Step 2: Red** (will fail if legacy still sync)

- [ ] **Step 3: Implement `_schedule_legacy_diff` fire-and-forget**

- [ ] **Step 4: Green** (may need short sleep after assert to avoid teardown races — prefer joining executor only in tests via monkeypatch of submit)

- [ ] **Step 5: Commit**

```bash
git commit -m "ike2: legacy diff runs in background"
```

---

### Task 6: Disagreement case (c) + wire integration

**Files:**
- Test: `backend/tests/test_ike2_primary_cutover.py`
- Possibly small hooks on `_run_legacy_diff_job` to capture compare payload

- [ ] **Step 1: Test (c)**

```python
def test_response_is_ike2_when_disagrees_with_legacy(monkeypatch):
    import core.bridge as bridge
    from core.models.verdict import ComplianceVerdict, VerdictStatus

    monkeypatch.setattr(
        bridge,
        "_run_ike2_compliance",
        lambda *a, **k: (
            # return objects that map to NOT_SAFE — or patch map directly
            None
        ),
    )
```

Prefer clearer version:

```python
def test_response_is_ike2_when_disagrees_with_legacy(monkeypatch):
    import core.bridge as bridge
    from core.models.verdict import ComplianceVerdict, VerdictStatus

    ike2_v = ComplianceVerdict(status=VerdictStatus.NOT_SAFE, triggered_ingredients=["gelatin"])
    captured = {}

    monkeypatch.setattr(bridge, "map_ike2_to_compliance_verdict", lambda *a, **k: ike2_v)
    monkeypatch.setattr(
        bridge,
        "_run_ike2_compliance",
        lambda *a, **k: ("result", "inputs"),
    )

    def capture_schedule(ingredients, rids, primary_status, prepared):
        captured["primary_status"] = primary_status

    monkeypatch.setattr(bridge, "_schedule_legacy_diff", capture_schedule)

    out = run_new_engine_chat(["gelatin"], restriction_ids=["vegan"], use_api_fallback=False)
    assert out.status == VerdictStatus.NOT_SAFE
    assert captured["primary_status"] == "NOT_SAFE"
```

- [ ] **Step 2–4:** Red → implement if gaps → Green

- [ ] **Step 5: Commit**

```bash
git commit -m "test: ike2 wins when engines disagree"
```

---

### Task 7: Sweep remaining `IKE2_MODE` off/shadow/fallback references

**Files:** grep hits under `backend/` (code + tests + scripts). **Skip** root README docs per spec.

- [ ] **Step 1:** Run `rg 'IKE2_MODE|"shadow"|run_shadow' backend --glob '!venv'` and fix code/tests/scripts needed for green CI.
- [ ] **Step 2:** Update `ike2_shadow_soak_report.py` docstring to say primary + legacy diff (no mode=shadow).
- [ ] **Step 3:** Run focused suites:

```bash
cd backend && ./venv/bin/python -m pytest \
  tests/test_ike2_primary_cutover.py \
  tests/ike2/test_shadow_runner.py \
  tests/test_chat_ingredients.py \
  tests/ike2/test_pipeline_e2e.py \
  -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: drop old ike2 mode checks"
```

---

### Task 8: Verification + review gate

- [ ] **Step 1:** Full IKE-2 related pytest as above + `tests/ike2/ -q` if time.
- [ ] **Step 2:** Manual smoke: `IKE2_MODE=shadow` in env → import config → `IKE2_MODE == "primary"`; chat path returns IKE-2 mapped verdict.
- [ ] **Step 3:** Request code review (requesting-code-review skill) on diff vs `origin/feat/ike2-engine` before this work… or vs task-1 parent.
- [ ] **Step 4:** Apply feedback per receiving-code-review (verify, no performative agreement).
- [ ] **Step 5:** Push in small commits (already committed per task).

---

## Spec coverage checklist

| Spec item | Task |
|-----------|------|
| Silent coerce primary | Task 1 |
| Mapper + to_external inheritance | Task 2 |
| Partial resolution note/test | Task 2 |
| Bridge IKE-2 first / no legacy return | Task 4 |
| IKE-2 error → UNCERTAIN | Task 4 |
| Background legacy + timeout | Task 5 |
| Diff rename / false_safe meaning | Task 3 |
| Tests a,b,c,c2,d | Tasks 1–6 |
| Docs flag only | (no task — do not edit) |
| No .env commit | (constraint) |
| No response.assemble | (constraint) |

## Placeholder / consistency self-review

- No TBD left in tasks.
- `run_legacy_diff` vs `_run_legacy_diff_job` / `_schedule_legacy_diff` naming is fixed in Task 3–5; implementers must use these names.
- Comparator arg order: legacy first, primary second — unchanged from today (`compare(legacy, ike2, raw)`).
