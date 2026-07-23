# Coverage OS Phase 2b — Induction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Phase 2b — offline induction that clusters unknown-log frequency + miss_class, proposes deterministic aliases/roles, submits only through a structural force-human wrapper, and measures precision A/A1/A2 against the ledger.

**Architecture:** One package `coverage_os/induction/` owns `cluster → propose → submit`. `assign_safety_class` is a thin composer over `deny_lists` + `hybrid_gate` predicates (same order as `decide_promote`). `submit` never passes `auto=True`. Precision queries read ledger rows that carry induction provenance + `safety_class`.

**Tech Stack:** Python 3.11, pytest, existing Coverage OS (`deny_lists`, `hybrid_gate`, `promote_writer`, `promote_ledger`, `profile_matrix`), `miss_class.classify_miss_class`, `UnknownIngredientsLog` / `data/unknown_ingredients_log.json`, Phase 2a neutralize roles.

**Spec:** `docs/superpowers/specs/2026-07-23-coverage-os-phase2b-induction-design.md`

## Global Constraints

- Induced path **must not** call `commit_promotion(..., auto=True)` even when `decide_promote` returns `auto_promote`.
- `decide_promote` predicates are **unchanged** — force-human is a wrapper in front.
- `safety_class` assignment imports and calls **only** `deny_lists.is_allergen_adjacent` / `is_animalish` and `hybrid_gate.has_dual_origin_collision` / `is_umbrella_term` (+ the same plant-closed condition as the gate). **No** local frozensets, **no** miss_class→safety_class maps, **no** parallel classifier.
- Alias target = deterministic **unique** closed-form resolve; else **no proposal**. No LLM. No co-occurrence.
- Role values = closed Phase 2a enum only: `plant_mod` | `dairy_head` | `process_keep` | `culinary_keep`.
- Facets / facet `write_kind` = **out of scope** (named residual).
- Mining = hybrid co-equal: frequency + miss_class in one pipeline.
- A1 dangerous set = exactly `{animalish, allergen_adjacent, dual_origin, umbrella}`.
- Exit: round-trip + no new false Safes vs `phase2a_matrix_baseline.json` + precision plumbing (query helpers). Live 50-decision precision bar is an **ops exit** measured after sample window fills — plan ships the query + fixture tests that prove the math.

**Path sanity (verified 2026-07-23):**

| Path | Confirmed |
|------|-----------|
| `backend/core/knowledge/ike2/coverage_os/hybrid_gate.py` | `decide_promote`, `has_dual_origin_collision`, `is_umbrella_term`; `_row_flags` private today |
| `backend/core/knowledge/ike2/coverage_os/deny_lists.py` | `is_allergen_adjacent`, `is_animalish` |
| `backend/core/knowledge/ike2/coverage_os/promote_writer.py` | `commit_promotion(..., auto=False, reviewer_id=..., approval_rationale=...)` |
| `backend/core/knowledge/ike2/miss_class.py` | `classify_miss_class(atom) -> str` (M1–M8-ish) |
| `backend/core/enrichment/unknown_log.py` | `UnknownIngredientsLog`; JSON shape `{"unknown_ingredients": {key: {frequency, ...}}}` |
| `data/unknown_ingredients_log.json` | Live log present |
| `backend/tests/ike2/coverage_os/fixtures/phase2a_matrix_baseline.json` | Phase 2a baseline for no-new-false-Safes |
| `backend/scripts/seed_neutralize_roles.py` | Force-human commit pattern to mirror |

## Literal-code-trace discipline (mandatory)

| Gate | After task | Trace must show |
|------|------------|-----------------|
| **LCT-1** | Task 1 | `assign_safety_class` body literally calls imported `is_allergen_adjacent` / `is_animalish` / `has_dual_origin_collision` / `is_umbrella_term` in **decide_promote order**; alignment tests pass; monkeypatch spy proves call site (not re-derived inline logic) |
| **LCT-2** | Task 5 | `submit_induced` never passes `auto=True`; even plant_closed / `auto_promote` gate decision still commits with `auto=False` + reviewer fields |
| **LCT-3** | Task 8 | Round-trip alias + role carry `safety_class` + provenance into ledger payload; precision helpers filter A1 set correctly |

Soft “looks right” sign-off is insufficient for LCT-1 especially — paste the function body and the spy test output into review notes.

## File map

| Path | Responsibility |
|------|----------------|
| `backend/core/knowledge/ike2/coverage_os/induction/__init__.py` | Package export |
| `backend/core/knowledge/ike2/coverage_os/induction/types.py` | `InductionCandidate`, `SafetyClass`, `ProposalKind` |
| `backend/core/knowledge/ike2/coverage_os/induction/safety_class.py` | `assign_safety_class` — thin composer only |
| `backend/core/knowledge/ike2/coverage_os/induction/cluster.py` | Load unknown log + miss_class; prioritize clusters |
| `backend/core/knowledge/ike2/coverage_os/induction/propose_alias.py` | Unique closed-form alias proposals |
| `backend/core/knowledge/ike2/coverage_os/induction/propose_role.py` | Pattern-fill + backfill role proposals |
| `backend/core/knowledge/ike2/coverage_os/induction/submit.py` | Force-human wrapper around gate + `commit_promotion` |
| `backend/core/knowledge/ike2/coverage_os/induction/precision.py` | A / A1 / A2 ledger queries |
| `backend/core/knowledge/ike2/coverage_os/induction/pipeline.py` | `build_candidates` compose |
| `backend/core/knowledge/ike2/coverage_os/promote_ledger.py` | Public `iter_rows()`; optional `payload` on `append_non_promotable` for reject safety_class |
| `backend/core/knowledge/ike2/coverage_os/hybrid_gate.py` | Export public `row_flags` (rename/alias `_row_flags`) for shared flag extraction |
| `backend/scripts/run_induction.py` | Operator CLI: cluster → propose → (review) → submit |
| `backend/tests/ike2/coverage_os/induction/test_safety_class.py` | Alignment + spy (LCT-1) |
| `backend/tests/ike2/coverage_os/induction/test_cluster.py` | Hybrid clustering |
| `backend/tests/ike2/coverage_os/induction/test_propose_alias.py` | Unique / no-proposal |
| `backend/tests/ike2/coverage_os/induction/test_propose_role.py` | Pattern-fill + backfill |
| `backend/tests/ike2/coverage_os/induction/test_submit.py` | Force-human (LCT-2) |
| `backend/tests/ike2/coverage_os/induction/test_precision.py` | A/A1/A2 math |
| `backend/tests/ike2/coverage_os/induction/test_phase2b_exit.py` | Round-trip + matrix smoke |

## Dependency order (do not reorder)

```text
Task 1 types + safety_class + LCT-1 alignment ── LCT-1
Task 2 cluster (frequency + miss_class)
Task 3 propose_alias
Task 4 propose_role
Task 5 submit force-human ───────────────────── LCT-2
Task 6 precision queries
Task 7 CLI glue
Task 8 exit: round-trip + matrix + precision fixtures ── LCT-3
```

---

