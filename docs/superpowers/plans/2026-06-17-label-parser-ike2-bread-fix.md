# Label Parser + IKE-2 Bread Label Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix FDA-style bread label parsing (square brackets, trace clauses) and IKE-2 L1 aliases so gluten-free shadow matches legacy NOT_SAFE and vegan is not spuriously UNCERTAIN.

**Architecture:** Extend shared nesting split in `ingredient_parser.py` + `parser.py` (DRY via one helper), align `input_layer.parse_atoms` with bridge `preprocess_ingredient_list` decomposition, add truth-anchor aliases for flour/gluten staples.

**Tech Stack:** Python 3, pytest, existing IKE-2 pipeline (`input_layer` → `resolver` → `compliance`).

**Spec:** `docs/superpowers/specs/2026-06-17-label-parser-ike2-bread-fix-design.md`

## Global Constraints

- Zero false-Safe regressions (IKE-2 invariant).
- Surgical changes only — no ontology DB seed, no IKE2_MODE=primary wiring.
- TDD: failing test before each production change.
- Match existing code style in `ingredient_parser.py` / `truth_anchor.py`.

---

### Task 1: Shared nesting split helper (square brackets)

**Files:**
- Create: `backend/core/parsing/nesting_split.py`
- Modify: `backend/core/parsing/ingredient_parser.py` (import helper, remove duplicate `_split_by_parentheses`)
- Modify: `backend/core/normalization/parser.py` (import helper, remove duplicate `_split_by_parentheses`)
- Test: `backend/tests/test_parser_and_profile.py`

**Interfaces:**
- Produces: `split_by_nesting(text: str) -> list[str]` — treats `()`, `[]` as nesting delimiters; commas inside delimiters become separate items.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_parser_and_profile.py`:

```python
BREAD_LABEL = (
    "Ingredients: Enriched Wheat Flour [Flour, Malted Barley Flour, Reduced Iron, Niacin, "
    "Thiamin Mononitrate (Vitamin B1), Riboflavin (Vitamin B2), Folic Acid], Water, "
    "Sourdough (Wheat Flour), Wheat Gluten, Yeast. Contains 2% Or Less Of Each Of The Following: "
    "Extra Virgin Olive Oil, Sea Salt, Preservatives (Calcium Propionate, Sorbic Acid), "
    "Organic Grain Vinegar, Enzymes."
)


def test_flatten_ingredients_bread_label_brackets():
    from core.normalization.parser import flatten_ingredients
    out = flatten_ingredients(BREAD_LABEL)
    assert not any("[" in x or "]" in x for x in out)
    assert "wheat gluten" in out
    assert "malted barley flour" in out or "barley" in out
    assert "enzymes" in out
    assert "yeast" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_parser_and_profile.py::test_flatten_ingredients_bread_label_brackets -v`  
Expected: FAIL (bracket artifacts or missing atoms)

- [ ] **Step 3: Implement `split_by_nesting`**

Create `backend/core/parsing/nesting_split.py`:

```python
import re

_OPEN = {"(": ")", "[": "]"}
_CLOSE = {")": "(", "]": "["}


def split_by_nesting(text: str) -> list[str]:
    """Split by top-level () and [] nesting; flatten inner commas."""
    if not text or not text.strip():
        return []
    out: list[str] = []
    depth = 0
    opener = ""
    start = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in _OPEN:
            if depth == 0 and i > start:
                chunk = text[start:i].strip()
                if chunk:
                    out.append(chunk)
            if depth == 0:
                opener = ch
            depth += 1
            if depth == 1:
                start = i + 1
            i += 1
        elif ch in _CLOSE and depth > 0 and _CLOSE[ch] == opener:
            depth -= 1
            if depth == 0:
                inner = text[start:i].strip()
                if inner:
                    for part in re.split(r"\s*,\s*", inner):
                        part = part.strip()
                        if part:
                            out.extend(split_by_nesting(part))
                start = i + 1
            i += 1
        else:
            i += 1
    if depth == 0 and start < len(text):
        chunk = text[start:].strip()
        if chunk:
            out.append(chunk)
    return out
