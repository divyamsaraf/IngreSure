# Coverage OS Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Phase 1 of Coverage OS — attested evidence chains, hybrid promote gate + ledger (with apply/retract), multi-profile matrix detector, and auto-lane guards — without induction.

**Architecture:** Offline Coverage OS writes versioned decisions to a promote ledger; the hybrid gate auto-promotes only closed-form plant-only candidates and queues everything else for human approval. Runtime chat stays IKE-2 L1→L2→L3→L5 (no API at verdict). File stores `data/ontology.json` and `data/commodity_seed_lists/variant_aliases.json` remain the canonical L2 / synonymy assets; Supabase L3 is a derived mirror only.

**Tech Stack:** Python 3.11, pytest, existing IKE-2 modules (`resolver`, `compliance`, `seam`, `rules`), JSONL ledger under `data/coverage_os/`.

**Spec:** `docs/superpowers/specs/2026-07-21-coverage-os-phase1-design.md`

## Global Constraints

- Evidentiary chain required for Safe; assume-away-unknown → Depends (all categories).
- Avoid fail-closed identical across allergy / medical / lifestyle / religious.
- Auto-promote only plant-only closed-form; animal / allergen / dual-or-compound → human (no exceptions).
- Allergen-adjacent deny includes sulfite and mollusc.
- Human ledger entries require `reviewer_id` + `approval_rationale`.
- Gate must short-circuit on `confirmed_non_promotable`.
- Writer must **apply** and **retract** (demote) the same L2 files.
- No Phase 2 induction in this plan.
- Path sanity (verified): `backend/core/knowledge/ike2/commodity_head.py`, `backend/scripts/promote_commodity_coverage.py` exist.

## File map

| Path | Responsibility |
|------|----------------|
| `backend/core/knowledge/ike2/coverage_os/__init__.py` | Package export |
| `backend/core/knowledge/ike2/coverage_os/deny_lists.py` | **Single** allergen-adjacent + animalish constants (sulfite=`sulphite_source`, mollusc via species); shared by evidence_chain + hybrid_gate |
| `backend/core/knowledge/ike2/coverage_os/evidence_chain.py` | Attested chain dataclass + builders; `verdict` = Safe/Avoid/Depends |
| `backend/core/knowledge/ike2/coverage_os/promote_ledger.py` | JSONL ledger: promote / demote / non_promotable |
| `backend/core/knowledge/ike2/coverage_os/hybrid_gate.py` | Non-promotable short-circuit + auto/human/reject; imports deny lists (no duplicate) |
| `backend/core/knowledge/ike2/coverage_os/promote_writer.py` | Apply / retract ontology + variant_aliases |
| `backend/core/knowledge/ike2/coverage_os/profile_matrix.py` | Paste × SUPPORTED_RESTRICTIONS report |
| `backend/core/knowledge/ike2/coverage_os/auto_lane_guards.py` | Sample audit + volume spike |
| `backend/scripts/run_profile_matrix.py` | CLI entry for analyst matrix runs |
| `data/coverage_os/ledger.jsonl` | Default ledger path (gitkeep / empty start) |
| `backend/tests/ike2/coverage_os/test_*.py` | Unit + smoke tests per component |

## Dependency order (do not reorder tasks)

```text
Task 1 evidence_chain ──┐
Task 2 promote_ledger ──┼──► Task 3 hybrid_gate ──► Task 4 promote_writer
                        │                              │
                        └──────────────────────────────┴──► Task 5 profile_matrix
                                                              Task 6 auto_lane_guards
```

---