### Task 1: `types` + `assign_safety_class` (+ LCT-1)

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/induction/__init__.py`
- Create: `backend/core/knowledge/ike2/coverage_os/induction/types.py`
- Create: `backend/core/knowledge/ike2/coverage_os/induction/safety_class.py`
- Modify: `backend/core/knowledge/ike2/coverage_os/hybrid_gate.py` — export `row_flags` as public alias of `_row_flags` (keep `_row_flags` name as thin wrapper calling `row_flags` or rename and update internal call sites)
- Test: `backend/tests/ike2/coverage_os/induction/test_safety_class.py`

**Interfaces:**
- Consumes: `deny_lists.is_allergen_adjacent`, `deny_lists.is_animalish`, `hybrid_gate.has_dual_origin_collision`, `hybrid_gate.is_umbrella_term`
- Produces:
  - `SafetyClass = Literal["plant_closed","animalish","allergen_adjacent","dual_origin","umbrella","role_only"]`
  - `ProposalKind = Literal["variant_alias","ontology_role"]`
  - `A1_DANGEROUS: frozenset[SafetyClass] = frozenset({"animalish","allergen_adjacent","dual_origin","umbrella"})`
  - `assign_safety_class(*, candidate_name: str, flags: Mapping[str, Any] | None, ontology: Mapping[str, Any]) -> SafetyClass`
  - `hybrid_gate.row_flags(row: Mapping[str, Any]) -> dict[str, Any]` (public)

**Branch order (spec lock — must match `decide_promote`):**

1. `is_allergen_adjacent(flags)` → `allergen_adjacent`
2. `is_animalish(flags)` → `animalish`
3. `has_dual_origin_collision(candidate_name, ontology)` → `dual_origin`
4. `is_umbrella_term(candidate_name, flags)` → `umbrella`
5. `flags.get("plant_origin") and not flags.get("animal_origin")` → `plant_closed`
6. else → `role_only`

- [ ] **Step 1: Write the failing alignment + spy tests**

```python
# backend/tests/ike2/coverage_os/induction/test_safety_class.py
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core.knowledge.ike2.coverage_os.hybrid_gate import decide_promote
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger
from core.knowledge.ike2.coverage_os.induction.safety_class import assign_safety_class
from core.knowledge.ike2.coverage_os.induction.types import A1_DANGEROUS


def _empty_ledger(tmp_path):
    return PromoteLedger(tmp_path / "ledger.jsonl")


@pytest.mark.parametrize(
    "name,flags,ontology,expected_class,expected_rule_id",
    [
        ("soy lecithin", {"soy_source": True}, {"ingredients": []}, "allergen_adjacent", "human_allergen_adjacent"),
        ("gelatin", {"animal_origin": True}, {"ingredients": []}, "animalish", "human_animal_derived"),
        (
            "ghee",
            {},
            {"ingredients": [{"canonical_name": "ghee", "animal_origin": True, "dairy_source": True}]},
            "dual_origin",
            "human_dual_origin_collision",
        ),
        ("natural flavors", {"verdict_cap": "WARN"}, {"ingredients": []}, "umbrella", "human_umbrella"),
        ("broccoli", {"plant_origin": True}, {"ingredients": []}, "plant_closed", "closed_form_plant_v1"),
        ("mystery token", {}, {"ingredients": []}, "role_only", "human_fail_closed"),
    ],
)
def test_safety_class_aligns_with_decide_promote(
    tmp_path, name, flags, ontology, expected_class, expected_rule_id
):
    sc = assign_safety_class(candidate_name=name, flags=flags, ontology=ontology)
    assert sc == expected_class
    decision = decide_promote(
        candidate_key=f"{name}=>{name}",
        candidate_name=name,
        flags=flags,
        ledger=_empty_ledger(tmp_path),
        ontology=ontology,
    )
    assert decision.rule_id == expected_rule_id
    if expected_class in A1_DANGEROUS:
        assert decision.action == "human_approval"
    if expected_class == "plant_closed":
        assert decision.action == "auto_promote"


def test_assign_safety_class_calls_is_animalish_not_inline(monkeypatch):
    """LCT-1: prove literal call to deny_lists helper, not re-derived flags."""
    import core.knowledge.ike2.coverage_os.induction.safety_class as mod

    calls: list = []

    def spy(flags):
        calls.append(dict(flags or {}))
        return True

    monkeypatch.setattr(mod, "is_animalish", spy)
    monkeypatch.setattr(mod, "is_allergen_adjacent", lambda f: False)
    out = assign_safety_class(
        candidate_name="x",
        flags={"animal_origin": True},
        ontology={"ingredients": []},
    )
    assert out == "animalish"
    assert calls, "is_animalish was not called"


def test_safety_class_module_has_no_local_animal_frozenset():
    import core.knowledge.ike2.coverage_os.induction.safety_class as sc_mod

    path = Path(sc_mod.__file__)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and "ANIMAL" in t.id.upper():
                    pytest.fail(f"forbidden local constant {t.id}")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_safety_class.py -v`  
Expected: FAIL (module not found / `assign_safety_class` missing)

- [ ] **Step 3: Export `row_flags` from hybrid_gate**

In `hybrid_gate.py`, rename `_row_flags` → `row_flags` and keep `_row_flags = row_flags` for any external private imports, **or** add:

```python
def row_flags(row: Mapping[str, Any]) -> dict[str, Any]:
    """Public flag extraction — shared by gate and induction safety_class callers."""
    nested = row.get("flags")
    if isinstance(nested, dict) and nested:
        return dict(nested)
    return {k: row[k] for k in _ROW_FLAG_KEYS if k in row}


def _row_flags(row: Mapping[str, Any]) -> dict[str, Any]:
    return row_flags(row)
```

- [ ] **Step 4: Implement types + assign_safety_class**

```python
# backend/core/knowledge/ike2/coverage_os/induction/types.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal

SafetyClass = Literal[
    "plant_closed",
    "animalish",
    "allergen_adjacent",
    "dual_origin",
    "umbrella",
    "role_only",
]
ProposalKind = Literal["variant_alias", "ontology_role"]

A1_DANGEROUS: frozenset[str] = frozenset(
    {"animalish", "allergen_adjacent", "dual_origin", "umbrella"}
)

ROLE_ENUM: frozenset[str] = frozenset(
    {"plant_mod", "dairy_head", "process_keep", "culinary_keep"}
)


@dataclass
class InductionCandidate:
    proposal_kind: ProposalKind
    raw: str
    canonical: str | None
    role: str | None
    frequency: int
    miss_class: str | None
    safety_class: SafetyClass
    provenance: dict[str, Any] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
```

```python
# backend/core/knowledge/ike2/coverage_os/induction/safety_class.py
from __future__ import annotations
from typing import Any, Mapping

from core.knowledge.ike2.coverage_os.deny_lists import (
    is_allergen_adjacent,
    is_animalish,
)
from core.knowledge.ike2.coverage_os.hybrid_gate import (
    has_dual_origin_collision,
    is_umbrella_term,
)
from core.knowledge.ike2.coverage_os.induction.types import SafetyClass


def assign_safety_class(
    *,
    candidate_name: str,
    flags: Mapping[str, Any] | None,
    ontology: Mapping[str, Any],
) -> SafetyClass:
    """Label for precision A1 — same predicates/order as decide_promote."""
    f = dict(flags or {})
    if is_allergen_adjacent(f):
        return "allergen_adjacent"
    if is_animalish(f):
        return "animalish"
    if has_dual_origin_collision(candidate_name, ontology):
        return "dual_origin"
    if is_umbrella_term(candidate_name, f):
        return "umbrella"
    if f.get("plant_origin") and not f.get("animal_origin"):
        return "plant_closed"
    return "role_only"
```

```python
# backend/core/knowledge/ike2/coverage_os/induction/__init__.py
"""Coverage OS Phase 2b induction pipeline."""
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_safety_class.py -v`  
Expected: PASS

- [ ] **Step 6: LCT-1 review gate** — paste `assign_safety_class` source + spy test output into review notes; confirm imports are from `deny_lists` / `hybrid_gate` only.

- [ ] **Step 7: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/induction \
  backend/core/knowledge/ike2/coverage_os/hybrid_gate.py \
  backend/tests/ike2/coverage_os/induction/test_safety_class.py
git commit -m "$(cat <<'EOF'
feat(coverage-os): add induction safety_class aligned to hybrid gate

Assigns precision labels via deny_lists/hybrid_gate helpers in decide_promote order; spy + alignment tests lock the wire.
EOF
)"
```