```

Wire into both parsers (replace local `_split_by_parentheses` with `split_by_nesting`).

- [ ] **Step 4: Run test — still expected FAIL** until Task 2 prefix/trace fixes.

- [ ] **Step 5: Commit** (only if user requests commit)

---

### Task 2: Label prefix + period/trace segment split

**Files:**
- Modify: `backend/core/parsing/ingredient_parser.py`
- Modify: `backend/core/normalization/parser.py`
- Test: `backend/tests/test_parser_and_profile.py`

**Interfaces:**
- Consumes: `split_by_nesting` from Task 1
- Produces: `_strip_label_prefix(raw) -> str`; segment split before nesting on `.` + trace introducer

- [ ] **Step 1: Write failing tests**

```python
def test_preprocess_ingredients_strips_label_prefix():
    from core.parsing.ingredient_parser import preprocess_ingredients
    items = preprocess_ingredients("Ingredients: water, salt")
    names = [x["name"] for x in items]
    assert "water" in names
    assert not any(n.startswith("ingredients") for n in names)


def test_preprocess_ingredients_trace_after_period():
    from core.parsing.ingredient_parser import preprocess_ingredients
    raw = "Yeast. Contains 2% Or Less Of Each Of The Following: Sea Salt, Enzymes"
    items = preprocess_ingredients(raw)
    by_name = {x["name"]: x["trace"] for x in items}
    assert by_name.get("yeast") is False
    assert by_name.get("sea salt") is True
    assert by_name.get("enzymes") is True
```

- [ ] **Step 2: Run tests — verify FAIL**

Run: `cd backend && python3 -m pytest tests/test_parser_and_profile.py::test_preprocess_ingredients_strips_label_prefix tests/test_parser_and_profile.py::test_preprocess_ingredients_trace_after_period -v`

- [ ] **Step 3: Implement**

In `ingredient_parser.py` add:

```python
_LABEL_PREFIX = re.compile(r"^\s*ingredients\s*:\s*", re.IGNORECASE)
_TRACE_SENTENCE = re.compile(
    r"\.\s+(?=contains\s+2%|<\s*2%|less than\s+2%)",
    re.IGNORECASE,
)

def _strip_label_prefix(text: str) -> str:
    return _LABEL_PREFIX.sub("", text).strip()
```

At start of `preprocess_ingredients`: `raw_str = _strip_label_prefix(raw_str)`  
Before comma split: `segments = re.split(_TRACE_SENTENCE, raw_str)` then comma-split each segment.

In `flatten_ingredients`: same prefix strip + sentence split; update comma regex to:

```python
segments = re.split(r",(?![^(\[]*[\)\]])", raw_str)
```

- [ ] **Step 4: Run all parser tests**

Run: `cd backend && python3 -m pytest tests/test_parser_and_profile.py -v`  
Expected: all PASS including `test_flatten_ingredients_bread_label_brackets`

- [ ] **Step 5: Commit** (if user requests)

---

### Task 3: Align IKE-2 `input_layer` with bridge decomposition

**Files:**
- Modify: `backend/core/knowledge/ike2/input_layer.py`
- Test: `backend/tests/ike2/test_input_layer.py`

**Interfaces:**
- Consumes: `preprocess_ingredients`, `flatten_ingredients`
- Produces: `parse_atoms(raw) -> list[ParsedAtom]` with same atoms as bridge for a full label paste

- [ ] **Step 1: Write failing test**

Add to `backend/tests/ike2/test_input_layer.py`:

```python
def test_parse_atoms_bread_label_matches_bridge_atoms():
    from core.bridge import preprocess_ingredient_list
    from core.knowledge.ike2.input_layer import parse_atoms
    from tests.test_parser_and_profile import BREAD_LABEL

    bridge_atoms, trace_keys, _ = preprocess_ingredient_list([BREAD_LABEL])
    ike2_atoms = [a.name for a in parse_atoms(BREAD_LABEL)]
    assert "wheat gluten" in ike2_atoms
    assert "enzymes" in ike2_atoms
    assert not any("[" in a for a in ike2_atoms)
    # Core gluten sources present
    assert any(x in ike2_atoms for x in ("wheat", "wheat flour", "barley", "malted barley flour"))
```

- [ ] **Step 2: Run test — verify FAIL**

Run: `cd backend && python3 -m pytest tests/ike2/test_input_layer.py::test_parse_atoms_bread_label_matches_bridge_atoms -v`

- [ ] **Step 3: Implement**

Replace comma-only loop in `parse_atoms` with:

```python
from core.parsing.ingredient_parser import preprocess_ingredients
from core.normalization.parser import flatten_ingredients

def parse_atoms(raw: str) -> list[ParsedAtom]:
    if not raw:
        return []
    by_name: dict[str, ParsedAtom] = {}
    for item in preprocess_ingredients(raw):
        for name in flatten_ingredients(item["name"]):
            if not name:
                continue
            is_trace = bool(item.get("trace"))
            existing = by_name.get(name)
            if existing is None:
                by_name[name] = ParsedAtom(name=name, trace=is_trace)
            elif is_trace and not existing.trace:
                by_name[name] = ParsedAtom(name=name, trace=True)
    return list(by_name.values())