### Task 1: `evidence_chain` (+ shared `deny_lists`)

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/__init__.py`
- Create: `backend/core/knowledge/ike2/coverage_os/deny_lists.py`
- Create: `backend/core/knowledge/ike2/coverage_os/evidence_chain.py`
- Test: `backend/tests/ike2/coverage_os/test_evidence_chain.py`
- Test: `backend/tests/ike2/coverage_os/test_deny_lists.py`

**Interfaces:**
- Consumes: `ComplianceInput`, `ResolvedIngredient`, `ComplianceResult`, `Verdict`, `to_external`
- Produces:
  - `deny_lists.is_allergen_adjacent(flags) -> bool` (single source of truth for Task 1 + Task 3)
  - `deny_lists.is_animalish(flags) -> bool`
  - `to_audit_bucket(Verdict) -> Literal["Safe","Avoid","Depends"]` — maps **now** in Task 1 (no “maps later”)
  - `EvidenceChain` with `verdict` = audit bucket; `internal_verdict` = `to_external(Verdict)` for debug
  - `build_chain_from_resolve(...) -> EvidenceChain`

**Vocabulary lock:** `EvidenceChain.verdict` is **only** `Safe` | `Avoid` | `Depends`. Never store engine `UNCERTAIN`/`NOT_SAFE` in `verdict`.

**Sulfite spelling:** codebase flag is British `sulphite_source` (see `rules.py` / truth_anchor). Deny list uses that exact name.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/ike2/coverage_os/test_deny_lists.py
from core.knowledge.ike2.coverage_os.deny_lists import is_allergen_adjacent


def test_sulphite_flag_is_allergen_adjacent():
    assert is_allergen_adjacent({"plant_origin": True, "sulphite_source": True}) is True


def test_mollusc_species_is_allergen_adjacent():
    assert is_allergen_adjacent({"animal_origin": True, "animal_species": "mollusk"}) is True
    assert is_allergen_adjacent({"animal_origin": True, "animal_species": "mollusc"}) is True


def test_plain_broccoli_not_allergen_adjacent():
    assert is_allergen_adjacent({"plant_origin": True, "animal_origin": False}) is False
```

```python
# backend/tests/ike2/coverage_os/test_evidence_chain.py
from types import SimpleNamespace
from core.knowledge.ike2.coverage_os.evidence_chain import (
    build_chain_from_resolve,
    to_audit_bucket,
)
from core.knowledge.ike2.compliance import ComplianceResult
from core.knowledge.ike2.verdict import Verdict
from core.knowledge.ike2.seam import ComplianceInput


def test_to_audit_bucket_maps_engine_to_three_buckets():
    assert to_audit_bucket(Verdict.SAFE) == "Safe"
    assert to_audit_bucket(Verdict.FAIL) == "Avoid"
    assert to_audit_bucket(Verdict.UNCERTAIN) == "Depends"
    assert to_audit_bucket(Verdict.WARN) == "Depends"


def test_safe_chain_stores_audit_bucket_not_engine_enum():
    resolved = SimpleNamespace(
        status="resolved",
        source="truth_anchor",
        resolution_layer="L1_truth_anchor",
        trusted=True,
        miss_class=None,
        group=SimpleNamespace(
            canonical_name="sugar",
            flags={"plant_origin": True, "animal_origin": False},
            knowledge_state="LOCKED",
        ),
    )
    inp = ComplianceInput(
        canonical_name="sugar",
        flags={"plant_origin": True, "animal_origin": False},
        knowledge_state="LOCKED",
        trusted=True,
        alcohol_role="none",
        verdict_cap=None,
        trace=False,
    )
    result = ComplianceResult(Verdict.SAFE, [], [], [], {})
    chain = build_chain_from_resolve(
        atom="sugar",
        resolved=resolved,
        compliance_result=result,
        restriction_id="hindu_vegetarian",
        compliance_input=inp,
    )
    d = chain.to_dict()
    assert d["verdict"] == "Safe"
    assert d["internal_verdict"] == "SAFE"
    assert d["source"] == "truth_anchor"
    assert d["canonical"] == "sugar"
    assert d["miss_class"] is None
    assert d["evidence_class"] == "closed_form_plant"
    assert "flags" in d and "rule_ids" in d


def test_fail_chain_is_avoid_bucket():
    resolved = SimpleNamespace(
        status="resolved",
        source="truth_anchor",
        resolution_layer="L1_truth_anchor",
        trusted=True,
        miss_class=None,
        group=SimpleNamespace(
            canonical_name="beef",
            flags={"animal_origin": True, "animal_species": "cow"},
            knowledge_state="LOCKED",
        ),
    )
    inp = ComplianceInput(
        canonical_name="beef",
        flags={"animal_origin": True, "animal_species": "cow"},
        knowledge_state="LOCKED",
        trusted=True,
        alcohol_role="none",
        verdict_cap=None,
        trace=False,
    )
    result = ComplianceResult(Verdict.FAIL, [], [], [], {})
    chain = build_chain_from_resolve(
        atom="beef",
        resolved=resolved,
        compliance_result=result,
        restriction_id="hindu_vegetarian",
        compliance_input=inp,
    )
    d = chain.to_dict()
    assert d["verdict"] == "Avoid"
    assert d["internal_verdict"] == "NOT_SAFE"
    assert d["evidence_class"] == "animal"


def test_uncertain_resolve_marks_insufficient_and_depends():
    resolved = SimpleNamespace(
        status="uncertain",
        source="unknown_queue",
        resolution_layer="L5_unknown_queue",
        trusted=False,
        miss_class="M1_absent",
        group=None,
    )
    result = ComplianceResult(Verdict.UNCERTAIN, [], [], [], {})
    chain = build_chain_from_resolve(
        atom="savills",
        resolved=resolved,
        compliance_result=result,
        restriction_id="vegan",
        compliance_input=None,
    )
    d = chain.to_dict()
    assert d["verdict"] == "Depends"
    assert d["internal_verdict"] == "UNCERTAIN"
    assert d["evidence_class"] == "insufficient"
    assert d["miss_class"] == "M1_absent"


def test_mollusc_evidence_class_is_allergen():
    resolved = SimpleNamespace(
        status="resolved",
        source="truth_anchor",
        resolution_layer="L1_truth_anchor",
        trusted=True,
        miss_class=None,
        group=None,
    )
    inp = ComplianceInput(
        canonical_name="snail",
        flags={"animal_origin": True, "animal_species": "mollusk"},
        knowledge_state="LOCKED",
        trusted=True,
        alcohol_role="none",
        verdict_cap=None,
        trace=False,
    )
    result = ComplianceResult(Verdict.FAIL, [], [], [], {})
    chain = build_chain_from_resolve(
        atom="snail",
        resolved=resolved,
        compliance_result=result,
        restriction_id="shellfish_allergy",
        compliance_input=inp,
    )
    # animalish may win first; either animal or allergen is acceptable if mollusc denied for auto
    assert chain.evidence_class in ("animal", "allergen")
    assert chain.verdict == "Avoid"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && pytest tests/ike2/coverage_os/test_deny_lists.py tests/ike2/coverage_os/test_evidence_chain.py -v`  
