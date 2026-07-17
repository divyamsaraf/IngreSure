# IKE-2 Resolution & Compliance Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix root-cause bugs so audit cards map FAIL→Avoid / WARN|UNCERTAIN→Depends / SAFE→Safe, resolve known ingredients without Supabase, reject non-food intent, and emit correct `reason_category` copy — verified by a golden matrix including Supabase-down.

**Architecture:** Keep IKE-2 as the sole verdict authority. Extend `resolver` with ResolutionCache + Tier-2 file ontology before Supabase. Fix `compliance.evaluate` breakdown to keep worst verdict and FAIL-only Avoid sourcing. Fix `map_ike2_to_compliance_verdict` + `response_composer` for buckets/copy. Gate intent before bare-ingredient fallback. TDD: golden matrix and unit tests fail first, then minimal production changes.

**Tech Stack:** Python 3 / pytest, existing `backend/core/knowledge/ike2/*`, `bridge.py`, `intent_detector.py`, `response_composer.py`, `data/ontology.json`

**Spec:** `docs/superpowers/specs/2026-07-17-ike2-resolution-compliance-fix-design.md` (approved)

## Global Constraints

- Policy A: Depends = genuine ambiguity only; non-food never enters audit.
- Plain Sugar → Safe on all diets including Vegan; never invent bone-char.
- Certainty: unresolved → Depends/`unknown_ingredient`, never forced Safe or Avoid.
- Mapper: FAIL→Avoid, WARN|UNCERTAIN→Depends, SAFE→Safe; species-unknown alone ≠ Avoid.
- Breakdown: `max` verdict per `(name, restriction)`, not last-write.
- WARN compounds (`verdict_cap=WARN`) always Depends in cards.
- ResolutionCache: boot-seed Tier 1; lazy Tier 2 write-through; Tier 3 only on miss.
- Supabase errors: silent miss; never `diet_conflict` / “may conflict with your dietary requirements”.
- Tests assert **bucket + `reason_category`** (bucket-only fails the spec).
- TDD: no production code without a failing test first.
- No frontend required for `reason_category` (backend emits; UI may ignore).
- Do not commit unless the user asks (follow repo commit rules).

## File structure (locked)

| Path | Responsibility |
|------|----------------|
| `backend/tests/ike2/golden/audit_matrix.jsonl` | Golden rows: diet, allergens, input, expect_bucket, expect_reason_category, expect_attribution |
| `backend/tests/ike2/test_audit_matrix.py` | Parametrized matrix runner (+ Supabase-down param) |
| `backend/tests/ike2/test_audit_mapping_contract.py` | Mapper FAIL/WARN/UNCERTAIN/SAFE unit cases |
| `backend/tests/ike2/test_breakdown_worst.py` | Breakdown keeps worst verdict |
| `backend/tests/ike2/test_intent_plausibility.py` | Intent gate garbage vs food |
| `backend/tests/ike2/test_resolution_tiers.py` | Cache seed, Tier2, Supabase-down |
| `backend/tests/test_verdict_explanation_attribution.py` (or extend existing) | Diet vs allergen copy |
| `backend/core/knowledge/ike2/resolution_cache.py` | In-process cache + boot seed API |
| `backend/core/knowledge/ike2/stores/local_ontology.py` | Tier-2 file lookup |
| `backend/core/knowledge/ike2/resolver.py` | Tier order + silent Tier-3 degrade |
| `backend/core/knowledge/ike2/truth_anchor.py` | Expand Tier-1 curated core |
| `backend/core/knowledge/ike2/compliance.py` | Worst breakdown; FAIL-only matched_contains (or equiv.) |
| `backend/core/bridge.py` | Map from per-ingredient verdict / breakdown |
| `backend/core/response_composer.py` | `reason_category`, attribution, no blanket diet-conflict Depends |
| `backend/core/intent_detector.py` | Plausibility gate |
| `backend/core/models/verdict.py` | Optional fields only if needed for category plumbing |

---

### Task 1: Golden matrix fixture + failing runner