---

### Task 2: `cluster` — frequency + miss_class

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/induction/cluster.py`
- Test: `backend/tests/ike2/coverage_os/induction/test_cluster.py`

**Interfaces:**
- Consumes: unknown-log dict shape (`unknown_ingredients` → `{normalized_key: {frequency, raw_inputs, ...}}`), `miss_class.classify_miss_class`
- Produces:
  - `@dataclass ClusterItem`: `normalized_key: str`, `raw: str`, `frequency: int`, `miss_class: str`
  - `load_clusters(log_path: Path | None = None, *, entries: Mapping | None = None, min_frequency: int = 1) -> list[ClusterItem]`
  - Sort: frequency desc, then normalized_key asc (stable prioritization)

- [ ] **Step 1: Write failing test**

```python
# backend/tests/ike2/coverage_os/induction/test_cluster.py
from core.knowledge.ike2.coverage_os.induction.cluster import load_clusters


def test_cluster_hybrid_frequency_and_miss_class():
    entries = {
        "beef brisket": {
            "normalized_key": "beef brisket",
            "raw_inputs": ["Beef brisket"],
            "frequency": 10,
        },
        "xyz junk": {
            "normalized_key": "xyz junk",
            "raw_inputs": ["xyz junk"],
            "frequency": 2,
        },
    }
    items = load_clusters(entries=entries, min_frequency=2)
    assert items[0].normalized_key == "beef brisket"
    assert items[0].frequency == 10
    assert items[0].miss_class.startswith("M2")
    assert items[1].miss_class  # classified, co-equal signal present
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_cluster.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement**

```python
# backend/core/knowledge/ike2/coverage_os/induction/cluster.py
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from core.knowledge.ike2.miss_class import classify_miss_class


@dataclass(frozen=True)
class ClusterItem:
    normalized_key: str
    raw: str
    frequency: int
    miss_class: str


def load_clusters(
    log_path: Path | None = None,
    *,
    entries: Mapping[str, Any] | None = None,
    min_frequency: int = 1,
) -> list[ClusterItem]:
    if entries is None:
        if log_path is None:
            raise ValueError("load_clusters requires log_path or entries")
        data = json.loads(Path(log_path).read_text(encoding="utf-8"))
        entries = data.get("unknown_ingredients") or {}
    out: list[ClusterItem] = []
    for key, ent in entries.items():
        if not isinstance(ent, Mapping):
            continue
        freq = int(ent.get("frequency") or 0)
        if freq < min_frequency:
            continue
        raws = ent.get("raw_inputs") or [key]
        raw = str(raws[0] if raws else key)
        nk = str(ent.get("normalized_key") or key)
        out.append(
            ClusterItem(
                normalized_key=nk,
                raw=raw,
                frequency=freq,
                miss_class=classify_miss_class(raw),
            )
        )
    out.sort(key=lambda c: (-c.frequency, c.normalized_key))
    return out
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_cluster.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/induction/cluster.py \
  backend/tests/ike2/coverage_os/induction/test_cluster.py
git commit -m "$(cat <<'EOF'
feat(coverage-os): cluster unknown-log with frequency and miss_class

Hybrid mining signal for induction prioritization.
EOF
)"
```

---

### Task 3: `propose_alias` — unique closed-form only

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/induction/propose_alias.py`
- Test: `backend/tests/ike2/coverage_os/induction/test_propose_alias.py`

**Interfaces:**
- Consumes: `ClusterItem`, ontology mapping, existing alias table, `normalize_ingredient_key`, `truth_anchor.lookup`, `commodity_head.simple_commodity_head`, `assign_safety_class`, `hybrid_gate.row_flags`
- Produces:
  - `propose_alias(item: ClusterItem, *, ontology: Mapping, alias_table: Mapping[str, str]) -> InductionCandidate | None`
  - Returns `None` when zero or >1 closed-form targets, or when raw already equals unique target, or when raw already in alias_table

**Unique closed-form resolve (deterministic):**

Collect a set of candidate target keys from, in order (union, then uniqueness check):

1. Exact ontology canonical / alias name match after `normalize_ingredient_key(raw)` (row already exists — then raw is not an *alias proposal*; return `None` unless proposing a *different* surface form — for v1: if exact row hit, **no alias proposal**).
2. Strip/fold via `simple_commodity_head(raw)` → if head normalizes to exactly one existing ontology row (canonical or alias), that row’s canonical is a target.
3. Token-drop variants: for multi-word raw, try dropping one trailing or leading token at a time; each hit that resolves to an ontology row adds that canonical to the set.
4. If the set has **exactly one** canonical **and** that canonical ≠ normalized raw **and** raw not already aliased → propose `variant_alias` raw→canonical.
5. Else → `None`.

`safety_class` / `flags`: from the **resolved target row** via `row_flags(row)`, name = that row’s `canonical_name`.

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/ike2/coverage_os/induction/test_propose_alias.py
from core.knowledge.ike2.coverage_os.induction.cluster import ClusterItem
from core.knowledge.ike2.coverage_os.induction.propose_alias import propose_alias


def _ont(*rows):
    return {"ingredients": list(rows)}


def test_unique_head_resolves_to_alias_proposal():
    ontology = _ont({"canonical_name": "broccoli", "plant_origin": True})
    item = ClusterItem("broccoli florets", "broccoli florets", 5, "M4_morphology")
    cand = propose_alias(item, ontology=ontology, alias_table={})
    assert cand is not None
    assert cand.proposal_kind == "variant_alias"
    assert cand.canonical == "broccoli"
    assert cand.safety_class == "plant_closed"


def test_ambiguous_or_missing_yields_no_proposal():
    # Two-token raw where each single-token drop hits a different ontology row
    # → len(targets) == 2 → no proposal (ambiguous branch).
    ontology = _ont(
        {"canonical_name": "apple", "plant_origin": True},
        {"canonical_name": "vinegar", "plant_origin": True},
    )
    ambiguous = ClusterItem("apple vinegar", "apple vinegar", 3, "M1_absent")
    assert propose_alias(ambiguous, ontology=ontology, alias_table={}) is None
    # Zero closed-form targets.
    missing = ClusterItem("zzzz unknown", "zzzz unknown", 3, "M1_absent")
    assert propose_alias(missing, ontology=ontology, alias_table={}) is None


def test_already_aliased_no_proposal():
    ontology = _ont({"canonical_name": "salt", "plant_origin": True})
    item = ClusterItem("salt himalayan", "salt himalayan", 4, "M1_absent")
    assert (
        propose_alias(
            item,
            ontology=ontology,
            alias_table={"salt himalayan": "salt"},
        )
        is None
    )
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_propose_alias.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement `propose_alias`**

```python
# backend/core/knowledge/ike2/coverage_os/induction/propose_alias.py
from __future__ import annotations

from typing import Any, Mapping

from core.knowledge.ike2.commodity_head import simple_commodity_head
from core.knowledge.ike2.coverage_os.hybrid_gate import row_flags
from core.knowledge.ike2.coverage_os.induction.cluster import ClusterItem
from core.knowledge.ike2.coverage_os.induction.safety_class import assign_safety_class
from core.knowledge.ike2.coverage_os.induction.types import InductionCandidate
from core.normalization.normalizer import normalize_ingredient_key