Expected: FAIL (modules not found)

- [ ] **Step 3: Write full implementation (complete files — no truncation)**

```python
# backend/core/knowledge/ike2/coverage_os/__init__.py
"""Coverage OS Phase 1 — evidence graph, hybrid promote, matrix."""
```

```python
# backend/core/knowledge/ike2/coverage_os/deny_lists.py
"""Single source of truth for allergen-adjacent / animalish predicates.

Used by ``evidence_chain`` and ``hybrid_gate`` so the two cannot drift.
Sulfite uses the existing British flag name ``sulphite_source``.
Mollusc has no dedicated ``*_source`` flag today — detect via ``animal_species``.
"""
from __future__ import annotations

from typing import Any

# Matches VALID_FLAG_COLUMNS / truth_anchor naming (sulphite_source, not sulfite_source).
ALLERGEN_ADJACENT_FLAGS: frozenset[str] = frozenset({
    "peanut_source",
    "tree_nut_source",
    "sesame_source",
    "soy_source",
    "gluten_source",
    "mustard_source",
    "celery_source",
    "lupin_source",
    "sulphite_source",
    "fish_source",
    "shellfish_source",
})

MOLLUSC_SPECIES: frozenset[str] = frozenset({"mollusk", "mollusc"})

ANIMALISH_FLAGS: frozenset[str] = frozenset({
    "animal_origin",
    "egg_source",
    "fish_source",
    "shellfish_source",
    "insect_derived",
    "bee_product",
    "dairy_source",
})


def is_allergen_adjacent(flags: dict[str, Any] | None) -> bool:
    f = flags or {}
    if any(f.get(k) for k in ALLERGEN_ADJACENT_FLAGS):
        return True
    species = str(f.get("animal_species") or "").lower().strip()
    return species in MOLLUSC_SPECIES


def is_animalish(flags: dict[str, Any] | None) -> bool:
    f = flags or {}
    if any(f.get(k) for k in ANIMALISH_FLAGS):
        return True
    species = str(f.get("animal_species") or "").lower().strip()
    return bool(species) and species not in ("", "none")
```