**Files:**
- Create: `backend/tests/ike2/golden/audit_matrix.jsonl`
- Create: `backend/tests/ike2/test_audit_matrix.py`
- Create (helper): `backend/tests/ike2/audit_matrix_helpers.py`

**Interfaces:**
- Consumes: `run_new_engine_chat`, `profile_to_restriction_ids`, `build_ingredient_audit_payload`, `compose_verdict_explanation`, `detect_intent`
- Produces: stable helper `run_audit_case(diet, ingredients, allergens=None) -> dict` with keys `bucket_by_name`, `reason_category_by_name`, `explanation`, `triggered_restrictions`, `intent` (for garbage rows)

- [ ] **Step 1: Write `audit_matrix.jsonl` with at least one row per cluster** from spec §10.3 (sugar×Vegan, natural flavors×Vegan, `2+2`, flour×Vegetarian, chicken×Vegan, egg×Hindu Non Vegetarian, collagen×Halal, gelatin×Hindu Vegetarian+Fish, beef×Hindu Non Vegetarian, potato×Jain, chicken×Pescatarian, reserved unknown token `zzzx_unknown_fixture_ingredient`).

Example row shape:

```json
{"cluster":"egg_hnv","diet":"Hindu Non Vegetarian","allergens":[],"input":"egg","expect_bucket":"safe","expect_reason_category":null,"expect_attribution":null}
{"cluster":"gelatin_diet_vs_allergen","diet":"Hindu Vegetarian","allergens":["Fish"],"input":"gelatin","expect_bucket":"avoid","expect_reason_category":"diet_conflict","expect_attribution":"diet"}
{"cluster":"intent_garbage","diet":"Vegan","allergens":[],"input":"2+2","expect_bucket":"no_audit","expect_reason_category":null,"expect_attribution":null}
```

- [ ] **Step 2: Write failing parametrized test**

```python
# backend/tests/ike2/test_audit_matrix.py
import json
from pathlib import Path
import pytest
from core.intent_detector import detect_intent
from tests.ike2.audit_matrix_helpers import run_audit_case

ROWS = [
    json.loads(line)
    for line in Path(__file__).with_name("golden").joinpath("audit_matrix.jsonl").read_text().splitlines()
    if line.strip() and not line.strip().startswith("#")
]

@pytest.mark.parametrize("row", ROWS, ids=lambda r: f"{r['cluster']}:{r['diet']}:{r['input']}")
def test_audit_matrix_row(row):
    if row["expect_bucket"] == "no_audit":
        pi = detect_intent(row["input"])
        assert pi.intent in ("GREETING", "GENERAL_QUESTION")
        assert not pi.ingredients
        return
    result = run_audit_case(row["diet"], [row["input"]], row.get("allergens") or [])
    name = row["input"].lower()
    # find bucket for ingredient (case-insensitive)
    bucket = result["bucket_by_name"].get(name) or next(
        (b for k, b in result["bucket_by_name"].items() if name in k or k in name), None
    )
    assert bucket == row["expect_bucket"], result
    cat = result["reason_category_by_name"].get(name) or result["reason_category_by_name"].get(
        next((k for k in result["reason_category_by_name"] if name in k or k in name), ""), None
    )
    assert cat == row["expect_reason_category"]
    if row.get("expect_attribution") == "diet":
        assert "allergen" not in (result["explanation"] or "").lower()
    blanket = "may conflict with your dietary requirements"
    if row["expect_reason_category"] != "diet_conflict":
        reasons = " ".join(str(x) for x in result["reason_category_by_name"].values())
        assert blanket not in (result.get("reasons_text") or "")
```

Implement `run_audit_case` to call bridge + `build_ingredient_audit_payload` and collect `reason` strings into `reasons_text`. Until `reason_category` exists on items, helper may read `item.get("reason_category")` (None) so tests fail for category assertions.