def _ontology_index(ontology: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for row in ontology.get("ingredients") or []:
        if not isinstance(row, Mapping):
            continue
        canon = normalize_ingredient_key(str(row.get("canonical_name") or row.get("name") or ""))
        if not canon:
            continue
        idx[canon] = dict(row)
        for a in row.get("aliases") or []:
            ak = normalize_ingredient_key(str(a))
            if ak:
                idx[ak] = dict(row)
    return idx


def _candidate_targets(raw: str, ontology_index: Mapping[str, dict[str, Any]]) -> set[str]:
    """Deterministic folds only — head + single token drop. No fuzzy."""
    targets: set[str] = set()
    nk = normalize_ingredient_key(raw)
    if not nk:
        return targets

    def _add_if_row(key: str) -> None:
        row = ontology_index.get(key)
        if row is None:
            return
        canon = normalize_ingredient_key(str(row.get("canonical_name") or ""))
        if canon:
            targets.add(canon)

    # Exact row hit → not an alias proposal surface (handled by caller via empty/equal check)
    _add_if_row(nk)

    head = simple_commodity_head(raw)
    if head:
        _add_if_row(normalize_ingredient_key(head))

    parts = nk.split()
    if len(parts) >= 2:
        _add_if_row(normalize_ingredient_key(" ".join(parts[:-1])))
        _add_if_row(normalize_ingredient_key(" ".join(parts[1:])))
    return targets


def propose_alias(
    item: ClusterItem,
    *,
    ontology: Mapping[str, Any],
    alias_table: Mapping[str, str],
) -> InductionCandidate | None:
    nk = normalize_ingredient_key(item.normalized_key or item.raw)
    if not nk:
        return None
    if nk in alias_table:
        return None

    idx = _ontology_index(ontology)
    if nk in idx:
        return None  # already an ontology surface form

    targets = _candidate_targets(item.raw, idx)
    targets.discard(nk)
    if len(targets) != 1:
        return None

    canonical = next(iter(targets))
    row = idx[canonical]
    flags = row_flags(row)
    safety = assign_safety_class(
        candidate_name=str(row.get("canonical_name") or canonical),
        flags=flags,
        ontology=ontology,
    )
    return InductionCandidate(
        proposal_kind="variant_alias",
        raw=nk,
        canonical=canonical,
        role=None,
        frequency=item.frequency,
        miss_class=item.miss_class,
        safety_class=safety,
        provenance={
            "rule": "unique_closed_form",
            "cluster_key": item.normalized_key,
        },
        flags=flags,
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_propose_alias.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/induction/propose_alias.py \
  backend/tests/ike2/coverage_os/induction/test_propose_alias.py
git commit -m "$(cat <<'EOF'
feat(coverage-os): propose unique closed-form alias candidates

No proposal when zero or ambiguous targets; safety_class from resolved target row.
EOF
)"
```

---

### Task 4: `propose_role` — pattern-fill + backfill

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/induction/propose_role.py`
- Test: `backend/tests/ike2/coverage_os/induction/test_propose_role.py`

**Interfaces:**
- Consumes: `ClusterItem` / ontology rows, `neutralize.build_role_index`, closed `ROLE_ENUM`, tear evidence optional mapping
- Produces:
  - `propose_role_pattern_fill(item, *, ontology, role_index) -> InductionCandidate | None`
  - `propose_role_backfill(*, ontology, tear_evidence: Mapping[str, str]) -> list[InductionCandidate]`
  - `tear_evidence`: `normalized_canonical -> role` implicated by matrix/tear telemetry (tests inject fixtures)

**Pattern-fill:** For multi-word `item.raw`, if one token already has a role in `role_index` and an adjacent token has **no** ontology row (or row with empty role), propose that missing token as the partner role implied by adjacency:

- If known token is `dairy_head` / animalish partner context and other token looks like plant_mod seed adjacency → propose other as `plant_mod` only when that token already exists as an ontology row with empty role **or** when proposing role on an existing empty-role row (v1: **only propose roles for tokens that already have an ontology row** — do not invent new ontology rows for roles; alias path covers new surface forms).
- If known token is `plant_mod` and partner is existing dairy_head-empty → propose `dairy_head` only when empty.

Keep v1 narrow: **pattern-fill only fills empty `role` on an existing ontology row** when adjacency to a role-bearing neighbor matches neutralize partner shapes. If no existing empty-role row → `None`.

**Backfill:** For each ontology row with missing/empty `role`, if `tear_evidence.get(canonical) in ROLE_ENUM`, propose that role.

`safety_class` from the **row being role-filled** (canonical + `row_flags(row)`).

- [ ] **Step 1: Write failing tests**

```python
from core.knowledge.ike2.coverage_os.induction.cluster import ClusterItem
from core.knowledge.ike2.coverage_os.induction.propose_role import (
    propose_role_backfill,
    propose_role_pattern_fill,
)
from core.knowledge.ike2.coverage_os.neutralize import build_role_index


def test_pattern_fill_proposes_empty_plant_mod_beside_dairy_head():
    ontology = {
        "ingredients": [
            {"canonical_name": "yogurt", "role": "dairy_head", "dairy_source": True, "animal_origin": True},
            {"canonical_name": "oat", "plant_origin": True},  # empty role
        ]
    }
    role_index = build_role_index(ontology["ingredients"])
    item = ClusterItem("oat yogurt", "oat yogurt", 8, "M6_dairy_variety")
    cand = propose_role_pattern_fill(item, ontology=ontology, role_index=role_index)
    assert cand is not None
    assert cand.proposal_kind == "ontology_role"
    assert cand.canonical == "oat"
    assert cand.role == "plant_mod"
    assert cand.safety_class == "plant_closed"


def test_backfill_from_tear_evidence():
    ontology = {
        "ingredients": [
            {"canonical_name": "vinegar", "plant_origin": True},
        ]
    }
    cands = propose_role_backfill(
        ontology=ontology,
        tear_evidence={"vinegar": "culinary_keep"},
    )
    assert len(cands) == 1
    assert cands[0].role == "culinary_keep"
    assert cands[0].safety_class == "plant_closed"


def test_no_role_proposal_without_existing_row():
    ontology = {"ingredients": [{"canonical_name": "yogurt", "role": "dairy_head", "dairy_source": True}]}
    role_index = build_role_index(ontology["ingredients"])
    item = ClusterItem("cashew yogurt", "cashew yogurt", 5, "M1_absent")
    assert propose_role_pattern_fill(item, ontology=ontology, role_index=role_index) is None
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_propose_role.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement**

```python
# backend/core/knowledge/ike2/coverage_os/induction/propose_role.py
from __future__ import annotations

from typing import Any, Mapping

from core.knowledge.ike2.coverage_os.hybrid_gate import row_flags
from core.knowledge.ike2.coverage_os.induction.cluster import ClusterItem
from core.knowledge.ike2.coverage_os.induction.safety_class import assign_safety_class
from core.knowledge.ike2.coverage_os.induction.types import ROLE_ENUM, InductionCandidate
from core.normalization.normalizer import normalize_ingredient_key


def _rows_by_canon(ontology: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in ontology.get("ingredients") or []:
        if not isinstance(row, Mapping):
            continue
        canon = normalize_ingredient_key(str(row.get("canonical_name") or ""))
        if canon:
            out[canon] = dict(row)
    return out


def _empty_role(row: Mapping[str, Any]) -> bool:
    return not str(row.get("role") or "").strip()


def _candidate_for_row(
    row: Mapping[str, Any],
    *,
    role: str,
    frequency: int,
    miss_class: str | None,
    provenance: dict[str, Any],
    ontology: Mapping[str, Any],
) -> InductionCandidate | None:
    if role not in ROLE_ENUM:
        return None
    canon = normalize_ingredient_key(str(row.get("canonical_name") or ""))
    if not canon:
        return None
    flags = row_flags(row)
    safety = assign_safety_class(
        candidate_name=str(row.get("canonical_name") or canon),
        flags=flags,
        ontology=ontology,
    )
    return InductionCandidate(
        proposal_kind="ontology_role",
        raw=canon,
        canonical=canon,
        role=role,
        frequency=frequency,
        miss_class=miss_class,
        safety_class=safety,
        provenance=provenance,
        flags=flags,
    )


def propose_role_pattern_fill(
    item: ClusterItem,
    *,
    ontology: Mapping[str, Any],
    role_index: Mapping[str, str],
) -> InductionCandidate | None:
    parts = normalize_ingredient_key(item.raw).split()
    if len(parts) != 2:
        return None
    a, b = parts[0], parts[1]
    rows = _rows_by_canon(ontology)

    def _try(known: str, other: str, proposed_role: str) -> InductionCandidate | None:
        if role_index.get(known) not in {"dairy_head", "plant_mod"}:
            return None
        row = rows.get(other)
        if row is None or not _empty_role(row):
            return None
        # Partner shapes: dairy_head beside empty → plant_mod; plant_mod beside empty → dairy_head
        known_role = role_index.get(known)
        if known_role == "dairy_head" and proposed_role != "plant_mod":
            return None
        if known_role == "plant_mod" and proposed_role != "dairy_head":
            return None
        return _candidate_for_row(
            row,
            role=proposed_role,
            frequency=item.frequency,
            miss_class=item.miss_class,
            provenance={"rule": "pattern_fill", "neighbor": known, "cluster_key": item.normalized_key},
            ontology=ontology,
        )

    return (
        _try(a, b, "plant_mod")
        or _try(b, a, "plant_mod")
        or _try(a, b, "dairy_head")
        or _try(b, a, "dairy_head")
    )


def propose_role_backfill(
    *,
    ontology: Mapping[str, Any],
    tear_evidence: Mapping[str, str],
) -> list[InductionCandidate]:
    out: list[InductionCandidate] = []
    for canon, row in _rows_by_canon(ontology).items():
        if not _empty_role(row):
            continue
        role = str(tear_evidence.get(canon) or "").strip()
        cand = _candidate_for_row(
            row,
            role=role,
            frequency=0,
            miss_class=None,
            provenance={"rule": "tear_backfill"},
            ontology=ontology,
        )
        if cand is not None:
            out.append(cand)
    return out
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_propose_role.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/induction/propose_role.py \
  backend/tests/ike2/coverage_os/induction/test_propose_role.py
git commit -m "$(cat <<'EOF'
feat(coverage-os): propose role pattern-fill and tear backfill

Only fills empty roles on existing ontology rows from closed enum.
EOF
)"
```

---

### Task 5: `submit` — structural force-human (+ LCT-2)

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/induction/submit.py`
- Test: `backend/tests/ike2/coverage_os/induction/test_submit.py`

**Interfaces:**
- Consumes: `InductionCandidate`, `decide_promote`, `commit_promotion`, `PromoteLedger`, `candidate_key`
- Produces:
  - `build_promote_entry(cand: InductionCandidate) -> dict` (payload + inverse)
  - `submit_induced(cand, *, ledger, ontology_path, aliases_path, ontology, reviewer_id, approval_rationale, decision: Literal["accept","reject"]) -> dict | None`
  - On `reject`: **no L2 write**; append `ledger.append_non_promotable(..., source="phase2b_induction", reason="reviewer_reject", payload={"induction": ...})` so precision A’s denominator includes rejects with `safety_class` (see Task 6). Do **not** call `commit_promotion`.
  - On `accept`: always `commit_promotion(..., auto=False, reviewer_id=..., approval_rationale=...)` after `decide_promote` (skip if `rejected`)

**Payload shapes:**

Alias:
```python
{
  "candidate_key": candidate_key(raw, canonical),
  "payload": {
    "write_kind": "variant_alias",
    "alias": raw_normalized,
    "canonical": canonical,
    "induction": { ...provenance, safety_class, frequency, miss_class, proposal_kind },
    "inverse": {"write_kind": "variant_alias", "alias": raw_normalized},
  },
}
```

Role:
```python
{
  "candidate_key": candidate_key(canonical, canonical),
  "payload": {
    "write_kind": "ontology_row",
    "canonical_name": canonical,
    "role": role,
    "flags": {},
    "induction": { ... },
    "inverse": {
      "write_kind": "ontology_row",
      "canonical_name": canonical,
      "prior_role": None,
      "role_patch_only": True,
    },
  },
}
```

- [ ] **Step 1: Write failing LCT-2 tests**

```python
# backend/tests/ike2/coverage_os/induction/test_submit.py
import json
from pathlib import Path

from core.knowledge.ike2.coverage_os.induction.types import InductionCandidate
from core.knowledge.ike2.coverage_os.induction.submit import submit_induced
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger


def test_submit_force_human_even_when_gate_would_auto(tmp_path, monkeypatch):
    ontology_path = tmp_path / "ontology.json"
    aliases_path = tmp_path / "variant_aliases.json"
    ontology_path.write_text(json.dumps({"ingredients": []}), encoding="utf-8")
    aliases_path.write_text(json.dumps({"aliases": {}}), encoding="utf-8")
    ledger = PromoteLedger(tmp_path / "ledger.jsonl")

    cand = InductionCandidate(
        proposal_kind="variant_alias",
        raw="broccoli florets",
        canonical="broccoli",
        role=None,
        frequency=5,
        miss_class="M4_morphology",
        safety_class="plant_closed",
        provenance={"rule": "unique_head"},
        flags={"plant_origin": True},
    )
    # Ensure ontology has broccoli so alias apply works
    ontology_path.write_text(
        json.dumps({"ingredients": [{"canonical_name": "broccoli", "plant_origin": True}]}),
        encoding="utf-8",
    )
    ontology = json.loads(ontology_path.read_text(encoding="utf-8"))

    row = submit_induced(
        cand,
        ledger=ledger,
        ontology_path=ontology_path,
        aliases_path=aliases_path,
        ontology=ontology,
        reviewer_id="tester",
        approval_rationale="accept plant alias",
        decision="accept",
    )
    assert row is not None
    assert row["auto"] is False
    assert row["reviewer_id"] == "tester"
    assert row["payload"]["induction"]["safety_class"] == "plant_closed"


def test_submit_has_no_auto_true_call_site():
    import ast
    from core.knowledge.ike2.coverage_os.induction import submit as submit_mod

    tree = ast.parse(Path(submit_mod.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords or []:
                if kw.arg == "auto" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    raise AssertionError("submit must not pass auto=True")
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_submit.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement `submit_induced`**

```python
# backend/core/knowledge/ike2/coverage_os/induction/submit.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Mapping

from core.knowledge.ike2.coverage_os.hybrid_gate import decide_promote
from core.knowledge.ike2.coverage_os.induction.types import InductionCandidate
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key
from core.knowledge.ike2.coverage_os.promote_writer import commit_promotion
from core.normalization.normalizer import normalize_ingredient_key


def build_promote_entry(cand: InductionCandidate) -> dict[str, Any]:
    induction = {
        "safety_class": cand.safety_class,
        "frequency": cand.frequency,
        "miss_class": cand.miss_class,
        "proposal_kind": cand.proposal_kind,
        "provenance": dict(cand.provenance),
    }
    if cand.proposal_kind == "variant_alias":
        alias = normalize_ingredient_key(cand.raw)
        canon = normalize_ingredient_key(cand.canonical or "")
        return {
            "candidate_key": candidate_key(alias, canon),
            "payload": {
                "write_kind": "variant_alias",
                "alias": alias,
                "canonical": canon,
                "induction": induction,
                "inverse": {"write_kind": "variant_alias", "alias": alias},
            },
        }
    canon = normalize_ingredient_key(cand.canonical or cand.raw)
    return {
        "candidate_key": candidate_key(canon, canon),
        "payload": {
            "write_kind": "ontology_row",
            "canonical_name": canon,
            "role": cand.role,
            "flags": {},
            "induction": induction,
            "inverse": {
                "write_kind": "ontology_row",
                "canonical_name": canon,
                "prior_role": None,
                "role_patch_only": True,
            },
        },
    }


def submit_induced(
    cand: InductionCandidate,
    *,
    ledger: PromoteLedger,
    ontology_path: Path,
    aliases_path: Path,
    ontology: Mapping[str, Any],
    reviewer_id: str,
    approval_rationale: str,
    decision: Literal["accept", "reject"],
) -> dict[str, Any] | None:
    entry = build_promote_entry(cand)
    if decision != "accept":
        # No L2 write; ledger marker so precision A counts the reject.
        return ledger.append_non_promotable(
            candidate_key=entry["candidate_key"],
            rule_id="induction_reviewer_reject",
            source="phase2b_induction",
            reason="reviewer_reject",
            payload={"induction": entry["payload"]["induction"]},
        )

    name = cand.canonical or cand.raw
    gate = decide_promote(
        candidate_key=entry["candidate_key"],
        candidate_name=name,
        flags=cand.flags,
        ledger=ledger,
        ontology=ontology,
    )
    if gate.action == "rejected":
        return None

    # Structural force-human: never auto=True, even if gate.action == auto_promote.
    return commit_promotion(
        entry,
        ledger,
        ontology_path=ontology_path,
        aliases_path=aliases_path,
        rule_id=gate.rule_id,
        source="phase2b_induction",
        auto=False,
        reviewer_id=reviewer_id,
        approval_rationale=approval_rationale,
        candidate_key=entry["candidate_key"],
    )
```

Also add a submit test: `decision="reject"` → no aliases/ontology change, ledger has `confirmed_non_promotable` with `source="phase2b_induction"`.

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_submit.py -v`  
Expected: PASS

- [ ] **Step 5: LCT-2 review gate** — paste `submit_induced` commit call + ast test output.

- [ ] **Step 6: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/induction/submit.py \
  backend/tests/ike2/coverage_os/induction/test_submit.py
git commit -m "$(cat <<'EOF'
feat(coverage-os): force-human submit wrapper for induction

Structural auto=False path; plant_closed still requires reviewer fields.
EOF
)"
```

---

### Task 6: `precision` — A / A1 / A2 queries (ledger-connected)

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/induction/precision.py`
- Modify: `backend/core/knowledge/ike2/coverage_os/promote_ledger.py` — **(1)** add public `iter_rows()` wrapper around existing `_iter_rows` (**no rename**); **(2)** add optional `payload: dict | None = None` to `append_non_promotable` (omit key when None)
- Modify: `backend/tests/ike2/coverage_os/test_promote_ledger.py` — optional-payload + bare-row regression
- Test: `backend/tests/ike2/coverage_os/induction/test_precision.py`