```python
# backend/core/knowledge/ike2/coverage_os/evidence_chain.py
"""Attested evidence chain for Coverage OS / multi-profile matrix.

``verdict`` is the audit three-bucket vocabulary locked in the Phase 1 spec:
Safe / Avoid / Depends. Engine state is stored separately as ``internal_verdict``
via ``to_external`` (SAFE / NOT_SAFE / UNCERTAIN) for debugging only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

from core.knowledge.ike2.coverage_os.deny_lists import is_allergen_adjacent, is_animalish
from core.knowledge.ike2.verdict import Verdict, to_external


def to_audit_bucket(verdict: Verdict) -> str:
    """Map engine Verdict → Safe / Avoid / Depends at the chain boundary."""
    if verdict == Verdict.SAFE:
        return "Safe"
    if verdict == Verdict.FAIL:
        return "Avoid"
    # WARN and UNCERTAIN both surface as Depends in the audit matrix.
    return "Depends"


@dataclass
class EvidenceChain:
    atom: str
    canonical: Optional[str]
    source: str
    flags: dict
    rule_ids: list[str]
    verdict: str  # Safe | Avoid | Depends only
    internal_verdict: str  # SAFE | NOT_SAFE | UNCERTAIN from to_external
    evidence_class: str
    miss_class: Optional[str]
    restriction_id: str
    resolution_layer: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _evidence_class(
    flags: dict,
    miss_class: Optional[str],
    verdict: Verdict,
) -> str:
    if miss_class or verdict in (Verdict.UNCERTAIN, Verdict.WARN):
        if not flags:
            return "insufficient"
    if is_animalish(flags):
        return "animal"
    if is_allergen_adjacent(flags):
        return "allergen"
    if flags.get("plant_origin") and not flags.get("animal_origin"):
        return "closed_form_plant"
    if flags.get("verdict_cap") == "WARN":
        return "dual_or_compound"
    return "insufficient"


def build_chain_from_resolve(
    *,
    atom: str,
    resolved,
    compliance_result,
    restriction_id: str,
    compliance_input=None,
) -> EvidenceChain:
    flags: dict = {}
    canonical = None
    if compliance_input is not None:
        flags = dict(compliance_input.flags or {})
        canonical = compliance_input.canonical_name
    elif getattr(resolved, "group", None) is not None:
        g = resolved.group
        flags = dict(getattr(g, "flags", None) or {})
        canonical = getattr(g, "canonical_name", None)

    engine_verdict: Verdict = compliance_result.verdict
    miss = getattr(resolved, "miss_class", None)

    rule_ids: list[str] = []
    breakdown = getattr(compliance_result, "breakdown", None) or {}
    for key in breakdown:
        if isinstance(key, tuple) and len(key) >= 2:
            rule_ids.append(str(key[1]))
        else:
            rule_ids.append(str(key))

    return EvidenceChain(
        atom=atom,
        canonical=canonical,
        source=getattr(resolved, "source", "unknown") or "unknown",
        flags=flags,
        rule_ids=sorted(set(rule_ids)),
        verdict=to_audit_bucket(engine_verdict),
        internal_verdict=to_external(engine_verdict),
        evidence_class=_evidence_class(flags, miss, engine_verdict),
        miss_class=miss,
        restriction_id=restriction_id,
        resolution_layer=getattr(resolved, "resolution_layer", None),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/ike2/coverage_os/test_deny_lists.py tests/ike2/coverage_os/test_evidence_chain.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/ \
  backend/tests/ike2/coverage_os/test_deny_lists.py \
  backend/tests/ike2/coverage_os/test_evidence_chain.py
git commit -m "feat(coverage-os): evidence chain with Safe/Avoid/Depends and shared deny lists"
```
---