- [ ] **Step 3: Run tests — expect FAIL**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/ike2/test_audit_matrix.py -q --tb=line
```

Expected: failures on egg_hnv (avoid≠safe), sugar (depends≠safe), compounds (safe≠depends), intent garbage (INGREDIENT_QUERY), missing `reason_category`, etc.

- [ ] **Step 4: Do not fix production yet** — proceed to Task 2 (mapper) which unblocks several rows; keep matrix red until later tasks green it.

---

### Task 2: Breakdown worst-verdict + FAIL-only Avoid sourcing

**Files:**
- Modify: `backend/core/knowledge/ike2/compliance.py`
- Create: `backend/tests/ike2/test_breakdown_worst.py`
- Modify: `backend/core/bridge.py` (`map_ike2_to_compliance_verdict`)
- Create: `backend/tests/ike2/test_audit_mapping_contract.py`

**Interfaces:**
- Consumes: `Verdict` IntEnum, `evaluate(...)`
- Produces: `breakdown[(name, restriction)] = max(old, new)`; Avoid list = names with any FAIL in breakdown; Depends = WARN/UNCERTAIN or unresolved inputs

- [ ] **Step 1: Write failing breakdown test**

```python
# backend/tests/ike2/test_breakdown_worst.py
from types import SimpleNamespace
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.verdict import Verdict
from core.knowledge.ike2 import rules

def _inp(name, **flags):
    return SimpleNamespace(
        canonical_name=name, flags=flags, knowledge_state="LOCKED",
        trusted=True, alcohol_role=None, verdict_cap=flags.get("verdict_cap"),
        trace=False, may_contain=False,
    )

def test_hindu_veg_gelatin_breakdown_keeps_fail_not_last_safe():
    gel = _inp("gelatin", animal_origin=True, fish_source=True,
               animal_species="bovine/porcine/fish depending on source",
               uncertainty_flags=["source_species_unspecified_on_label"],
               verdict_cap="WARN")
    profile = SimpleNamespace(restrictions={"hindu_vegetarian": "medical"})
    result = evaluate([gel], profile, rules.seeded_rules())
    assert result.breakdown[("gelatin", "hindu_vegetarian")] == Verdict.FAIL
```

- [ ] **Step 2: Write failing mapper contract tests**

```python
# backend/tests/ike2/test_audit_mapping_contract.py
from types import SimpleNamespace
from core.bridge import map_ike2_to_compliance_verdict, run_new_engine_chat
from core.knowledge.ike2.verdict import Verdict
from core.models.verdict import VerdictStatus

def test_egg_hindu_non_veg_not_in_triggered():
    v = run_new_engine_chat(["egg"], restriction_ids=["hindu_non_vegetarian"])
    assert "egg" not in (v.triggered_ingredients or [])
    assert v.status != VerdictStatus.NOT_SAFE or not v.triggered_ingredients

def test_warn_compound_goes_to_uncertain_not_safe_path():
    v = run_new_engine_chat(["natural flavors"], restriction_ids=["vegan"])
    assert "natural flavors" in (v.uncertain_ingredients or [])
    assert "natural flavors" not in (v.triggered_ingredients or [])
```

- [ ] **Step 3: Run — expect FAIL**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/ike2/test_breakdown_worst.py tests/ike2/test_audit_mapping_contract.py -q --tb=short
```

- [ ] **Step 4: Implement minimal compliance fix**

In `evaluate`, replace last-write with:

```python
key = (name, rule.restriction)
prev = breakdown.get(key)
breakdown[key] = verdict if prev is None else max(prev, verdict)
```

Only append to `matched_contains` when `verdict == Verdict.FAIL` (and triggered), not on UNCERTAIN caution.

- [ ] **Step 5: Implement mapper** so Avoid = names with any breakdown FAIL; Depends = names with worst in (WARN, UNCERTAIN) **or** unresolved/untrusted inputs **or** `verdict_cap==WARN` / per-ingredient WARN; never put WARN-only into `triggered_ingredients`.

- [ ] **Step 6: Re-run Task 2 tests — expect PASS**. Re-run matrix — expect partial green (egg_hnv, compounds, breakdown) but sugar/chicken still fail until Tier-1.