```

Remove or keep `_atom_from_segment` only if still used elsewhere (delete if dead).

- [ ] **Step 4: Run IKE-2 input tests**

Run: `cd backend && python3 -m pytest tests/ike2/test_input_layer.py -v`  
Expected: PASS

- [ ] **Step 5: Commit** (if user requests)

---

### Task 4: L1 truth-anchor aliases (flour, water, yeast, enzymes)

**Files:**
- Modify: `backend/core/knowledge/ike2/truth_anchor.py`
- Test: `backend/tests/ike2/test_truth_anchor.py` (extend) + `backend/tests/ike2/test_bread_label.py` (new)

**Interfaces:**
- Produces: L1 lookups for `wheat flour`, `wheat gluten`, `malted barley flour`, `water`, `yeast`, `enzymes`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/ike2/test_bread_label.py`:

```python
from tests.ike2.golden_runner import run_case_full
from tests.test_parser_and_profile import BREAD_LABEL

def test_bread_label_gluten_free_not_safe():
    case = {
        "raw_input": BREAD_LABEL,
        "profile": {"restrictions": {"gluten_free": "medical"}},
        "region": None,
    }
    _, _, external, _ = run_case_full(case)
    assert external == "NOT_SAFE"


def test_bread_label_vegan_not_uncertain_from_staples():
    case = {
        "raw_input": BREAD_LABEL,
        "profile": {"restrictions": {"vegan": "lifestyle"}},
        "region": None,
    }
    _, result, external, _ = run_case_full(case)
    assert external != "UNCERTAIN", "water/yeast should resolve trusted"
```

Add to `test_truth_anchor.py`:

```python
def test_wheat_flour_gluten_anchor():
    from core.knowledge.ike2.truth_anchor import lookup
    fact = lookup("wheat flour")
    assert fact is not None
    assert fact.flags.get("gluten_source") is True
```

- [ ] **Step 2: Run tests — verify FAIL**

Run: `cd backend && python3 -m pytest tests/ike2/test_bread_label.py tests/ike2/test_truth_anchor.py::test_wheat_flour_gluten_anchor -v`

- [ ] **Step 3: Implement anchors**

In `truth_anchor.py` after gluten block:

```python
_add(["wheat flour", "enriched wheat flour", "bleached wheat flour"], "wheat",
     _f(gluten_source=True))
_add(["wheat gluten"], "gluten", _f(gluten_source=True))
_add(["malted barley flour"], "barley", _f(gluten_source=True))
_add(["water"], "water", _f())
_add(["yeast"], "yeast", _f(fungal=True))
_add_compound(["enzymes", "enzyme"], "enzymes")
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python3 -m pytest tests/ike2/test_bread_label.py tests/ike2/test_truth_anchor.py -v`  
Expected: PASS

- [ ] **Step 5: Commit** (if user requests)

---

### Task 5: Golden corpus row + full regression

**Files:**
- Modify: `backend/tests/ike2/golden/corpus.jsonl`
- Test: full IKE-2 suite

- [ ] **Step 1: Add corpus row** (only if `test_pipeline_external_matches_golden` should cover bread — optional separate test file may suffice)

If adding to corpus, use shortened input or full BREAD_LABEL with `expected_verdict: NOT_SAFE` for `gluten_free` only as separate case — **do not** add vegan row to corpus unless expected verdict is stable.

- [ ] **Step 2: Run full verification**

```bash
cd backend
python3 -m pytest tests/test_parser_and_profile.py tests/ike2/ -q
python3 scripts/verify_e_number_catalog.py --fail-on-error
```

Expected: 0 failures; golden safety budget unchanged.

- [ ] **Step 3: Manual shadow smoke** (with `IKE2_MODE=shadow`)

Paste bread label in UI with Gluten-free profile; confirm log:

`IKE2_SHADOW legacy=NOT_SAFE ike2=NOT_SAFE match=True`

- [ ] **Step 4: Request code review** — invoke `requesting-code-review` skill against spec success criteria.

---

## Execution Handoff

**Plan saved to:** `docs/superpowers/plans/2026-06-17-label-parser-ike2-bread-fix.md`

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — implement in this session via `executing-plans` with checkpoints

**Which approach should I use?**

After implementation, run **verification-before-completion** before claiming done.