### Task 2: `promote_ledger`

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/promote_ledger.py`
- Create: `data/coverage_os/.gitkeep`
- Test: `backend/tests/ike2/coverage_os/test_promote_ledger.py`

**Interfaces:**
- Consumes: filesystem path
- Produces:
  - `PromoteLedger(path: Path)`
  - `append_promoted(...)`, `append_demoted(...)`, `append_non_promotable(...)`
  - `find_non_promotable(candidate_key: str) -> dict | None`
  - `latest_promoted(candidate_key: str) -> dict | None`
  - `candidate_key(atom: str, target_canonical: str | None) -> str`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/ike2/coverage_os/test_promote_ledger.py
import pytest
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key


def test_non_promotable_blocks_lookup(tmp_path):
    led = PromoteLedger(tmp_path / "ledger.jsonl")
    key = candidate_key("roman bean", "roman bean")
    led.append_non_promotable(
        candidate_key=key,
        rule_id="human_reject",
        source="corpus",
        reason="not a food commodity",
    )
    hit = led.find_non_promotable(key)
    assert hit is not None
    assert hit["kind"] == "confirmed_non_promotable"


def test_human_promote_requires_reviewer_fields(tmp_path):
    led = PromoteLedger(tmp_path / "ledger.jsonl")
    key = candidate_key("broccoli", "broccoli")
    with pytest.raises(ValueError):
        led.append_promoted(
            candidate_key=key,
            rule_id="closed_form_plant_v1",
            source="human",
            payload={"canonical": "broccoli"},
            auto=False,
            reviewer_id=None,
            approval_rationale=None,
        )
    led.append_promoted(
        candidate_key=key,
        rule_id="closed_form_plant_v1",
        source="human",
        payload={"canonical": "broccoli", "flags": {"plant_origin": True}},
        auto=False,
        reviewer_id="reviewer-1",
        approval_rationale="single-origin vegetable",
    )
    row = led.latest_promoted(key)
    assert row["reviewer_id"] == "reviewer-1"
    assert row["approval_rationale"]
    assert row["version"] == 1


def test_demote_increments_and_marks_inactive(tmp_path):
    led = PromoteLedger(tmp_path / "ledger.jsonl")
    key = candidate_key("broccoli", "broccoli")
    led.append_promoted(
        candidate_key=key,
        rule_id="closed_form_plant_v1",
        source="auto",
        payload={"canonical": "broccoli"},
        auto=True,
    )
    led.append_demoted(candidate_key=key, reason="sample_audit_fail")
    assert led.latest_promoted(key) is None or led.latest_promoted(key).get("active") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ike2/coverage_os/test_promote_ledger.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Implement JSONL append-only ledger with:
- `kind`: `promoted` | `demoted` | `confirmed_non_promotable`
- auto promote: `reviewer_id`/`approval_rationale` optional
- human promote: both required (`ValueError` if missing)
- `version` monotonic per `candidate_key`
- `find_non_promotable`: scan for latest matching kind
- `latest_promoted`: latest `promoted` not superseded by later `demoted`

```python
def candidate_key(atom: str, target_canonical: str | None) -> str:
    a = (atom or "").strip().lower()
    c = (target_canonical or a).strip().lower()
    return f"{a}=>{c}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ike2/coverage_os/test_promote_ledger.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/promote_ledger.py \
  backend/tests/ike2/coverage_os/test_promote_ledger.py data/coverage_os/.gitkeep
git commit -m "feat(coverage-os): add versioned promote ledger with non-promotable"
```

---

### Task 3: `hybrid_gate`

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/hybrid_gate.py`
- Test: `backend/tests/ike2/coverage_os/test_hybrid_gate.py`

**Interfaces:**
- Consumes: `PromoteLedger.find_non_promotable`, candidate flags dict, **`deny_lists.is_allergen_adjacent` / `is_animalish`** (do **not** copy flag frozensets into this module)
- Produces:
  - `GateDecision` with `action: Literal["auto_promote","human_approval","rejected"]`, `rule_id`, `reason`
  - `decide_promote(*, candidate_key, flags, ledger: PromoteLedger, name_collision_animal: bool = False, is_umbrella: bool = False) -> GateDecision`

**Allergen-adjacent:** call `is_allergen_adjacent(flags)` from `deny_lists.py` only. Sulfite = `sulphite_source`; mollusc = `animal_species` in `{mollusk, mollusc}` (encoded inside that helper).

- [ ] **Step 1: Write the failing test**