**Interfaces:**
- Consumes: real `PromoteLedger` JSONL via `ledger.iter_rows()` — promoted / demoted / confirmed_non_promotable rows with `source`, `payload.induction.safety_class`, demote `reason`
- Produces:
  - `@dataclass DecisionRecord`: `candidate_key`, `accepted`, `safety_class`, `demoted_for_safety`
  - `@dataclass PrecisionReport`: `n_decisions`, `accept_rate`, `a1_n`, `a1_accept_rate`, `a2_demote_for_safety_count`, `meets_a`, `meets_a1`, `meets_a2`
  - `demote_reason_is_safety(reason: str | None) -> bool` — True iff `"safety"` in reason (case-insensitive)
  - `iter_induced_decisions(ledger: PromoteLedger, *, source: str = "phase2b_induction") -> list[DecisionRecord]`
  - `measure_precision(records: list[DecisionRecord], *, window: int = 50) -> PrecisionReport`

**`iter_induced_decisions` algorithm (load-bearing — ops exit depends on this):**

1. Scan `ledger.iter_rows()` in append order.
2. Collect induction **accepts**: `kind == "promoted"` and `source == source` and `auto is False`. Read `safety_class` from `payload.induction.safety_class` (required; skip row if missing — do not invent).
3. Collect induction **rejects**: `kind == "confirmed_non_promotable"` and `source == source` and `reason == "reviewer_reject"`. Read `safety_class` from `payload.induction.safety_class` (Task 5 reject path must pass `payload={"induction": ...}` via additive optional `payload` on `append_non_promotable`).
4. For each accept `candidate_key`, scan later rows for `kind == "demoted"` with same key; if any such demote has `demote_reason_is_safety(reason)`, set `demoted_for_safety=True` on that DecisionRecord.
5. Emit DecisionRecords in first-seen decision order (promote or reject appearance). Distinct `candidate_key`: if the same key appears twice, keep the **first** decision only for the window (spec: first N distinct decisions).
6. Rejects: `accepted=False`, `demoted_for_safety=False`.