---

### Task 3: Tier-1 curated core expansion

**Files:**
- Modify: `backend/core/knowledge/ike2/truth_anchor.py`
- Modify: `backend/tests/ike2/test_truth_anchor.py` (extend)

**Interfaces:**
- Consumes: existing `_add` / `_add_compound`
- Produces: lookups for sugar, cane sugar, beet sugar, flour, chicken, potato, fish (generic), collagen, rennet (collagen/rennet already may exist — verify), etc. per spec §9.2

- [ ] **Step 1: Write failing lookup tests**

```python
from core.knowledge.ike2 import truth_anchor

@pytest.mark.parametrize("key", ["sugar", "cane sugar", "beet sugar", "flour", "chicken", "potato"])
def test_tier1_core_present(key):
    assert truth_anchor.lookup(key) is not None

def test_sugar_plant_safe_flags():
    f = truth_anchor.lookup("sugar")
    assert f.flags.get("animal_origin") is False
    assert f.flags.get("plant_origin") is True
    assert "bone_char" not in str(f.flags.get("uncertainty_flags") or [])

def test_chicken_has_species():
    f = truth_anchor.lookup("chicken")
    assert f.flags.get("animal_origin") is True
    assert f.flags.get("animal_species") == "chicken"
```

- [ ] **Step 2: Run — expect FAIL** for missing keys.

- [ ] **Step 3: Add Tier-1 anchors** (minimal flags only):

```python
_add(["sugar"], "sugar", _f(animal_origin=False, plant_origin=True))
_add(["cane sugar"], "cane sugar", _f(animal_origin=False, plant_origin=True))
_add(["beet sugar"], "beet sugar", _f(animal_origin=False, plant_origin=True))
_add(["flour", "wheat flour", "all purpose flour"], "flour", _f(gluten_source=True))  # or map wheat flour→wheat already; ensure "flour" resolves
_add(["chicken"], "chicken", _f(animal_origin=True, animal_species="chicken"))
_add(["potato"], "potato", _f(root_vegetable=True, plant_origin=True))
# fish generic if missing:
_add(["fish"], "fish", _f(animal_origin=True, animal_species="fish", fish_source=True))
```

Ensure collagen/rennet exist with `animal_origin=True` and **no** `animal_species` (species-unknown Depends path).

- [ ] **Step 4: Run truth_anchor + mapping tests — expect PASS** for sugar/chicken rows when Supabase down locally.

---

### Task 4: ResolutionCache + Tier-2 local ontology + silent Tier-3

**Files:**
- Create: `backend/core/knowledge/ike2/resolution_cache.py`
- Create: `backend/core/knowledge/ike2/stores/local_ontology.py`
- Modify: `backend/core/knowledge/ike2/resolver.py`
- Create: `backend/tests/ike2/test_resolution_tiers.py`

**Interfaces:**
- Produces:
  - `resolution_cache.get(key) -> ResolvedIngredient | None`
  - `resolution_cache.put(key, ResolvedIngredient) -> None`
  - `resolution_cache.seed_tier1() -> None` (call at module import or first `resolve`)
  - `local_ontology.lookup(normalized_alias) -> TruthAnchorFact-like | Group-like | None`
  - `resolve(atom, region)` order: cache → Tier1 → Tier2 (cache put) → Tier3 try/except miss → uncertain

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/ike2/test_resolution_tiers.py
from unittest.mock import patch
from core.knowledge.ike2 import resolver

def test_sugar_resolves_when_db_raises():
    with patch("core.knowledge.ike2.stores.db.resolve_alias", side_effect=RuntimeError("down")):
        with patch("core.knowledge.ike2.stores.db.disambiguate", side_effect=RuntimeError("down")):
            r = resolver.resolve("sugar", None)
    assert r.status == "resolved"
    assert r.trusted is True