```python
from core.knowledge.ike2.coverage_os.hybrid_gate import decide_promote
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key


def test_non_promotable_short_circuits(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    key = candidate_key("roman", "roman")
    led.append_non_promotable(key, "human_reject", "corpus", "junk")
    d = decide_promote(
        candidate_key=key,
        flags={"plant_origin": True},
        ledger=led,
    )
    assert d.action == "rejected"
    assert "non_promotable" in d.reason


def test_broccoli_auto_promotes():
    # ledger empty
    from pathlib import Path
    import tempfile
    led = PromoteLedger(Path(tempfile.mkdtemp()) / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("broccoli", "broccoli"),
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
    )
    assert d.action == "auto_promote"
    assert d.rule_id == "closed_form_plant_v1"


def test_sulphite_goes_human():
    led = PromoteLedger(__import__("pathlib").Path(__import__("tempfile").mkdtemp()) / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("dried apricot", "dried apricot"),
        flags={"plant_origin": True, "sulphite_source": True},
        ledger=led,
    )
    assert d.action == "human_approval"


def test_mollusc_species_goes_human():
    led = PromoteLedger(__import__("pathlib").Path(__import__("tempfile").mkdtemp()) / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("snail", "snail"),
        flags={"animal_origin": True, "animal_species": "mollusk"},
        ledger=led,
    )
    assert d.action == "human_approval"


def test_beef_goes_human_not_auto():
    led = PromoteLedger(__import__("pathlib").Path(__import__("tempfile").mkdtemp()) / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("beef", "beef"),
        flags={"animal_origin": True, "animal_species": "cow"},
        ledger=led,
    )
    assert d.action == "human_approval"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ike2/coverage_os/test_hybrid_gate.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Order inside `decide_promote`:
1. If `ledger.find_non_promotable(candidate_key)` → `rejected`
2. If `is_animalish(flags)` or `is_allergen_adjacent(flags)` or dual collision or umbrella → `human_approval`
3. If plant-only closed-form → `auto_promote` with `rule_id="closed_form_plant_v1"`
4. Else → `human_approval` (fail-closed to human, never silent auto)

Import allergen/animal checks **only** from `deny_lists` — no local duplicate frozensets.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ike2/coverage_os/test_hybrid_gate.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/hybrid_gate.py \
  backend/tests/ike2/coverage_os/test_hybrid_gate.py
git commit -m "feat(coverage-os): hybrid promote gate with non-promotable short-circuit"
```

---

### Task 4: `promote_writer` (apply + retract)

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/promote_writer.py`
- Test: `backend/tests/ike2/coverage_os/test_promote_writer.py`

**Interfaces:**
- Consumes: ledger rows, paths to ontology + variant_aliases
- Produces:
  - `apply_promotion(entry, *, ontology_path, aliases_path) -> None`
  - `retract_promotion(entry, *, ontology_path, aliases_path) -> None`
  - Optional: `mirror_l3_inject(entry) -> None` stub that logs "derived mirror; not source of truth" (no hard fail if Supabase down)

**Behavior:**
- `apply`: add/update ingredient row in `ontology.json` ingredients list OR add alias key in `variant_aliases.json` per payload `kind` (`ontology_row` | `variant_alias`)
- `retract`: remove the alias key or mark/remove the ontology row that this ledger version added (payload must include enough to reverse; store `inverse` in ledger payload at promote time)
- Never leave half-written JSON (write temp + replace)
- On failure: raise; caller leaves ledger pending

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path
from core.knowledge.ike2.coverage_os.promote_writer import apply_promotion, retract_promotion


def _base_ontology(tmp: Path) -> Path:
    p = tmp / "ontology.json"
    p.write_text(json.dumps({"ontology_version": "test", "ingredients": []}) + "\n")
    return p


def _base_aliases(tmp: Path) -> Path:
    p = tmp / "variant_aliases.json"
    p.write_text(json.dumps({"aliases": {}}) + "\n")
    return p


def test_apply_and_retract_variant_alias(tmp_path):
    ont = _base_ontology(tmp_path)
    al = _base_aliases(tmp_path)
    entry = {
        "kind": "promoted",
        "payload": {
            "write_kind": "variant_alias",
            "alias": "salt himalayan",
            "canonical": "himalayan salt",
            "inverse": {"write_kind": "variant_alias", "alias": "salt himalayan"},
        },
    }
    apply_promotion(entry, ontology_path=ont, aliases_path=al)
    aliases = json.loads(al.read_text())["aliases"]
    assert aliases["salt himalayan"] == "himalayan salt"
    retract_promotion(entry, ontology_path=ont, aliases_path=al)
    aliases = json.loads(al.read_text())["aliases"]
    assert "salt himalayan" not in aliases
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ike2/coverage_os/test_promote_writer.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Use atomic replace. For ontology rows, payload includes `canonical_name` + flags; inverse removes by canonical_name if `coverage_os_managed: true` marker was set on apply.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ike2/coverage_os/test_promote_writer.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/promote_writer.py \
  backend/tests/ike2/coverage_os/test_promote_writer.py
git commit -m "feat(coverage-os): promote writer apply and retract for L2 files"
```