**Ops path:** `measure_precision(iter_induced_decisions(ledger), window=50)` — no hand transcription.

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/ike2/coverage_os/induction/test_precision.py
from __future__ import annotations

import json
from pathlib import Path

from core.knowledge.ike2.coverage_os.induction.precision import (
    DecisionRecord,
    demote_reason_is_safety,
    iter_induced_decisions,
    measure_precision,
)
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger


def test_precision_a_a1_a2_thresholds():
    records = [
        DecisionRecord(f"k{i}", True, "plant_closed") for i in range(40)
    ] + [
        DecisionRecord(f"d{i}", True, "animalish") for i in range(9)
    ] + [
        DecisionRecord("d9", True, "animalish"),
    ]
    report = measure_precision(records, window=50)
    assert report.n_decisions == 50
    assert report.meets_a
    assert report.a1_n == 10
    assert report.meets_a1
    assert report.meets_a2


def test_a2_fails_on_safety_demote():
    records = [DecisionRecord(f"k{i}", True, "plant_closed") for i in range(50)]
    records[0] = DecisionRecord("k0", True, "plant_closed", demoted_for_safety=True)
    report = measure_precision(records, window=50)
    assert not report.meets_a2


def test_demote_reason_is_safety():
    assert demote_reason_is_safety("demoted for safety — wrong animal flag")
    assert demote_reason_is_safety("SAFETY")
    assert not demote_reason_is_safety("typo fix")