def test_unknown_when_all_tiers_miss_no_raise():
    with patch("core.knowledge.ike2.stores.db.resolve_alias", side_effect=RuntimeError("down")):
        with patch("core.knowledge.ike2.stores.db.disambiguate", side_effect=RuntimeError("down")):
            r = resolver.resolve("zzzx_unknown_fixture_ingredient", None)
    assert r.status == "uncertain"
    assert r.trusted is False
```

- [ ] **Step 2: Run — FAIL** if sugar still hits except→uncertain without Tier1 (after Task 3 sugar is in Tier1 — this should already pass for sugar; keep test for unknown + ensure DB exception after Tier1/2 miss does not raise).

- [ ] **Step 3: Implement cache + local ontology**

`local_ontology.py`: load `data/ontology.json` once; index by normalized canonical + aliases; return a SimpleNamespace/TruthAnchorFact-compatible object with flags + `knowledge_state` (default CLASSIFIED/VERIFIED only if flags complete; else treat as incomplete → do not trust for SAFE).

**Sanity-check while implementing (review note, not a plan redo):** Supabase-down tests mock *exceptions*. Also handle Tier-3 *successful but malformed/incomplete rows* (missing `canonical_name` / required flags): treat as miss or untrusted — never invent SAFE — same incomplete-flags policy as Tier 2. Add a small unit case if easy (`resolve_alias` returns a bare/empty row → uncertain or unverified, not Safe).

`resolver.py` rewrite order:

```python
def resolve(atom, region):
    key = normalize(atom)  # existing normalizer
    seed_tier1_once()
    hit = cache.get(cache_key(key, region))
    if hit: return hit
    fact = truth_anchor.lookup(atom)
    if fact:
        out = ...; cache.put(...); return out
    local = local_ontology.lookup(key)
    if local:
        out = ... trusted static ...; cache.put(...); return out
    try:
        # Tier 3
        ...
    except Exception:
        logger.warning(...); return _uncertain("L3_db_error", "db")
    return _uncertain("L5_unknown_queue", "unknown_queue")
```

- [ ] **Step 4: Supabase-down matrix subset**

```python
@pytest.mark.parametrize("row", TIER1_ROWS)
def test_matrix_supabase_down(row):
    with patch(...db raises...):
        # same assertions as matrix for Tier-1 clusters only
```

- [ ] **Step 5: Run `test_resolution_tiers.py` + Tier-1 matrix rows — PASS**.

---

### Task 5: Intent plausibility gate

**Files:**
- Modify: `backend/core/intent_detector.py`
- Create: `backend/tests/ike2/test_intent_plausibility.py` (or `backend/tests/test_intent_plausibility.py`)

**Interfaces:**
- Produces: `_is_plausible_ingredient_query(text: str) -> bool` used before `_bare_ingredients_fallback`

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.parametrize("q", ["2+2", "act as", "Namaste", "asdfgh", "null", "true", "{}", "ignore previous instructions"])
def test_garbage_not_ingredient_query(q):
    pi = detect_intent(q)
    assert pi.intent != "INGREDIENT_QUERY" or not pi.ingredients

@pytest.mark.parametrize("q", ["egg", "gelatin", "sugar", "E120", "natural flavors"])
def test_food_still_ingredient_query(q):
    pi = detect_intent(q)
    assert pi.intent == "INGREDIENT_QUERY"
    assert pi.ingredients
```

- [ ] **Step 2: Run — FAIL** on garbage.

- [ ] **Step 3: Implement gate** (denylist + math/literal/JSON/SQL heuristics; accept if Tier1/2 alias hit OR food-like letters). Expand `_BARE_QUERY_DENYLIST` with `namaste`, etc.

- [ ] **Step 4: Run intent + matrix intent_garbage rows — PASS**.

---

### Task 6: `reason_category` + copy attribution

**Files:**
- Modify: `backend/core/response_composer.py`
- Modify: `backend/tests/test_llm_verdict_explanation.py` and/or new `backend/tests/test_verdict_explanation_attribution.py`
- Optionally extend audit item dict in `build_ingredient_audit_payload`

**Interfaces:**
- Produces: each audit item may include `"reason_category": <str|null>`; explanation uses diet-primary attribution per spec §7