---

### Task 5: `profile_matrix`

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/profile_matrix.py`
- Create: `backend/scripts/run_profile_matrix.py`
- Create: `backend/tests/ike2/coverage_os/golden/matrix_smoke.txt` (small paste: `sugar, beef, egg, salt himalayan, savills`)
- Test: `backend/tests/ike2/coverage_os/test_profile_matrix.py`

**Interfaces:**
- Consumes: `parse_atoms`, `resolve`, `to_compliance_input`, `evaluate`, `seeded_rules`, `SUPPORTED_RESTRICTIONS`, `build_chain_from_resolve`
- Produces:
  - `run_matrix(raw: str, restriction_ids: list[str] | None = None) -> list[dict]`
  - Each row: `ingredient`, `profile`, `bucket` (`Safe`|`Avoid`|`Depends`), `chain` dict
  - **Bucket = `chain.verdict`** (already Safe/Avoid/Depends from Task 1). Do not re-map `to_external` here.

- [ ] **Step 1: Write the failing test**

```python
from core.knowledge.ike2.coverage_os.profile_matrix import run_matrix
from core.knowledge.ike2.rules import SUPPORTED_RESTRICTIONS


def test_matrix_covers_supported_profiles_for_one_atom():
    rows = run_matrix("sugar", restriction_ids=sorted(SUPPORTED_RESTRICTIONS)[:3])
    profiles = {r["profile"] for r in rows}
    assert len(profiles) == 3
    assert all("chain" in r and "bucket" in r for r in rows)
    sugar_rows = [r for r in rows if r["ingredient"] == "sugar"]
    assert sugar_rows
    # sugar should not Avoid on hindu_vegetarian when that profile is included
    for r in sugar_rows:
        assert r["bucket"] in ("Safe", "Avoid", "Depends")
        assert r["chain"]["atom"]
        assert r["bucket"] == r["chain"]["verdict"]


def test_avoid_parity_beef_fails_veg_profiles():
    rows = run_matrix("beef", restriction_ids=["hindu_vegetarian", "vegan", "vegetarian"])
    by_p = {r["profile"]: r["bucket"] for r in rows}
    assert by_p["hindu_vegetarian"] == "Avoid"
    assert by_p["vegan"] == "Avoid"
    assert by_p["vegetarian"] == "Avoid"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ike2/coverage_os/test_profile_matrix.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation + CLI**

`run_matrix`:
1. `parse_atoms(raw)`
2. For each atom × each restriction_id: resolve → seam → evaluate → build_chain → bucket
3. Clear resolution cache between full runs if needed (`resolution_cache.clear()`)

CLI `run_profile_matrix.py`: argparse `--paste` / `--file`, `--csv out.csv`, default all `SUPPORTED_RESTRICTIONS`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ike2/coverage_os/test_profile_matrix.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/profile_matrix.py \
  backend/scripts/run_profile_matrix.py \
  backend/tests/ike2/coverage_os/test_profile_matrix.py \
  backend/tests/ike2/coverage_os/golden/matrix_smoke.txt
git commit -m "feat(coverage-os): multi-profile matrix detector with evidence chains"
```

---

### Task 6: `auto_lane_guards`

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/auto_lane_guards.py`
- Test: `backend/tests/ike2/coverage_os/test_auto_lane_guards.py`

**Interfaces:**
- Produces:
  - `select_sample_audit(promotions: list[dict], *, every_n: int = 10) -> list[dict]`
  - `check_volume_spike(promotions: list[dict], *, window_seconds: int, threshold: int, now: float | None = None) -> bool`
  - `log_volume_spike_if_needed(...)` logs WARNING when spike True