def test_iter_induced_decisions_from_real_ledger(tmp_path):
    """Ledger JSONL → DecisionRecord; demote safety correlates; reject counts as not accepted."""
    ledger = PromoteLedger(tmp_path / "ledger.jsonl")
    # Accept plant alias
    ledger.append_promoted(
        candidate_key="broccoli florets=>broccoli",
        rule_id="closed_form_plant_v1",
        source="phase2b_induction",
        payload={
            "write_kind": "variant_alias",
            "induction": {"safety_class": "plant_closed", "frequency": 5},
        },
        auto=False,
        reviewer_id="r1",
        approval_rationale="ok",
    )
    # Accept animalish then demote for safety
    ledger.append_promoted(
        candidate_key="gelatin powder=>gelatin",
        rule_id="human_animal_derived",
        source="phase2b_induction",
        payload={
            "write_kind": "variant_alias",
            "induction": {"safety_class": "animalish", "frequency": 3},
        },
        auto=False,
        reviewer_id="r1",
        approval_rationale="ok",
    )
    ledger.append_demoted(
        candidate_key="gelatin powder=>gelatin",
        reason="demoted for safety — incorrect animal routing",
    )
    # Reviewer reject
    ledger.append_non_promotable(
        candidate_key="junk=>junk",
        rule_id="induction_reviewer_reject",
        source="phase2b_induction",
        reason="reviewer_reject",
        payload={"induction": {"safety_class": "role_only"}},
    )
    # Unrelated source ignored
    ledger.append_promoted(
        candidate_key="noise=>noise",
        rule_id="closed_form_plant_v1",
        source="phase2a_role_seed",
        payload={"induction": {"safety_class": "plant_closed"}},
        auto=False,
        reviewer_id="r1",
        approval_rationale="seed",
    )

    records = iter_induced_decisions(ledger)
    by_key = {r.candidate_key: r for r in records}
    assert set(by_key) == {
        "broccoli florets=>broccoli",
        "gelatin powder=>gelatin",
        "junk=>junk",
    }
    assert by_key["broccoli florets=>broccoli"].accepted is True
    assert by_key["broccoli florets=>broccoli"].demoted_for_safety is False
    assert by_key["gelatin powder=>gelatin"].accepted is True
    assert by_key["gelatin powder=>gelatin"].demoted_for_safety is True
    assert by_key["gelatin powder=>gelatin"].safety_class == "animalish"
    assert by_key["junk=>junk"].accepted is False
    assert by_key["junk=>junk"].safety_class == "role_only"

    # Ops path: ledger → measure_precision (no hand DecisionRecords)
    report = measure_precision(records, window=50)
    assert report.n_decisions == 3
    assert report.a2_demote_for_safety_count == 1
    assert not report.meets_a2
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_precision.py -v`  
Expected: FAIL (`iter_induced_decisions` missing and/or `append_non_promotable` lacks `payload`)

- [ ] **Step 3a: Phase 1 ledger — additive only (no rename, no behavior change for existing callers)**

**Constraint:** Do **not** rename `_iter_rows`. Internal callers (`_next_version`, `find_non_promotable`, `latest_promoted`) keep calling `_iter_rows` unchanged. Version numbering, demote clearing, and non-promotable short-circuit stay byte-identical in logic.

**Change 1 — new public wrapper** (insert after `_iter_rows`):

```python
    def iter_rows(self) -> Iterator[dict[str, Any]]:
        """Public scan of append-only JSONL (order preserved)."""
        yield from self._iter_rows()
```

**Change 2 — optional `payload` on `append_non_promotable`** (replace the method body exactly as below). Existing call sites that omit `payload` keep the same row shape (no `payload` key):

```python
    def append_non_promotable(
        self,
        *,
        candidate_key: str,
        rule_id: str,
        source: str,
        reason: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "kind": "confirmed_non_promotable",
            "candidate_key": candidate_key,
            "rule_id": rule_id,
            "source": source,
            "reason": reason,
            "version": self._next_version(candidate_key),
        }
        if payload is not None:
            row["payload"] = payload
        return self._append(row)