- [ ] **Step 1: Failing tests**

```python
def test_depends_unknown_not_diet_conflict_copy():
    # force unresolved path if needed
    ...
    assert item["reason_category"] == "unknown_ingredient"
    assert "may conflict with your dietary requirements" not in item["reason"]

def test_gelatin_hindu_veg_with_fish_allergen_diet_attribution():
    # run engine + compose_verdict_explanation
    assert "allergen" not in explanation.lower()
    assert "hindu vegetarian" in explanation.lower() or "diet" in explanation.lower()

def test_compound_category():
    audit = ...
    assert item["reason_category"] == "compound_umbrella"
```

- [ ] **Step 2: Implement**

Replace default `_ingredient_reason` blanket for Depends paths with category-specific strings. Add helper:

```python
def _reason_category_for_item(status, *, verdict_cap=None, unresolved=False, source_ambiguous=False, allergy=False) -> str | None:
    ...
```

Wire into `build_ingredient_audit_payload` for avoid/depends items. Fix `compose_verdict_explanation` attribution priority (spec §7.2). Pass attribution hint into LLM composer if present; fall back to template on contradiction.

- [ ] **Step 3: Run explanation + full matrix — expect green** for category assertions.

- [ ] **Step 4: Forbidden phrase guard**

```python
def test_no_blanket_phrase_on_safe_or_unknown():
    ...
```

---

### Task 7: Full matrix green + Supabase-down suite + regression sweep

**Files:**
- Extend: `backend/tests/ike2/golden/audit_matrix.jsonl` to full diet×cluster coverage from spec §10.2–10.3
- Modify: `backend/tests/ike2/test_audit_matrix.py` (add `supabase_down` param)

- [ ] **Step 1: Expand JSONL** so each cluster covers required diets (not only one row).

- [ ] **Step 2: Add**

```python
@pytest.mark.parametrize("supabase_down", [False, True])
@pytest.mark.parametrize("row", TIER1_ELIGIBLE_ROWS, ...)
def test_audit_matrix_tier1_parity(row, supabase_down):
    ...
```

- [ ] **Step 3: Run full suite**

```bash
cd backend && source venv/bin/activate && python -m pytest \
  tests/ike2/test_audit_matrix.py \
  tests/ike2/test_audit_mapping_contract.py \
  tests/ike2/test_breakdown_worst.py \
  tests/ike2/test_resolution_tiers.py \
  tests/ike2/test_intent_plausibility.py \
  tests/ike2/test_truth_anchor.py \
  tests/test_verdict_explanation_attribution.py \
  -q --tb=line
```

Expected: all PASS.

- [ ] **Step 4: Manual smoke** (optional): hit chat with Sugar/Gelatin list on Vegetarian and egg on Hindu Non-Veg; confirm cards.

- [ ] **Step 5: Stop** — present summary to user; commit only if requested.

---

## Self-review vs spec

| Spec requirement | Task |
|------------------|------|
| Mapper FAIL/WARN/UNCERTAIN/SAFE | Task 2 |
| Breakdown worst verdict | Task 2 |
| WARN compounds Depends | Task 2 (+ Tier1 compounds already) |
| Intent gate | Task 5 |
| Allergen/diet attribution | Task 6 |
| reason_category + no blanket Depends copy | Task 6 |
| Tier1 core + Sugar Safe | Task 3 |
| Cache boot Tier1 + lazy Tier2 | Task 4 |
| Silent Supabase degrade | Task 4 |
| Golden matrix + reason_category | Tasks 1, 7 |
| Supabase-down suite | Tasks 4, 7 |
| Certainty / unknown | Tasks 4, 6 |

No TBD placeholders. Types align: audit items gain optional `reason_category`; resolver remains `resolve(atom, region) -> ResolvedIngredient`.

---

## Execution handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-17-ike2-resolution-compliance-fix.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with executing-plans checkpoints  

**Which approach?** (Still no production code until you pick one and say to implement.)