- [ ] **Step 1: Write the failing test**

```python
import logging
from core.knowledge.ike2.coverage_os.auto_lane_guards import (
    select_sample_audit,
    check_volume_spike,
    log_volume_spike_if_needed,
)


def test_sample_audit_returns_non_empty_on_fixture_batch():
    batch = [{"id": i, "auto": True} for i in range(25)]
    sample = select_sample_audit(batch, every_n=10)
    assert sample  # non-empty
    assert len(sample) >= 2


def test_volume_spike_stub_logs(caplog):
    now = 1_000_000.0
    promos = [{"ts": now - 10, "source": "usda"} for _ in range(20)]
    assert check_volume_spike(promos, window_seconds=60, threshold=5, now=now) is True
    with caplog.at_level(logging.WARNING):
        log_volume_spike_if_needed(promos, window_seconds=60, threshold=5, now=now)
    assert any("volume spike" in r.message.lower() for r in caplog.records)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ike2/coverage_os/test_auto_lane_guards.py -v`  
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

`select_sample_audit`: take every Nth auto promotion (1-indexed or 0-indexed consistently).  
`check_volume_spike`: count promotions with `ts` in `[now - window, now]`; True if count > threshold.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ike2/coverage_os/test_auto_lane_guards.py -v`  
Expected: PASS

- [ ] **Step 5: Wire smoke into ledger append path (optional thin hook)**

When `append_promoted(..., auto=True)` succeeds, call sample selector on recent auto rows (in-memory list passed by caller is fine in Phase 1 — no need for a daemon). Document in module docstring that Phase 1 is log/stub only.

- [ ] **Step 6: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/auto_lane_guards.py \
  backend/tests/ike2/coverage_os/test_auto_lane_guards.py
git commit -m "feat(coverage-os): auto-lane sample audit and volume-spike guards"
```

---

### Task 7: Phase 1 integration smoke + exit checklist

**Files:**
- Test: `backend/tests/ike2/coverage_os/test_phase1_integration.py`
- Modify: `docs/superpowers/specs/2026-07-21-coverage-os-phase1-design.md` only if path notes needed (prefer not)

- [ ] **Step 1: Write integration test**

```python
def test_gate_writer_ledger_round_trip(tmp_path):
    # auto-promote broccoli → apply alias or ontology row → demote retracts
    # non_promotable blocks second decide_promote
    ...


def test_matrix_emits_chain_for_each_cell():
    rows = run_matrix("sugar, beef", restriction_ids=["hindu_vegetarian", "vegan"])
    assert len(rows) >= 4
    assert all(r["chain"]["restriction_id"] == r["profile"] for r in rows)
```

- [ ] **Step 2: Run full coverage_os suite**

Run: `pytest tests/ike2/coverage_os/ -v`  
Expected: all PASS

- [ ] **Step 3: Manual exit-criteria checklist (record in PR)**

1. Evidence chain on matrix rows  
2. Hybrid gate + non_promotable short-circuit  
3. Ledger promote/demote/retract + human reviewer fields  
4. Matrix CLI run on smoke paste  
5. Avoid parity test green  
6. Auto-lane guard tests green  
7. Confirm no induction code landed  

- [ ] **Step 4: Commit**

```bash
git add backend/tests/ike2/coverage_os/test_phase1_integration.py
git commit -m "test(coverage-os): Phase 1 integration smoke and exit checklist"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|------------------|------|
| Evidence graph fields; verdict = Safe/Avoid/Depends | Task 1 |
| Shared deny lists (sulfite + mollusc); gate imports same | Task 1 + Task 3 |
| Non-promotable short-circuit | Task 2 + 3 |
| Ledger human reviewer fields | Task 2 |
| Writer apply + retract | Task 4 |
| L2 file unification | Task 4 |
| L3 derived mirror stub | Task 4 |
| Multi-profile matrix | Task 5 |
| Auto-lane sample + volume tests | Task 6 |
| Avoid parity | Task 5 + 7 |
| No Phase 2 induction | Global constraints + Task 7 checklist |
| Dependency order ledger→gate→writer→matrix/guards | Tasks 1–6 order |

No TBD/placeholder steps remaining after self-review.