```

**Regression (must pass unchanged):**
`cd backend && python -m pytest tests/ike2/coverage_os/test_promote_ledger.py tests/ike2/coverage_os/test_hybrid_gate.py tests/ike2/coverage_os/test_phase1_integration.py -v`

Add one new ledger unit test:

```python
def test_append_non_promotable_optional_payload(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    row = led.append_non_promotable(
        candidate_key="a=>a",
        rule_id="r",
        source="phase2b_induction",
        reason="reviewer_reject",
        payload={"induction": {"safety_class": "role_only"}},
    )
    assert row["payload"]["induction"]["safety_class"] == "role_only"
    bare = led.append_non_promotable(
        candidate_key="b=>b",
        rule_id="r",
        source="phase1",
        reason="blocked",
    )
    assert "payload" not in bare
```

- [ ] **Step 3b: Implement precision module**

```python
# backend/core/knowledge/ike2/coverage_os/induction/precision.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.knowledge.ike2.coverage_os.induction.types import A1_DANGEROUS
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger


@dataclass(frozen=True)
class DecisionRecord:
    candidate_key: str
    accepted: bool
    safety_class: str
    demoted_for_safety: bool = False


@dataclass(frozen=True)
class PrecisionReport:
    n_decisions: int
    accept_rate: float
    a1_n: int
    a1_accept_rate: float
    a2_demote_for_safety_count: int
    meets_a: bool
    meets_a1: bool
    meets_a2: bool


def demote_reason_is_safety(reason: str | None) -> bool:
    """A2: demote reason contains substring 'safety' (case-insensitive)."""
    return "safety" in str(reason or "").lower()


def iter_induced_decisions(
    ledger: PromoteLedger,
    *,
    source: str = "phase2b_induction",
) -> list[DecisionRecord]:
    rows = list(ledger.iter_rows())
    # candidate_key -> first decision draft
    ordered_keys: list[str] = []
    accepted: dict[str, bool] = {}
    safety: dict[str, str] = {}
    demoted_safety: dict[str, bool] = {}

    for row in rows:
        if row.get("source") != source and row.get("kind") != "demoted":
            continue
        key = str(row.get("candidate_key") or "")
        if not key:
            continue
        kind = row.get("kind")
        if kind == "promoted" and row.get("source") == source and row.get("auto") is False:
            if key in accepted:
                continue  # first distinct decision wins
            ind = (row.get("payload") or {}).get("induction") or {}
            sc = ind.get("safety_class")
            if not sc:
                continue
            ordered_keys.append(key)
            accepted[key] = True
            safety[key] = str(sc)
            demoted_safety[key] = False
        elif (
            kind == "confirmed_non_promotable"
            and row.get("source") == source
            and str(row.get("reason") or "") == "reviewer_reject"
        ):
            if key in accepted:
                continue
            ind = (row.get("payload") or {}).get("induction") or {}
            sc = ind.get("safety_class") or "role_only"
            ordered_keys.append(key)
            accepted[key] = False
            safety[key] = str(sc)
            demoted_safety[key] = False
        elif kind == "demoted" and key in accepted and accepted[key]:
            if demote_reason_is_safety(row.get("reason")):
                demoted_safety[key] = True

    return [
        DecisionRecord(
            candidate_key=k,
            accepted=accepted[k],
            safety_class=safety[k],
            demoted_for_safety=demoted_safety[k],
        )
        for k in ordered_keys
    ]


def measure_precision(
    records: list[DecisionRecord],
    *,
    window: int = 50,
) -> PrecisionReport:
    windowed = records[:window]
    n = len(windowed)
    accepts = sum(1 for r in windowed if r.accepted)
    accept_rate = (accepts / n) if n else 0.0
    a1 = [r for r in windowed if r.safety_class in A1_DANGEROUS]
    a1_n = len(a1)
    a1_accepts = sum(1 for r in a1 if r.accepted)
    a1_rate = (a1_accepts / a1_n) if a1_n else 0.0
    a2_count = sum(1 for r in windowed if r.demoted_for_safety)
    meets_a = n >= window and accept_rate >= 0.70
    meets_a1 = a1_n >= 10 and a1_rate >= 0.90
    meets_a2 = a2_count == 0
    return PrecisionReport(
        n_decisions=n,
        accept_rate=accept_rate,
        a1_n=a1_n,
        a1_accept_rate=a1_rate,
        a2_demote_for_safety_count=a2_count,
        meets_a=meets_a,
        meets_a1=meets_a1,
        meets_a2=meets_a2,
    )
```

Update Task 5 reject path to pass induction payload:

```python
return ledger.append_non_promotable(
    candidate_key=entry["candidate_key"],
    rule_id="induction_reviewer_reject",
    source="phase2b_induction",
    reason="reviewer_reject",
    payload={"induction": entry["payload"]["induction"]},
)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_precision.py -v`  
Expected: PASS (including `test_iter_induced_decisions_from_real_ledger`)

- [ ] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/induction/precision.py \
  backend/core/knowledge/ike2/coverage_os/promote_ledger.py \
  backend/tests/ike2/coverage_os/induction/test_precision.py \
  backend/core/knowledge/ike2/coverage_os/induction/submit.py
git commit -m "$(cat <<'EOF'
feat(coverage-os): ledger-backed induction precision A/A1/A2

iter_induced_decisions reads promote/reject/demote rows; ops path is measure_precision(iter_induced_decisions(ledger)).
EOF
)"
```

---

### Task 7: CLI glue — `pipeline.py` + `run_induction.py`

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/induction/pipeline.py`
- Create: `backend/scripts/run_induction.py`
- Test: `backend/tests/ike2/coverage_os/induction/test_pipeline.py`

**Interfaces:**
- Produces: `build_candidates(*, entries|log_path, ontology, alias_table, tear_evidence) -> list[InductionCandidate]`
- Dedupe by `candidate_key(raw, canonical)` / `candidate_key(canonical, canonical)`
- CLI: `--ontology`, `--aliases`, `--ledger`, `--unknown-log`, `--tear-evidence`, `--reviewer-id`, `--dry-run` (default True)

- [ ] **Step 1: Write failing test**

```python
# backend/tests/ike2/coverage_os/induction/test_pipeline.py
from core.knowledge.ike2.coverage_os.induction.pipeline import build_candidates


def test_build_candidates_composes_alias_and_role():
    entries = {
        "broccoli florets": {
            "normalized_key": "broccoli florets",
            "raw_inputs": ["broccoli florets"],
            "frequency": 5,
        }
    }
    ontology = {
        "ingredients": [
            {"canonical_name": "broccoli", "plant_origin": True},
            {"canonical_name": "vinegar", "plant_origin": True},
        ]
    }
    cands = build_candidates(
        entries=entries,
        ontology=ontology,
        alias_table={},
        tear_evidence={"vinegar": "culinary_keep"},
    )
    kinds = {c.proposal_kind for c in cands}
    assert "variant_alias" in kinds
    assert "ontology_role" in kinds
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_pipeline.py -v`  
Expected: FAIL

- [ ] **Step 3: Implement pipeline + script**

```python
# backend/core/knowledge/ike2/coverage_os/induction/pipeline.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from core.knowledge.ike2.coverage_os.induction.cluster import load_clusters
from core.knowledge.ike2.coverage_os.induction.propose_alias import propose_alias
from core.knowledge.ike2.coverage_os.induction.propose_role import (
    propose_role_backfill,
    propose_role_pattern_fill,
)
from core.knowledge.ike2.coverage_os.induction.types import InductionCandidate
from core.knowledge.ike2.coverage_os.neutralize import build_role_index
from core.knowledge.ike2.coverage_os.promote_ledger import candidate_key


def build_candidates(
    *,
    ontology: Mapping[str, Any],
    alias_table: Mapping[str, str],
    tear_evidence: Mapping[str, str] | None = None,
    log_path: Path | None = None,
    entries: Mapping[str, Any] | None = None,
    min_frequency: int = 1,
) -> list[InductionCandidate]:
    clusters = load_clusters(log_path, entries=entries, min_frequency=min_frequency)
    role_index = build_role_index(list(ontology.get("ingredients") or []))
    out: list[InductionCandidate] = []
    seen: set[str] = set()

    def _add(cand: InductionCandidate | None) -> None:
        if cand is None:
            return
        if cand.proposal_kind == "variant_alias":
            key = candidate_key(cand.raw, cand.canonical)
        else:
            key = candidate_key(cand.canonical or cand.raw, cand.canonical or cand.raw)
        if key in seen:
            return
        seen.add(key)
        out.append(cand)

    for item in clusters:
        _add(propose_alias(item, ontology=ontology, alias_table=alias_table))
        _add(propose_role_pattern_fill(item, ontology=ontology, role_index=role_index))
    for cand in propose_role_backfill(ontology=ontology, tear_evidence=tear_evidence or {}):
        _add(cand)
    out.sort(key=lambda c: (-c.frequency, c.raw))
    return out
```

`run_induction.py`: argparse like `seed_neutralize_roles.py`; default `--dry-run`; interactive accept calls `submit_induced` only (never `auto=True`).

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && python -m pytest tests/ike2/coverage_os/induction/test_pipeline.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/induction/pipeline.py \
  backend/scripts/run_induction.py \
  backend/tests/ike2/coverage_os/induction/test_pipeline.py
git commit -m "$(cat <<'EOF'
feat(coverage-os): induction pipeline compose and operator CLI

Dry-run default; submit only through force-human wrapper.
EOF
)"
```

---

### Task 8: Exit criteria — round-trip + matrix smoke (+ LCT-3)

**Files:**
- Create: `backend/tests/ike2/coverage_os/induction/test_phase2b_exit.py`
- Modify: none of live ontology/aliases unless via tmp_path

**Must prove:**

1. Alias + role round-trip: propose → submit accept → ledger promoted `auto=False` with induction provenance → demote retracts.
2. Matrix/smoke vs `fixtures/phase2a_matrix_baseline.json`: after applying **only** fixture-local promotions in tmp copies, **no new false Safes** (reuse Phase 2a baseline comparison helper if present; else assert baseline file still loads and `test_phase2a_matrix_baseline` still passes unchanged in the same pytest run).
3. Precision fixtures: synthetic 50-decision set meets A/A1/A2 helpers.
4. Structural: grep/ast already in Task 5; re-assert `submit` cannot auto.

- [ ] **Step 1: Write exit tests**

```python
# backend/tests/ike2/coverage_os/induction/test_phase2b_exit.py
def test_round_trip_alias_and_role_force_human(tmp_path):
    ...


def test_phase2a_baseline_fixture_still_present():
    p = Path("tests/ike2/coverage_os/fixtures/phase2a_matrix_baseline.json")
    assert p.exists()


def test_precision_helpers_ready_for_ops_window():
    ...
```

Also run existing baseline test:

Run: `cd backend && python -m pytest tests/ike2/coverage_os/test_phase2a_matrix_baseline.py tests/ike2/coverage_os/induction/ -v`

- [ ] **Step 2: Implement any missing glue so exit tests pass**

- [ ] **Step 3: LCT-3 review** — paste ledger row showing `payload.induction.safety_class` + precision filter on A1 set.

- [ ] **Step 4: Commit**

```bash
git commit -m "$(cat <<'EOF'
test(coverage-os): Phase 2b induction exit round-trip and precision fixtures

Locks force-human provenance and A/A1/A2 query readiness against Phase 2a baseline.
EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Hybrid mining frequency + miss_class | Task 2 |
| Unique closed-form alias or no proposal | Task 3 |
| Role pattern-fill + backfill | Task 4 |
| Structural force-human submit | Task 5 + LCT-2 |
| `safety_class` via deny_lists/hybrid_gate only | Task 1 + LCT-1 |
| Alias classifies on target row | Task 3 |
| Role classifies on filled row | Task 4 |
| Precision A/A1/A2 | Task 6 + Task 8 |
| Round-trip + no new false Safes plumbing | Task 8 |
| Facets deferred / no decide_promote changes | Global constraints |
| Single induction package | File map |

## Ops note (not a code task)

Live exit bar (first 50 human decisions ≥70% accept; A1 ≥90% with ≥10 dangerous; A2 zero safety demotes) is measured with:

```python
from core.knowledge.ike2.coverage_os.induction.precision import (
    iter_induced_decisions,
    measure_precision,
)
report = measure_precision(iter_induced_decisions(ledger), window=50)
```

after operators run `run_induction.py` against real unknown-log volume (accepts + rejects land in the same ledger). CI proves ledger→DecisionRecord wiring + threshold math; ops fills the window.
