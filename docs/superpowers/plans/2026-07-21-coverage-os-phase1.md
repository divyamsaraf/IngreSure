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
| `backend/core/knowledge/ike2/coverage_os/evidence_chain.py` | Attested chain; `verdict` = Safe/Avoid/Depends; `rule_ids` from `matched_rules` filtered to atom |
| `backend/core/knowledge/ike2/compliance.py` | Additive: `matched_rules` list on evaluate result |
| `backend/core/knowledge/ike2/rules.py` | Additive: `rule_identity(rule)` |
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

### Task 1: `evidence_chain` (+ shared `deny_lists` + compliance `matched_rules`)

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/__init__.py`
- Create: `backend/core/knowledge/ike2/coverage_os/deny_lists.py`
- Create: `backend/core/knowledge/ike2/coverage_os/evidence_chain.py`
- Modify: `backend/core/knowledge/ike2/compliance.py` — add `matched_rules` on `ComplianceResult` / `evaluate`
- Modify: `backend/core/knowledge/ike2/rules.py` — add `rule_identity(rule) -> str` helper
- Test: `backend/tests/ike2/coverage_os/test_deny_lists.py`
- Test: `backend/tests/ike2/coverage_os/test_evidence_chain.py`
- Test: `backend/tests/ike2/test_compliance_matched_rules.py` (or fold into evidence_chain tests)

**Interfaces:**
- Consumes: `ComplianceInput`, `ResolvedIngredient`, `ComplianceResult` (with **`matched_rules`**), `Verdict`, `to_external`
- Produces:
  - `deny_lists.is_allergen_adjacent(flags) -> bool` / `is_animalish(flags) -> bool`
  - `rules.rule_identity(rule) -> str` e.g. `hindu_vegetarian:meat_fish_derived` or `hindu_vegetarian:egg_source`
  - `to_audit_bucket(Verdict) -> Literal["Safe","Avoid","Depends"]`
  - `EvidenceChain.verdict` = audit bucket; `internal_verdict` = `to_external(...)`
  - `EvidenceChain.rule_ids` = **fired rule identities for this atom only**
  - `build_chain_from_resolve(...) -> EvidenceChain`

**Why `breakdown` is not enough (named blind spot):**  
`breakdown[(canonical, restriction_id)] = verdict` only stores the worst verdict per restriction. It has **no rule identity**. Empty `breakdown={}` in prior draft tests hid a buggy loop that stuffed `restriction_id` into `rule_ids`. Task 1 must not mark done until a **non-empty multi-ingredient** `matched_rules` test passes.

**Vocabulary lock:** `verdict` is only `Safe` | `Avoid` | `Depends`.

**Verdict grain lock (roundtable 2026-07-21):**  
`EvidenceChain.verdict` MUST come from **`breakdown[(canonical, restriction_id)]`** (fallback: worst triggered `matched_rules` row for that atom+restriction). **Never** use aggregate `ComplianceResult.verdict` for a per-atom chain. Missing breakdown key → Depends/`UNCERTAIN` (fail-closed), do not inherit paste-level FAIL.  
Required regression: `evaluate([beef, sugar], …)` → sugar×`hindu_vegetarian` is **Safe**, beef×`hindu_vegetarian` is **Avoid**.

**Unit-test grain note:** Hand-built `ComplianceResult` fixtures for Safe/Avoid chains **must** include a per-cell `breakdown[(canonical, restriction)]` entry (or triggered `matched_rules`); empty `breakdown={}` with only aggregate `Verdict.SAFE`/`FAIL` is invalid under this lock and must not be used.

**Sulfite spelling:** flag name is `sulphite_source`.

**evidence_class order:** check **`is_allergen_adjacent` before `is_animalish`** so fish/shellfish label as `allergen` (audit trail), not only `animal`. Both still human-gate in Task 3.

- [x] **Step 1: Write the failing tests**

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
from core.knowledge.ike2.rules import seeded_rules, rule_identity
from core.knowledge.ike2.compliance import evaluate


def test_to_audit_bucket_maps_engine_to_three_buckets():
    assert to_audit_bucket(Verdict.SAFE) == "Safe"
    assert to_audit_bucket(Verdict.FAIL) == "Avoid"
    assert to_audit_bucket(Verdict.UNCERTAIN) == "Depends"
    assert to_audit_bucket(Verdict.WARN) == "Depends"


def test_safe_chain_stores_audit_bucket_not_engine_enum():
    resolved = SimpleNamespace(
        status="resolved", source="truth_anchor",
        resolution_layer="L1_truth_anchor", trusted=True, miss_class=None, group=None,
    )
    inp = ComplianceInput(
        canonical_name="sugar",
        flags={"plant_origin": True, "animal_origin": False},
        knowledge_state="LOCKED", trusted=True,
        alcohol_role="none", verdict_cap=None, trace=False,
    )
    result = ComplianceResult(
        Verdict.SAFE, [], [], [],
        {("sugar", "hindu_vegetarian"): Verdict.SAFE},
        matched_rules=[],
    )
    chain = build_chain_from_resolve(
        atom="sugar", resolved=resolved, compliance_result=result,
        restriction_id="hindu_vegetarian", compliance_input=inp,
    )
    d = chain.to_dict()
    assert d["verdict"] == "Safe"
    assert d["internal_verdict"] == "SAFE"
    assert d["evidence_class"] == "closed_form_plant"
    assert d["rule_ids"] == []


def test_rule_ids_are_rule_identity_filtered_to_this_ingredient():
    """Non-empty multi-ingredient matched_rules — must not leak other atoms' rules."""
    beef = ComplianceInput(
        canonical_name="beef",
        flags={"animal_origin": True, "animal_species": "cow"},
        knowledge_state="LOCKED", trusted=True,
        alcohol_role="none", verdict_cap=None, trace=False,
    )
    sugar = ComplianceInput(
        canonical_name="sugar",
        flags={"plant_origin": True, "animal_origin": False},
        knowledge_state="LOCKED", trusted=True,
        alcohol_role="none", verdict_cap=None, trace=False,
    )
    profile = SimpleNamespace(restrictions={"hindu_vegetarian": "preference", "vegan": "preference"})
    result = evaluate([beef, sugar], profile, seeded_rules())
    assert getattr(result, "matched_rules", None), "evaluate must populate matched_rules"
    # Beef under hindu_vegetarian should include meat_fish_derived (or animal) rule id
    beef_ids = [
        m["rule_id"] for m in result.matched_rules
        if m["canonical"] == "beef" and m["restriction"] == "hindu_vegetarian"
    ]
    assert beef_ids
    assert all("hindu_vegetarian" in rid for rid in beef_ids)
    assert any("meat_fish" in rid or "animal" in rid or "species" in rid for rid in beef_ids)
    # Sugar must not appear as a FAIL trigger for hindu meat rule
    sugar_hindu = [
        m for m in result.matched_rules
        if m["canonical"] == "sugar" and m["restriction"] == "hindu_vegetarian" and m.get("triggered")
    ]
    # Build chain for beef only — must not include vegan rules fired only on sugar context
    resolved = SimpleNamespace(
        status="resolved", source="ontology", resolution_layer="L2_local_ontology",
        trusted=True, miss_class=None, group=None,
    )
    chain = build_chain_from_resolve(
        atom="beef", resolved=resolved, compliance_result=result,
        restriction_id="hindu_vegetarian", compliance_input=beef,
    )
    assert chain.verdict == "Avoid"
    assert chain.rule_ids
    assert all(rid.startswith("hindu_vegetarian:") for rid in chain.rule_ids)
    assert not any(rid.startswith("vegan:") for rid in chain.rule_ids)
    # No bare restriction ids without a rule qualifier
    assert "hindu_vegetarian" not in chain.rule_ids

    # Same evaluate result: sugar must NOT inherit Avoid from beef (verdict grain)
    sugar_chain = build_chain_from_resolve(
        atom="sugar", resolved=resolved, compliance_result=result,
        restriction_id="hindu_vegetarian", compliance_input=sugar,
    )
    assert sugar_chain.verdict == "Safe"
    assert sugar_chain.rule_ids == []


def test_fish_evidence_class_is_allergen_not_only_animal():
    resolved = SimpleNamespace(
        status="resolved", source="truth_anchor",
        resolution_layer="L1_truth_anchor", trusted=True, miss_class=None, group=None,
    )
    inp = ComplianceInput(
        canonical_name="salmon",
        flags={"animal_origin": True, "fish_source": True, "animal_species": "fish"},
        knowledge_state="LOCKED", trusted=True,
        alcohol_role="none", verdict_cap=None, trace=False,
    )
    result = ComplianceResult(
        Verdict.FAIL, ["salmon"], [], [],
        {("salmon", "fish_allergy"): Verdict.FAIL},
        matched_rules=[],
    )
    chain = build_chain_from_resolve(
        atom="salmon", resolved=resolved, compliance_result=result,
        restriction_id="fish_allergy", compliance_input=inp,
    )
    assert chain.evidence_class == "allergen"
    assert chain.verdict == "Avoid"


def test_uncertain_resolve_marks_insufficient_and_depends():
    resolved = SimpleNamespace(
        status="uncertain", source="unknown_queue",
        resolution_layer="L5_unknown_queue", trusted=False,
        miss_class="M1_absent", group=None,
    )
    result = ComplianceResult(Verdict.UNCERTAIN, [], [], [], {}, matched_rules=[])
    chain = build_chain_from_resolve(
        atom="savills", resolved=resolved, compliance_result=result,
        restriction_id="vegan", compliance_input=None,
    )
    d = chain.to_dict()
    assert d["verdict"] == "Depends"
    assert d["internal_verdict"] == "UNCERTAIN"
    assert d["evidence_class"] == "insufficient"
    assert d["miss_class"] == "M1_absent"


def test_depends_from_uncertainty_can_have_empty_rule_ids():
    """KS/uncertainty Depends is not a trigger — rule_ids may be empty."""
    resolved = SimpleNamespace(
        status="resolved", source="ontology",
        resolution_layer="L2_local_ontology", trusted=True,
        miss_class=None, group=None,
    )
    inp = ComplianceInput(
        canonical_name="mystery plant",
        flags={"plant_origin": True, "animal_origin": False},
        knowledge_state="DISCOVERED", trusted=True,
        alcohol_role="none", verdict_cap=None, trace=False,
    )
    # Cell verdict WARN/UNCERTAIN via breakdown only — no triggered rules
    result = ComplianceResult(
        Verdict.WARN, [], [], [],
        {("mystery plant", "vegan"): Verdict.WARN},
        matched_rules=[],
    )
    chain = build_chain_from_resolve(
        atom="mystery plant", resolved=resolved, compliance_result=result,
        restriction_id="vegan", compliance_input=inp,
    )
    assert chain.verdict == "Depends"
    assert chain.rule_ids == []
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd backend && source venv/bin/activate && pytest tests/ike2/coverage_os/test_deny_lists.py tests/ike2/coverage_os/test_evidence_chain.py -v`  
Expected: FAIL (modules / `matched_rules` / `rule_identity` missing)

- [x] **Step 3: Implement `rule_identity` + `matched_rules` in compliance**

In `rules.py`:

```python
def rule_identity(rule) -> str:
    """Stable id for audit: restriction + kind/flag — not bare restriction name."""
    restriction = getattr(rule, "restriction", "") or ""
    kind = getattr(rule, "kind", "flag") or "flag"
    trigger = getattr(rule, "trigger_flag", None)
    if kind == "flag" and trigger:
        return f"{restriction}:{trigger}"
    if kind in ("meat_fish_derived", "meat_land_derived", "alcohol"):
        return f"{restriction}:{kind}"
    match_value = getattr(rule, "match_value", None)
    if kind in ("species_match", "species_in_list", "alcohol_content") and match_value is not None:
        if isinstance(match_value, (list, tuple)):
            mv = ",".join(str(x) for x in match_value)
        else:
            mv = str(match_value)
        return f"{restriction}:{kind}:{mv}"
    return f"{restriction}:{kind}"
```

In `compliance.py` `ComplianceResult.__init__`, add `matched_rules=None` and assign **`self.matched_rules = list(matched_rules or [])`** (never a mutable default shared across instances).
In `evaluate`, when a rule is evaluated, append:

```python
matched_rules.append({
    "canonical": name,
    "restriction": rule.restriction,
    "rule_id": rule_identity(rule),
    "triggered": bool(triggered),
    "verdict": verdict,  # engine Verdict
})
```

Only **triggered** rows need to feed `EvidenceChain.rule_ids` (filter `triggered is True`). Keep all rows optional for debugging; chain builder filters.

Backward compatible: existing callers that ignore the new kwarg still work if defaulted.

- [x] **Step 4: Implement deny_lists + evidence_chain (complete)**

```python
# backend/core/knowledge/ike2/coverage_os/deny_lists.py
from __future__ import annotations
from typing import Any

ALLERGEN_ADJACENT_FLAGS: frozenset[str] = frozenset({
    "peanut_source", "tree_nut_source", "sesame_source", "soy_source",
    "gluten_source", "mustard_source", "celery_source", "lupin_source",
    "sulphite_source", "fish_source", "shellfish_source",
})
MOLLUSC_SPECIES: frozenset[str] = frozenset({"mollusk", "mollusc"})
ANIMALISH_FLAGS: frozenset[str] = frozenset({
    "animal_origin", "egg_source", "fish_source", "shellfish_source",
    "insect_derived", "bee_product", "dairy_source",
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
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any, Optional

from core.knowledge.ike2.coverage_os.deny_lists import is_allergen_adjacent, is_animalish
from core.knowledge.ike2.verdict import Verdict, to_external


def to_audit_bucket(verdict: Verdict) -> str:
    if verdict == Verdict.SAFE:
        return "Safe"
    if verdict == Verdict.FAIL:
        return "Avoid"
    return "Depends"


@dataclass
class EvidenceChain:
    atom: str
    canonical: Optional[str]
    source: str
    flags: dict
    rule_ids: list[str]
    verdict: str
    internal_verdict: str
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
    *,
    verdict_cap: Optional[str] = None,
) -> str:
    if miss_class or verdict in (Verdict.UNCERTAIN, Verdict.WARN):
        if not flags:
            return "insufficient"
    # Compound/umbrella before plant — else spices audit as closed_form_plant.
    cap = verdict_cap or flags.get("verdict_cap")
    if cap == "WARN":
        return "dual_or_compound"
    # Allergen-adjacent BEFORE animalish so fish/shellfish audit as allergen.
    if is_allergen_adjacent(flags):
        return "allergen"
    if is_animalish(flags):
        return "animal"
    if flags.get("plant_origin") and not flags.get("animal_origin"):
        return "closed_form_plant"
    return "insufficient"


def _rule_ids_for_atom(compliance_result, *, canonical: Optional[str], atom: str, restriction_id: str) -> list[str]:
    """Pull real rule identities; filter to this ingredient + this restriction."""
    names = {n for n in (canonical, atom) if n}
    names |= {n.lower() for n in names}
    out: list[str] = []
    for row in getattr(compliance_result, "matched_rules", None) or []:
        if not row.get("triggered"):
            continue
        if row.get("restriction") != restriction_id:
            continue
        c = (row.get("canonical") or "").strip()
        if c not in names and c.lower() not in names:
            continue
        rid = row.get("rule_id")
        if rid and rid not in out:
            out.append(rid)
    return out


def _engine_verdict_for_cell(compliance_result, *, canonical: Optional[str], atom: str, restriction_id: str) -> Verdict:
    """Per-(ingredient, restriction) verdict — never paste-level aggregate."""
    breakdown = getattr(compliance_result, "breakdown", None) or {}
    for name in (canonical, atom):
        if not name:
            continue
        if (name, restriction_id) in breakdown:
            return breakdown[(name, restriction_id)]
        # case-fold fallback
        for (c, r), v in breakdown.items():
            if r == restriction_id and str(c).lower() == str(name).lower():
                return v
    # Fallback: worst triggered matched_rules row for this cell
    worst = None
    names = {n for n in (canonical, atom) if n}
    names |= {n.lower() for n in names}
    for row in getattr(compliance_result, "matched_rules", None) or []:
        if not row.get("triggered"):
            continue
        if row.get("restriction") != restriction_id:
            continue
        c = (row.get("canonical") or "").strip()
        if c not in names and c.lower() not in names:
            continue
        v = row.get("verdict")
        if v is None:
            continue
        worst = v if worst is None else max(worst, v)
    if worst is not None:
        return worst
    return Verdict.UNCERTAIN


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

    engine_verdict = _engine_verdict_for_cell(
        compliance_result,
        canonical=canonical,
        atom=atom,
        restriction_id=restriction_id,
    )
    miss = getattr(resolved, "miss_class", None)
    verdict_cap = None
    if compliance_input is not None:
        verdict_cap = getattr(compliance_input, "verdict_cap", None)

    return EvidenceChain(
        atom=atom,
        canonical=canonical,
        source=getattr(resolved, "source", "unknown") or "unknown",
        flags=flags,
        rule_ids=_rule_ids_for_atom(
            compliance_result,
            canonical=canonical,
            atom=atom,
            restriction_id=restriction_id,
        ),
        verdict=to_audit_bucket(engine_verdict),
        internal_verdict=to_external(engine_verdict),
        evidence_class=_evidence_class(
            flags, miss, engine_verdict, verdict_cap=verdict_cap
        ),
        miss_class=miss,
        restriction_id=restriction_id,
        resolution_layer=getattr(resolved, "resolution_layer", None),
    )
```

**Do not** iterate `breakdown` keys for `rule_ids`.

- [x] **Step 5: Run tests to verify they pass**

Run: `pytest tests/ike2/coverage_os/test_deny_lists.py tests/ike2/coverage_os/test_evidence_chain.py -v`  
Expected: PASS (including multi-ingredient `matched_rules` test)

- [x] **Step 6: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/ \
  backend/core/knowledge/ike2/compliance.py \
  backend/core/knowledge/ike2/rules.py \
  backend/tests/ike2/coverage_os/test_deny_lists.py \
  backend/tests/ike2/coverage_os/test_evidence_chain.py
git commit -m "feat(coverage-os): evidence chain with real rule_ids and shared deny lists"
```

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

- [x] **Step 1: Write the failing test**

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
    assert led.latest_promoted(key) is not None
    assert led.latest_promoted(key)["version"] == 1
    demoted = led.append_demoted(candidate_key=key, reason="sample_audit_fail")
    assert demoted["version"] == 2
    assert demoted["prior_version"] == 1
    assert led.latest_promoted(key) is None


def test_rejected_human_promote_writes_nothing(tmp_path):
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
    assert led.path.read_text(encoding="utf-8").strip() == ""
    assert led.latest_promoted(key) is None
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/ike2/coverage_os/test_promote_ledger.py -v`  
Expected: FAIL

- [x] **Step 3: Write minimal implementation**

**Literal `PromoteLedger` (review before Task 2 done)** — full class body, not prose. Answers:
1. `latest_promoted` = forward JSONL scan; last `promoted` wins until a later `demoted` for the same key clears it to `None`.
2. `version` = `max(existing versions for candidate_key) + 1` across **all** kinds (promote/demote/non_promotable); Phase 1 is single-writer append (no multi-process lock).
3. Human `ValueError` runs **before** `_append` / any file write.

```python
# backend/core/knowledge/ike2/coverage_os/promote_ledger.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, Optional


def candidate_key(atom: str, target_canonical: str | None) -> str:
    a = (atom or "").strip().lower()
    c = (target_canonical or a).strip().lower()
    return f"{a}=>{c}"


class PromoteLedger:
    """Append-only JSONL promote / demote / confirmed_non_promotable ledger."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def _iter_rows(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)

    def _next_version(self, candidate_key: str) -> int:
        """Strictly monotonic per candidate_key across every kind."""
        max_v = 0
        for row in self._iter_rows():
            if row.get("candidate_key") != candidate_key:
                continue
            try:
                max_v = max(max_v, int(row.get("version") or 0))
            except (TypeError, ValueError):
                continue
        return max_v + 1

    def _append(self, row: dict[str, Any]) -> dict[str, Any]:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        return row

    def append_promoted(
        self,
        *,
        candidate_key: str,
        rule_id: str,
        source: str,
        payload: dict[str, Any],
        auto: bool = True,
        reviewer_id: str | None = None,
        approval_rationale: str | None = None,
    ) -> dict[str, Any]:
        # Validate BEFORE any write — rejected call must leave no partial row.
        if not auto:
            if not reviewer_id or not str(approval_rationale or "").strip():
                raise ValueError(
                    "human promote requires reviewer_id and approval_rationale"
                )

        row: dict[str, Any] = {
            "kind": "promoted",
            "candidate_key": candidate_key,
            "rule_id": rule_id,
            "source": source,
            "payload": payload,
            "auto": bool(auto),
            "version": self._next_version(candidate_key),
            "active": True,
        }
        if not auto:
            row["reviewer_id"] = reviewer_id
            row["approval_rationale"] = str(approval_rationale).strip()
        return self._append(row)

    def append_demoted(
        self,
        *,
        candidate_key: str,
        reason: str,
        prior_version: int | None = None,
    ) -> dict[str, Any]:
        # Phase 1 decision: demote with no active promote is allowed (prior_version=None).
        # Do not raise — unlikely caller error; a clear prior_version=None is preferable
        # to a hard fail that blocks audit logging of "we tried to retract."
        if prior_version is None:
            latest = self.latest_promoted(candidate_key)
            prior_version = int(latest["version"]) if latest else None
        row: dict[str, Any] = {
            "kind": "demoted",
            "candidate_key": candidate_key,
            "reason": reason,
            "prior_version": prior_version,
            "version": self._next_version(candidate_key),
            "active": False,
        }
        return self._append(row)

    def append_non_promotable(
        self,
        *,
        candidate_key: str,
        rule_id: str,
        source: str,
        reason: str,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "kind": "confirmed_non_promotable",
            "candidate_key": candidate_key,
            "rule_id": rule_id,
            "source": source,
            "reason": reason,
            "version": self._next_version(candidate_key),
        }
        return self._append(row)

    def find_non_promotable(self, candidate_key: str) -> dict | None:
        """Latest confirmed_non_promotable for this key, or None."""
        hit: dict | None = None
        for row in self._iter_rows():
            if (
                row.get("candidate_key") == candidate_key
                and row.get("kind") == "confirmed_non_promotable"
            ):
                hit = row
        return hit

    def latest_promoted(self, candidate_key: str) -> dict | None:
        """Forward scan: last promoted for key, cleared by a later demoted.

        Demote after promote → returns None (not an inactive promoted row).
        Non-promotable rows do not clear an active promote (separate short-circuit).
        """
        current: dict | None = None
        for row in self._iter_rows():
            if row.get("candidate_key") != candidate_key:
                continue
            kind = row.get("kind")
            if kind == "promoted":
                current = row
            elif kind == "demoted":
                current = None
        return current
```

**Trace notes (same standard as decide_promote):**
- `test_human_promote_requires_reviewer_fields`: `ValueError` before `_append`; file stays empty; successful human write has `version == 1`.
- `test_demote_increments_and_marks_inactive`: promote v1 → demote v2 → `latest_promoted` is `None` (cleared by demoted), not a stale active row.
- `test_non_promotable_blocks_lookup`: `find_non_promotable` returns latest `confirmed_non_promotable` row.
- Version interleaving: promote → demote → non_promotable on same key yields versions 1, 2, 3 via shared `_next_version`.

Tighten demote assertion to the literal semantics (no `active is False` ambiguity):

```python
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
    assert led.latest_promoted(key) is not None
    assert led.latest_promoted(key)["version"] == 1
    demoted = led.append_demoted(candidate_key=key, reason="sample_audit_fail")
    assert demoted["version"] == 2
    assert demoted["prior_version"] == 1
    assert led.latest_promoted(key) is None


def test_rejected_human_promote_writes_nothing(tmp_path):
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
    assert led.path.read_text(encoding="utf-8").strip() == ""
    assert led.latest_promoted(key) is None
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/ike2/coverage_os/test_promote_ledger.py -v`  
Expected: PASS

- [x] **Step 5: Commit**

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
- Consumes: `PromoteLedger.find_non_promotable`, candidate flags dict, ontology mapping (for collision), **`deny_lists.is_allergen_adjacent` / `is_animalish`** (do **not** copy flag frozensets into this module)
- Produces:
  - `has_dual_origin_collision(candidate_name, ontology) -> bool` — predicate #4
  - `is_umbrella_term(candidate_name, flags=None) -> bool` — predicate #5
  - `GateDecision` with `action: Literal["auto_promote","human_approval","rejected"]`, `rule_id`, `reason`
  - `decide_promote(*, candidate_key, candidate_name, flags, ledger, ontology) -> GateDecision`

**Named blind spot (closed 2026-07-21):** Do **not** accept `name_collision_animal` / `is_umbrella` as inert bool defaults. `decide_promote` **must compute** predicates #4 and #5 internally (or via the helpers above) every call. Callers pass `candidate_name` + `ontology`; they never pass pre-baked booleans that default to False.

**Allergen-adjacent:** call `is_allergen_adjacent(flags)` from `deny_lists.py` only. Sulfite = `sulphite_source`; mollusc = `animal_species` in `{mollusk, mollusc}` (encoded inside that helper).

**Detection contracts (full substance — review before Task 3):**

Ontology rows in `data/ontology.json` store identity flags **flat** on the ingredient
(`animal_origin`, …) plus `aliases: list[str]`. Nested `flags` dicts are also accepted
for test fixtures / future payloads.

```python
# --- truth_anchor.py addition (reuse, do not fork compound lists) ---
def is_compound_umbrella(name: str) -> bool:
    """True when name is a Tier-1 compound/umbrella registered via _add_compound.

    Uses ``_COMPOUND_CANONICALS`` + ``lookup`` — the same set that caps
    natural flavors / spices / dish shells to verdict_cap=WARN. Do **not**
    re-list those strings in hybrid_gate.
    """
    from core.normalization.normalizer import normalize_ingredient_key

    if not name or not str(name).strip():
        return False
    key = normalize_ingredient_key(str(name).strip())
    if key in _COMPOUND_CANONICALS:
        return True
    fact = lookup(key) or lookup(str(name).strip())
    if fact is None:
        return False
    return fact.canonical_name in _COMPOUND_CANONICALS
```

```python
# --- hybrid_gate.py detection (computed every decide_promote call) ---
from __future__ import annotations
from typing import Any, Mapping

from core.knowledge.ike2.coverage_os.deny_lists import is_allergen_adjacent, is_animalish
from core.knowledge.ike2.truth_anchor import is_compound_umbrella
from core.normalization.normalizer import is_e_number_code, normalize_ingredient_key

_ROW_FLAG_KEYS = (
    # Enough to feed deny_lists; prefer nested flags when present.
    "plant_origin", "animal_origin", "animal_species",
    "egg_source", "fish_source", "shellfish_source", "insect_derived",
    "bee_product", "dairy_source", "peanut_source", "tree_nut_source",
    "sesame_source", "soy_source", "gluten_source", "mustard_source",
    "celery_source", "lupin_source", "sulphite_source", "verdict_cap",
)


def _row_flags(row: Mapping[str, Any]) -> dict[str, Any]:
    nested = row.get("flags")
    if isinstance(nested, dict) and nested:
        return dict(nested)
    return {k: row[k] for k in _ROW_FLAG_KEYS if k in row}


def _norm_key(s: str) -> str:
    return normalize_ingredient_key(str(s).strip()) if s else ""


def has_dual_origin_collision(candidate_name: str, ontology: Mapping[str, Any]) -> bool:
    """Predicate #4 — True if candidate_name keys an animalish/allergen ontology row.

    Match surface (all case-/normalize-folded):
      1. ingredient ``canonical_name`` (or ``name``)
      2. every entry in ingredient ``aliases``

    A collision that only exists as an **alias** (e.g. candidate ``gelatine`` vs
    row canonical ``gelatin`` with aliases ``[Gelatine, …]``) **must** return True.
    Does not require the candidate's own proposed flags to look animalish — the
    *existing* row's flags decide.
    """
    needle = _norm_key(candidate_name)
    if not needle:
        return False
    for row in ontology.get("ingredients") or []:
        if not isinstance(row, Mapping):
            continue
        names = {_norm_key(row.get("canonical_name") or row.get("name") or "")}
        for a in row.get("aliases") or []:
            names.add(_norm_key(a))
        names.discard("")
        if needle not in names:
            continue
        flags = _row_flags(row)
        if is_animalish(flags) or is_allergen_adjacent(flags):
            return True
    return False


def is_umbrella_term(candidate_name: str, flags: dict | None = None) -> bool:
    """Predicate #5 — compound/process umbrella; prefer shared Tier-1 logic.

    Order:
      1. candidate ``flags.verdict_cap == "WARN"`` (same signal compounds carry)
      2. ``truth_anchor.is_compound_umbrella(name)`` — **reuses** ``_COMPOUND_CANONICALS``
         / ``_add_compound`` (natural flavors, spices, enzymes, dish shells, …)
      3. ``is_e_number_code(name)`` — E-numbers are process/additive umbrellas at promote time

    **Drift note (named, not silent):** ``promote_commodity_coverage.py`` keeps a
    separate ``_COMPOUND_DISH_RE`` / ``_COMPOUND_NEVER_FIRM_SEED`` for seed filtering.
    Phase 1 gate does **not** copy that regex. Dish umbrellas already registered via
    ``_add_compound`` in truth_anchor are covered by (2). Unifying the script's regex
    into a shared library is a follow-up — not a second string list inside hybrid_gate.
    """
    f = flags or {}
    if f.get("verdict_cap") == "WARN":
        return True
    if is_compound_umbrella(candidate_name or ""):
        return True
    if is_e_number_code(candidate_name or ""):
        return True
    return False
```

- [x] **Step 1: Write the failing tests** (include positive collision → human)

```python
from core.knowledge.ike2.coverage_os.hybrid_gate import (
    decide_promote,
    has_dual_origin_collision,
    is_umbrella_term,
)
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key
from core.knowledge.ike2.truth_anchor import is_compound_umbrella


def _empty_ontology():
    return {"ingredients": []}


def _gelatin_ontology():
    """Mirrors real ontology shape: flat flags + aliases including Gelatine."""
    return {
        "ingredients": [
            {
                "canonical_name": "gelatin",
                "aliases": [
                    "E441", "Gelatine", "Pork Gelatin", "Beef Gelatin",
                    "Fish Gelatin",
                ],
                "animal_origin": True,
                "fish_source": True,
                "plant_origin": False,
            }
        ]
    }


def test_non_promotable_short_circuits(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    key = candidate_key("roman", "roman")
    led.append_non_promotable(
        candidate_key=key, rule_id="human_reject", source="corpus", reason="junk",
    )
    d = decide_promote(
        candidate_key=key,
        candidate_name="roman",
        flags={"plant_origin": True},
        ledger=led,
        ontology=_empty_ontology(),
    )
    assert d.action == "rejected"
    assert "non_promotable" in d.reason


def test_broccoli_auto_promotes(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("broccoli", "broccoli"),
        candidate_name="broccoli",
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology=_empty_ontology(),
    )
    assert d.action == "auto_promote"
    assert d.rule_id == "closed_form_plant_v1"


def test_sulphite_goes_human(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("dried apricot", "dried apricot"),
        candidate_name="dried apricot",
        flags={"plant_origin": True, "sulphite_source": True},
        ledger=led,
        ontology=_empty_ontology(),
    )
    assert d.action == "human_approval"


def test_mollusc_species_goes_human(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("snail", "snail"),
        candidate_name="snail",
        flags={"animal_origin": True, "animal_species": "mollusk"},
        ledger=led,
        ontology=_empty_ontology(),
    )
    assert d.action == "human_approval"


def test_beef_goes_human_not_auto(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("beef", "beef"),
        candidate_name="beef",
        flags={"animal_origin": True, "animal_species": "cow"},
        ledger=led,
        ontology=_empty_ontology(),
    )
    assert d.action == "human_approval"


def test_collision_via_alias_not_only_canonical():
    """Positive: plant-looking candidate name hits animal row via alias only."""
    ontology = _gelatin_ontology()
    # Canonical-only check would miss this — alias Gelatine must collide.
    assert has_dual_origin_collision("gelatine", ontology) is True
    assert has_dual_origin_collision("Gelatine", ontology) is True
    assert has_dual_origin_collision("gelatin", ontology) is True
    assert has_dual_origin_collision("broccoli", ontology) is False


def test_plant_candidate_colliding_alias_routes_human_not_auto(tmp_path):
    """Positive end-to-end: plant-only flags + alias collision → human_approval."""
    led = PromoteLedger(tmp_path / "l.jsonl")
    ontology = _gelatin_ontology()
    d = decide_promote(
        candidate_key=candidate_key("gelatine", "gelatin"),
        candidate_name="gelatine",
        # Candidate payload looks plant-only — collision must still block auto.
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology=ontology,
    )
    assert d.action == "human_approval"
    assert d.rule_id == "human_dual_origin_collision"
    assert "collision" in d.reason.lower()
    assert "dual" in d.reason.lower()


def test_umbrella_reuses_truth_anchor_compounds(tmp_path):
    """Predicate #5 — shared Tier-1 compounds, not a forked string list."""
    assert is_compound_umbrella("natural flavors") is True
    assert is_compound_umbrella("spices") is True
    assert is_compound_umbrella("broccoli") is False
    assert is_umbrella_term("natural flavors", {"plant_origin": True}) is True
    assert is_umbrella_term("broccoli", {"plant_origin": True}) is False
    assert is_umbrella_term("mystery", {"plant_origin": True, "verdict_cap": "WARN"}) is True
    assert is_umbrella_term("e441", {}) is True  # e-number umbrella

    led = PromoteLedger(tmp_path / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("natural flavors", "natural flavors"),
        candidate_name="natural flavors",
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology=_empty_ontology(),
    )
    assert d.action == "human_approval"
    assert d.rule_id == "human_umbrella"
    assert "umbrella" in d.reason.lower()
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/ike2/coverage_os/test_hybrid_gate.py -v`  
Expected: FAIL

- [x] **Step 3: Write minimal implementation**

Also add `is_compound_umbrella` to `truth_anchor.py` (export for gate + tests).

**Wiring (literal — review before Task 3 done):** `GateDecision` + `decide_promote` below are the full function bodies, not an outline. Detection helpers above are called from here.

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Optional

from core.knowledge.ike2.coverage_os.deny_lists import is_allergen_adjacent, is_animalish
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger


@dataclass(frozen=True)
class GateDecision:
    action: Literal["auto_promote", "human_approval", "rejected"]
    rule_id: str
    reason: str


def decide_promote(
    *,
    candidate_key: str,
    candidate_name: str,
    flags: Optional[dict[str, Any]],
    ledger: PromoteLedger,
    ontology: Mapping[str, Any],
) -> GateDecision:
    """Hybrid gate. Non-promotable short-circuit runs before any other predicate."""
    flags = dict(flags or {})

    # 1) Ledger short-circuit — strictly first; do not compute collision/umbrella yet.
    blocked = ledger.find_non_promotable(candidate_key)
    if blocked is not None:
        return GateDecision(
            action="rejected",
            rule_id=str(blocked.get("rule_id") or "confirmed_non_promotable"),
            reason="confirmed_non_promotable",
        )

    # 2) Compute predicates #4 and #5 every call (never caller-supplied bools).
    collision = has_dual_origin_collision(candidate_name, ontology)
    umbrella = is_umbrella_term(candidate_name, flags)

    # 3) Human paths — first matching reason wins (specific strings for audit/tests).
    if is_allergen_adjacent(flags):
        return GateDecision(
            action="human_approval",
            rule_id="human_allergen_adjacent",
            reason="allergen-adjacent flags require human approval",
        )
    if is_animalish(flags):
        return GateDecision(
            action="human_approval",
            rule_id="human_animal_derived",
            reason="animal-derived flags require human approval",
        )
    if collision:
        return GateDecision(
            action="human_approval",
            rule_id="human_dual_origin_collision",
            reason="dual-origin name collision with animal/allergen ontology row",
        )
    if umbrella:
        return GateDecision(
            action="human_approval",
            rule_id="human_umbrella",
            reason="compound/process umbrella requires human approval",
        )

    # 4) Auto only for plant-only closed-form with no blocking predicates above.
    if flags.get("plant_origin") and not flags.get("animal_origin"):
        return GateDecision(
            action="auto_promote",
            rule_id="closed_form_plant_v1",
            reason="closed_form_plant",
        )

    # 5) Fail-closed to human — never silent auto.
    return GateDecision(
        action="human_approval",
        rule_id="human_fail_closed",
        reason="insufficient closed-form plant evidence",
    )
```

**Wiring notes (verify against tests):**
- `test_non_promotable_short_circuits`: returns at step 1; `reason == "confirmed_non_promotable"`; `rule_id` from ledger row (or fallback).
- `test_plant_candidate_colliding_alias_routes_human_not_auto`: plant flags skip animalish/allergen; `collision` True → `reason` contains both `"dual"` and `"collision"`; `rule_id == "human_dual_origin_collision"`.
- `test_umbrella_reuses_truth_anchor_compounds` end-to-end: `rule_id == "human_umbrella"`; `reason` contains `"umbrella"`.
- `test_broccoli_auto_promotes`: `rule_id == "closed_form_plant_v1"`.
- Rejected / human paths always set `rule_id` (never leave it empty or only populate on auto).

Import allergen/animal checks **only** from `deny_lists` — no local duplicate frozensets.
Import compound umbrellas **only** via `truth_anchor.is_compound_umbrella` — no local copy of natural-flavors/spices strings.

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/ike2/coverage_os/test_hybrid_gate.py -v`  
Expected: PASS (incl. alias-collision positive + umbrella reuse tests)

- [x] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/truth_anchor.py \
  backend/core/knowledge/ike2/coverage_os/hybrid_gate.py \
  backend/tests/ike2/coverage_os/test_hybrid_gate.py
git commit -m "feat(coverage-os): hybrid gate with alias collision and shared umbrella detection"
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
  - `commit_promotion(entry, ledger, *, ontology_path, aliases_path, **ledger_kwargs) -> None` — **write first, then** `ledger.append_promoted(...)`; on write failure raise and leave ledger without a promoted entry
  - Optional: `mirror_l3_inject(entry) -> None` stub that logs "derived mirror; not source of truth" (no hard fail if Supabase down)

**Behavior:**
- `apply`: add/update ingredient row in `ontology.json` ingredients list OR add alias key in `variant_aliases.json` per payload `write_kind` (`ontology_row` | `variant_alias`)
- `retract`: remove the alias key or mark/remove the ontology row that this ledger version added (payload must include enough to reverse; store `inverse` in ledger payload at promote time)
- Never leave half-written JSON (write temp + replace)
- On failure: raise; caller / `commit_promotion` leaves ledger pending (no `promoted` row)

- [x] **Step 1: Write the failing tests**

```python
import json
from pathlib import Path
from unittest.mock import patch
from core.knowledge.ike2.coverage_os.promote_writer import (
    apply_promotion,
    retract_promotion,
    commit_promotion,
)
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key


def _base_ontology(tmp: Path) -> Path:
    p = tmp / "ontology.json"
    p.write_text(json.dumps({"ontology_version": "test", "ingredients": []}) + "\n")
    return p


def _base_aliases(tmp: Path) -> Path:
    p = tmp / "variant_aliases.json"
    p.write_text(json.dumps({
        "aliases": {},
        "coverage_os_managed_aliases": [],
    }) + "\n")
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


def test_apply_and_retract_ontology_row(tmp_path):
    """Symmetric path — most Coverage OS candidates are new ingredient facts."""
    ont = _base_ontology(tmp_path)
    al = _base_aliases(tmp_path)
    entry = {
        "kind": "promoted",
        "payload": {
            "write_kind": "ontology_row",
            "canonical_name": "broccoli",
            "flags": {"plant_origin": True, "animal_origin": False},
            "inverse": {
                "write_kind": "ontology_row",
                "canonical_name": "broccoli",
            },
        },
    }
    apply_promotion(entry, ontology_path=ont, aliases_path=al)
    ingredients = json.loads(ont.read_text())["ingredients"]
    row = next(i for i in ingredients if i.get("canonical_name") == "broccoli")
    assert row["flags"]["plant_origin"] is True
    assert row.get("coverage_os_managed") is True
    retract_promotion(entry, ontology_path=ont, aliases_path=al)
    ingredients = json.loads(ont.read_text())["ingredients"]
    assert not any(i.get("canonical_name") == "broccoli" for i in ingredients)


def test_write_failure_leaves_ledger_pending(tmp_path):
    """Write fails → no promoted ledger row (never mark promoted that was not written)."""
    ont = _base_ontology(tmp_path)
    al = _base_aliases(tmp_path)
    led = PromoteLedger(tmp_path / "l.jsonl")
    key = candidate_key("broccoli", "broccoli")
    entry = {
        "kind": "promoted",
        "candidate_key": key,
        "payload": {
            "write_kind": "ontology_row",
            "canonical_name": "broccoli",
            "flags": {"plant_origin": True},
            "inverse": {"write_kind": "ontology_row", "canonical_name": "broccoli"},
        },
    }
    with patch(
        "core.knowledge.ike2.coverage_os.promote_writer.apply_promotion",
        side_effect=OSError("disk full"),
    ):
        try:
            commit_promotion(
                entry,
                led,
                ontology_path=ont,
                aliases_path=al,
                rule_id="closed_form_plant_v1",
                source="test",
            )
            assert False, "expected OSError"
        except OSError:
            pass
    assert led.latest_promoted(key) is None


def test_refuse_overwrite_and_retract_unmanaged_alias(tmp_path):
    """Parity with ontology coverage_os_managed — hand-authored aliases are sacred."""
    ont = _base_ontology(tmp_path)
    al = _base_aliases(tmp_path)
    # Seed a hand-authored alias (not in coverage_os_managed_aliases).
    al.write_text(json.dumps({
        "aliases": {"salt himalayan": "himalayan salt"},
        "coverage_os_managed_aliases": [],
    }) + "\n")
    entry = {
        "kind": "promoted",
        "payload": {
            "write_kind": "variant_alias",
            "alias": "salt himalayan",
            "canonical": "table salt",  # would clobber
            "inverse": {"write_kind": "variant_alias", "alias": "salt himalayan"},
        },
    }
    try:
        apply_promotion(entry, ontology_path=ont, aliases_path=al)
        assert False, "expected ValueError on unmanaged overwrite"
    except ValueError as e:
        assert "non-coverage_os_managed" in str(e)
    aliases = json.loads(al.read_text())["aliases"]
    assert aliases["salt himalayan"] == "himalayan salt"  # untouched
    try:
        retract_promotion(entry, ontology_path=ont, aliases_path=al)
        assert False, "expected ValueError on unmanaged retract"
    except ValueError as e:
        assert "non-coverage_os_managed" in str(e)
    aliases = json.loads(al.read_text())["aliases"]
    assert aliases["salt himalayan"] == "himalayan salt"
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/ike2/coverage_os/test_promote_writer.py -v`  
Expected: FAIL

- [x] **Step 3: Write minimal implementation**

**Literal `promote_writer.py` (review before Task 4 done)** — full module body.

Atomic write: temp file in same directory → `os.replace` (POSIX atomic).  
`coverage_os_managed: true` is set on every ontology row Coverage OS creates; retract **only** removes a row when that marker is present (never deletes hand-curated rows).  
`commit_promotion`: `apply_promotion` **then** `ledger.append_promoted` — on apply failure, raise and leave ledger without a promoted row.

```python
# backend/core/knowledge/ike2/coverage_os/promote_writer.py
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger

log = logging.getLogger(__name__)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _atomic_write_json(path: Path, data: Mapping[str, Any]) -> None:
    """Write JSON via temp file + os.replace — never leave half-written target."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _payload(entry: Mapping[str, Any]) -> dict[str, Any]:
    raw = entry.get("payload")
    if not isinstance(raw, dict):
        raise ValueError("promotion entry requires payload dict")
    return dict(raw)


def _managed_alias_set(data: Mapping[str, Any]) -> set[str]:
    """Keys Coverage OS may overwrite/retract. Parallel to aliases string map.

    Keeps ``aliases`` values as bare strings so ``variant_aliases.py`` consumers
    stay unchanged. Marker lives in ``coverage_os_managed_aliases`` (list).
    """
    return {str(x) for x in (data.get("coverage_os_managed_aliases") or [])}


def _apply_variant_alias(payload: Mapping[str, Any], *, aliases_path: Path) -> None:
    alias = str(payload.get("alias") or "").strip()
    canonical = str(payload.get("canonical") or "").strip()
    if not alias or not canonical:
        raise ValueError("variant_alias requires alias and canonical")
    data = _read_json(aliases_path)
    aliases = dict(data.get("aliases") or {})
    managed = _managed_alias_set(data)
    if alias in aliases and alias not in managed:
        raise ValueError(
            f"refusing to overwrite non-coverage_os_managed alias: {alias}"
        )
    aliases[alias] = canonical
    managed.add(alias)
    data["aliases"] = aliases
    data["coverage_os_managed_aliases"] = sorted(managed)
    _atomic_write_json(aliases_path, data)


def _retract_variant_alias(inverse: Mapping[str, Any], *, aliases_path: Path) -> None:
    alias = str(inverse.get("alias") or "").strip()
    if not alias:
        raise ValueError("variant_alias inverse requires alias")
    data = _read_json(aliases_path)
    aliases = dict(data.get("aliases") or {})
    managed = _managed_alias_set(data)
    if alias not in managed:
        if alias not in aliases:
            return  # idempotent: nothing Coverage OS owned
        raise ValueError(
            f"refusing to retract non-coverage_os_managed alias: {alias}"
        )
    aliases.pop(alias, None)
    managed.discard(alias)
    data["aliases"] = aliases
    data["coverage_os_managed_aliases"] = sorted(managed)
    _atomic_write_json(aliases_path, data)


def _apply_ontology_row(payload: Mapping[str, Any], *, ontology_path: Path) -> None:
    name = str(payload.get("canonical_name") or "").strip()
    if not name:
        raise ValueError("ontology_row requires canonical_name")
    flags = dict(payload.get("flags") or {})
    data = _read_json(ontology_path)
    ingredients = list(data.get("ingredients") or [])

    existing_idx = None
    for i, row in enumerate(ingredients):
        if str(row.get("canonical_name") or "").strip() == name:
            existing_idx = i
            break

    if existing_idx is not None:
        existing = ingredients[existing_idx]
        if not existing.get("coverage_os_managed"):
            raise ValueError(
                f"refusing to overwrite non-coverage_os_managed row: {name}"
            )
        row = dict(existing)
    else:
        row = {
            "id": name.replace(" ", "_"),
            "canonical_name": name,
            "aliases": [],
        }

    # Nested flags (test/audit) + flat copies (match data/ontology.json consumers).
    row["flags"] = flags
    for k, v in flags.items():
        row[k] = v
    row["coverage_os_managed"] = True

    if existing_idx is not None:
        ingredients[existing_idx] = row
    else:
        ingredients.append(row)
    data["ingredients"] = ingredients
    _atomic_write_json(ontology_path, data)


def _retract_ontology_row(inverse: Mapping[str, Any], *, ontology_path: Path) -> None:
    name = str(inverse.get("canonical_name") or "").strip()
    if not name:
        raise ValueError("ontology_row inverse requires canonical_name")
    data = _read_json(ontology_path)
    ingredients = list(data.get("ingredients") or [])
    kept: list[dict[str, Any]] = []
    removed = False
    for row in ingredients:
        if str(row.get("canonical_name") or "").strip() != name:
            kept.append(row)
            continue
        # Only reverse what Coverage OS itself added.
        if not row.get("coverage_os_managed"):
            raise ValueError(
                f"refusing to retract non-coverage_os_managed row: {name}"
            )
        removed = True
        # drop row
    if not removed:
        # Idempotent: nothing to remove.
        return
    data["ingredients"] = kept
    _atomic_write_json(ontology_path, data)


def apply_promotion(
    entry: Mapping[str, Any],
    *,
    ontology_path: Path,
    aliases_path: Path,
) -> None:
    payload = _payload(entry)
    kind = payload.get("write_kind")
    if kind == "variant_alias":
        _apply_variant_alias(payload, aliases_path=Path(aliases_path))
        return
    if kind == "ontology_row":
        _apply_ontology_row(payload, ontology_path=Path(ontology_path))
        return
    raise ValueError(f"unsupported write_kind: {kind!r}")


def retract_promotion(
    entry: Mapping[str, Any],
    *,
    ontology_path: Path,
    aliases_path: Path,
) -> None:
    payload = _payload(entry)
    inverse = payload.get("inverse")
    if not isinstance(inverse, dict):
        raise ValueError("retract requires payload.inverse dict")
    kind = inverse.get("write_kind") or payload.get("write_kind")
    if kind == "variant_alias":
        _retract_variant_alias(inverse, aliases_path=Path(aliases_path))
        return
    if kind == "ontology_row":
        _retract_ontology_row(inverse, ontology_path=Path(ontology_path))
        return
    raise ValueError(f"unsupported inverse write_kind: {kind!r}")


def commit_promotion(
    entry: Mapping[str, Any],
    ledger: PromoteLedger,
    *,
    ontology_path: Path,
    aliases_path: Path,
    rule_id: str,
    source: str,
    auto: bool = True,
    reviewer_id: str | None = None,
    approval_rationale: str | None = None,
    candidate_key: str | None = None,
) -> dict[str, Any]:
    """Write L2 first; only then append ledger promoted row.

    If apply_promotion raises, ledger is untouched (pending / no promoted entry).
    """
    apply_promotion(entry, ontology_path=ontology_path, aliases_path=aliases_path)
    key = candidate_key or entry.get("candidate_key")
    if not key:
        raise ValueError("commit_promotion requires candidate_key")
    return ledger.append_promoted(
        candidate_key=str(key),
        rule_id=rule_id,
        source=source,
        payload=_payload(entry),
        auto=auto,
        reviewer_id=reviewer_id,
        approval_rationale=approval_rationale,
    )


def mirror_l3_inject(entry: Mapping[str, Any]) -> None:
    """Phase 1 stub: L3 is a derived mirror, never source of truth."""
    log.info(
        "coverage_os L3 mirror stub; not source of truth; entry=%s",
        entry.get("candidate_key") or entry.get("kind"),
    )
```

**Trace notes:**
- `test_apply_and_retract_variant_alias`: apply writes alias + adds key to `coverage_os_managed_aliases`; retract pops only if managed.
- `test_apply_and_retract_ontology_row`: apply sets nested `flags` + `coverage_os_managed: true`; retract drops only managed rows.
- `test_write_failure_leaves_ledger_pending`: patched `apply_promotion` raises → `append_promoted` never called → `latest_promoted` is None.
- `test_refuse_overwrite_and_retract_unmanaged_alias`: hand-authored alias survives both apply and retract attempts.
- Alias marker uses parallel `coverage_os_managed_aliases` list (keeps `aliases` values as bare strings for `variant_aliases.py`).

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/ike2/coverage_os/test_promote_writer.py -v`  
Expected: PASS (alias path, ontology-row path, write-failure/ledger-pending)

- [x] **Step 5: Commit**

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

- [x] **Step 1: Write the failing test**

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


def test_run_matrix_clears_resolution_cache(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        "core.knowledge.ike2.coverage_os.profile_matrix.resolution_cache.clear",
        lambda: calls.append("resolution"),
    )
    monkeypatch.setattr(
        "core.knowledge.ike2.coverage_os.profile_matrix.local_ontology.reset_cache",
        lambda: calls.append("ontology"),
    )
    monkeypatch.setattr(
        "core.knowledge.ike2.coverage_os.profile_matrix.reset_variant_alias_cache",
        lambda: calls.append("aliases"),
    )
    run_matrix("sugar", restriction_ids=["vegan"])
    assert calls == ["resolution", "ontology", "aliases"]
    calls.clear()
    run_matrix("sugar", restriction_ids=["vegan"], clear_caches=False)
    assert calls == []
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/ike2/coverage_os/test_profile_matrix.py -v`  
Expected: FAIL

- [x] **Step 3: Write minimal implementation + CLI**

**Literal `profile_matrix.py` + CLI (review before Task 5 done).**

Threading (per `(atom, restriction_id)` cell):
`parse_atoms` → for each atom: `resolve` once → `to_compliance_input` once → for each restriction: `evaluate([inp], single-restriction profile)` → `build_chain_from_resolve` → row with `bucket = chain.verdict`.

Cache: **every** `run_matrix` call starts with `_reset_l2_caches()` (resolution cache + local ontology + variant aliases) unless `clear_caches=False`. Within one run, resolve still benefits from write-through cache across atoms. Stale L2 after promote_writer applies must not survive across analyst matrix re-runs.

**Path sanity (verified 2026-07-21):** `local_ontology.reset_cache`, `reset_variant_alias_cache`, and `resolution_cache.clear` exist as real callables in the codebase (confirmed via import before implement).

**Phase 1 performance tradeoff (named, not silent):** `run_matrix` calls `evaluate()` once per `(atom × restriction)` rather than once per atom with all restrictions on the profile — O(atoms × |SUPPORTED_RESTRICTIONS|) engine calls. Safer against batch-aggregation risk; offline analyst tool only (not chat hot path). Large production pastes against the full restriction set may be slow; optimize later only if measured.

```python
# backend/core/knowledge/ike2/coverage_os/profile_matrix.py
from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, Optional

from core.knowledge.ike2 import resolution_cache
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.coverage_os.evidence_chain import build_chain_from_resolve
from core.knowledge.ike2.input_layer import parse_atoms
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.rules import SUPPORTED_RESTRICTIONS, seeded_rules
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.stores import local_ontology
from core.knowledge.ike2.variant_aliases import reset_variant_alias_cache


def _reset_l2_caches() -> None:
    """Drop in-process L2 resolution state so a full matrix run sees current files.

    Called at the start of every ``run_matrix`` (default). Does not clear mid-run;
    within one paste, resolve write-through cache remains useful across atoms.
    """
    resolution_cache.clear()
    local_ontology.reset_cache()
    reset_variant_alias_cache()


def run_matrix(
    raw: str,
    restriction_ids: Optional[Iterable[str]] = None,
    *,
    region: Optional[str] = None,
    clear_caches: bool = True,
) -> list[dict[str, Any]]:
    if clear_caches:
        _reset_l2_caches()

    if restriction_ids is None:
        profiles = sorted(SUPPORTED_RESTRICTIONS)
    else:
        profiles = list(restriction_ids)

    atoms = parse_atoms(raw)
    rules = seeded_rules()
    rows: list[dict[str, Any]] = []

    for atom in atoms:
        resolved = resolve(atom.name, region)
        compliance_input = to_compliance_input(
            resolved,
            trace=atom.trace,
            may_contain=atom.may_contain,
            query_atom=atom.name,
        )
        for restriction_id in profiles:
            profile = SimpleNamespace(
                restrictions={restriction_id: "preference"},
            )
            # One restriction per evaluate so this cell's ComplianceResult is not
            # an aggregate across unrelated profiles (bucket still comes from chain).
            compliance_result = evaluate([compliance_input], profile, rules)
            chain = build_chain_from_resolve(
                atom=atom.name,
                resolved=resolved,
                compliance_result=compliance_result,
                restriction_id=restriction_id,
                compliance_input=compliance_input,
            )
            rows.append({
                "ingredient": atom.name,
                "profile": restriction_id,
                "bucket": chain.verdict,  # Safe | Avoid | Depends — already audit bucket
                "chain": chain.to_dict(),
            })
    return rows


def write_matrix_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["ingredient", "profile", "bucket", "evidence_class", "miss_class"],
        )
        w.writeheader()
        for r in rows:
            chain = r.get("chain") or {}
            w.writerow({
                "ingredient": r.get("ingredient"),
                "profile": r.get("profile"),
                "bucket": r.get("bucket"),
                "evidence_class": chain.get("evidence_class"),
                "miss_class": chain.get("miss_class"),
            })
```

```python
# backend/scripts/run_profile_matrix.py
"""CLI: paste × profiles → Safe/Avoid/Depends + evidence chains."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python backend/scripts/run_profile_matrix.py` from repo root.
_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from core.knowledge.ike2.coverage_os.profile_matrix import run_matrix, write_matrix_csv
from core.knowledge.ike2.rules import SUPPORTED_RESTRICTIONS


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Coverage OS multi-profile matrix")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--paste", help="Raw ingredient paste string")
    src.add_argument("--file", type=Path, help="Path to paste text file")
    p.add_argument(
        "--restrictions",
        nargs="*",
        default=None,
        help="Restriction ids (default: all SUPPORTED_RESTRICTIONS)",
    )
    p.add_argument("--csv", type=Path, default=None, help="Optional CSV output path")
    p.add_argument("--json", type=Path, default=None, help="Optional JSON output path")
    p.add_argument(
        "--no-clear-caches",
        action="store_true",
        help="Skip L2 cache reset (default is clear at start of each run)",
    )
    args = p.parse_args(argv)

    raw = args.paste if args.paste is not None else Path(args.file).read_text(encoding="utf-8")
    restriction_ids = args.restrictions
    if restriction_ids is None:
        restriction_ids = sorted(SUPPORTED_RESTRICTIONS)

    rows = run_matrix(
        raw,
        restriction_ids=restriction_ids,
        clear_caches=not args.no_clear_caches,
    )
    if args.csv:
        write_matrix_csv(rows, args.csv)
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    else:
        # Default: compact stdout lines for analyst scanning.
        for r in rows:
            print(f"{r['ingredient']}\t{r['profile']}\t{r['bucket']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Extra test (cache clear is not optional prose):

```python
def test_run_matrix_clears_resolution_cache(monkeypatch):
    calls: list[str] = []

    def _clear():
        calls.append("resolution")

    monkeypatch.setattr(
        "core.knowledge.ike2.coverage_os.profile_matrix.resolution_cache.clear",
        _clear,
    )
    monkeypatch.setattr(
        "core.knowledge.ike2.coverage_os.profile_matrix.local_ontology.reset_cache",
        lambda: calls.append("ontology"),
    )
    monkeypatch.setattr(
        "core.knowledge.ike2.coverage_os.profile_matrix.reset_variant_alias_cache",
        lambda: calls.append("aliases"),
    )
    run_matrix("sugar", restriction_ids=["vegan"])
    assert calls == ["resolution", "ontology", "aliases"]
    calls.clear()
    run_matrix("sugar", restriction_ids=["vegan"], clear_caches=False)
    assert calls == []
```

Golden paste file:

```text
sugar, beef, egg, salt himalayan, savills
```

- [x] **Step 4: Run test to verify it passes**
Run: `pytest tests/ike2/coverage_os/test_profile_matrix.py -v`  
Expected: PASS

- [x] **Step 5: Commit**

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

- [x] **Step 1: Write the failing test**

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

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/ike2/coverage_os/test_auto_lane_guards.py -v`  
Expected: FAIL

- [x] **Step 3: Write minimal implementation**

`select_sample_audit`: take every Nth auto promotion (1-indexed or 0-indexed consistently).  
`check_volume_spike`: count promotions with `ts` in `[now - window, now]`; True if count > threshold.

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/ike2/coverage_os/test_auto_lane_guards.py -v`  
Expected: PASS

- [x] **Step 5: Wire smoke into ledger append path (optional thin hook)**

When `append_promoted(..., auto=True)` succeeds, call sample selector on recent auto rows (in-memory list passed by caller is fine in Phase 1 — no need for a daemon). Document in module docstring that Phase 1 is log/stub only.

- [x] **Step 6: Commit**

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

- [ ] **Step 1: Write integration tests** (literal — both L2 write paths)

Exercises gate → writer → ledger → demote/retract → non_promotable short-circuit for **ontology_row** and **variant_alias** separately (closes the Task 4 asymmetry gap at integration grain). Also matrix chain emission.

```python
# backend/tests/ike2/coverage_os/test_phase1_integration.py
from __future__ import annotations

import json
from pathlib import Path

from core.knowledge.ike2.coverage_os.hybrid_gate import decide_promote
from core.knowledge.ike2.coverage_os.profile_matrix import run_matrix
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key
from core.knowledge.ike2.coverage_os.promote_writer import (
    apply_promotion,
    commit_promotion,
    retract_promotion,
)


def _empty_ontology(tmp: Path) -> Path:
    p = tmp / "ontology.json"
    p.write_text(json.dumps({"ontology_version": "test", "ingredients": []}) + "\n")
    return p


def _empty_aliases(tmp: Path) -> Path:
    p = tmp / "variant_aliases.json"
    p.write_text(json.dumps({
        "aliases": {},
        "coverage_os_managed_aliases": [],
    }) + "\n")
    return p


def test_gate_writer_ledger_round_trip_ontology_row(tmp_path):
    """E2E: auto broccoli ontology_row → demote retracts → non_promotable blocks re-gate."""
    ont = _empty_ontology(tmp_path)
    al = _empty_aliases(tmp_path)
    led = PromoteLedger(tmp_path / "ledger.jsonl")
    key = candidate_key("broccoli", "broccoli")

    d = decide_promote(
        candidate_key=key,
        candidate_name="broccoli",
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology={"ingredients": []},
    )
    assert d.action == "auto_promote"
    assert d.rule_id == "closed_form_plant_v1"

    entry = {
        "kind": "promoted",
        "candidate_key": key,
        "payload": {
            "write_kind": "ontology_row",
            "canonical_name": "broccoli",
            "flags": {"plant_origin": True, "animal_origin": False},
            "inverse": {"write_kind": "ontology_row", "canonical_name": "broccoli"},
        },
    }
    commit_promotion(
        entry,
        led,
        ontology_path=ont,
        aliases_path=al,
        rule_id=d.rule_id,
        source="auto",
        auto=True,
    )
    assert led.latest_promoted(key) is not None
    row = next(
        i for i in json.loads(ont.read_text())["ingredients"]
        if i.get("canonical_name") == "broccoli"
    )
    assert row.get("coverage_os_managed") is True

    led.append_demoted(candidate_key=key, reason="sample_audit_fail")
    assert led.latest_promoted(key) is None
    retract_promotion(entry, ontology_path=ont, aliases_path=al)
    assert not any(
        i.get("canonical_name") == "broccoli"
        for i in json.loads(ont.read_text())["ingredients"]
    )

    led.append_non_promotable(
        candidate_key=key,
        rule_id="human_reject",
        source="corpus",
        reason="blocked after demote",
    )
    d2 = decide_promote(
        candidate_key=key,
        candidate_name="broccoli",
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology={"ingredients": []},
    )
    assert d2.action == "rejected"
    assert "non_promotable" in d2.reason


def test_gate_writer_ledger_round_trip_variant_alias(tmp_path):
    """E2E sibling path: auto variant_alias → demote retracts → non_promotable blocks."""
    ont = _empty_ontology(tmp_path)
    al = _empty_aliases(tmp_path)
    led = PromoteLedger(tmp_path / "ledger.jsonl")
    key = candidate_key("salt himalayan", "himalayan salt")

    d = decide_promote(
        candidate_key=key,
        candidate_name="salt himalayan",
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology={"ingredients": []},
    )
    assert d.action == "auto_promote"

    entry = {
        "kind": "promoted",
        "candidate_key": key,
        "payload": {
            "write_kind": "variant_alias",
            "alias": "salt himalayan",
            "canonical": "himalayan salt",
            "inverse": {"write_kind": "variant_alias", "alias": "salt himalayan"},
        },
    }
    commit_promotion(
        entry,
        led,
        ontology_path=ont,
        aliases_path=al,
        rule_id=d.rule_id,
        source="auto",
        auto=True,
    )
    data = json.loads(al.read_text())
    assert data["aliases"]["salt himalayan"] == "himalayan salt"
    assert "salt himalayan" in data["coverage_os_managed_aliases"]
    assert led.latest_promoted(key) is not None

    led.append_demoted(candidate_key=key, reason="sample_audit_fail")
    assert led.latest_promoted(key) is None
    retract_promotion(entry, ontology_path=ont, aliases_path=al)
    data = json.loads(al.read_text())
    assert "salt himalayan" not in data["aliases"]
    assert "salt himalayan" not in data.get("coverage_os_managed_aliases", [])

    led.append_non_promotable(
        candidate_key=key,
        rule_id="human_reject",
        source="corpus",
        reason="blocked after demote",
    )
    d2 = decide_promote(
        candidate_key=key,
        candidate_name="salt himalayan",
        flags={"plant_origin": True, "animal_origin": False},
        ledger=led,
        ontology={"ingredients": []},
    )
    assert d2.action == "rejected"
    assert "non_promotable" in d2.reason


def test_matrix_emits_chain_for_each_cell():
    rows = run_matrix("sugar, beef", restriction_ids=["hindu_vegetarian", "vegan"])
    assert len(rows) >= 4
    assert all(r["chain"]["restriction_id"] == r["profile"] for r in rows)
    assert all(r["bucket"] == r["chain"]["verdict"] for r in rows)
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
| Evidence graph; verdict = Safe/Avoid/Depends; real rule_ids via matched_rules | Task 1 |
| Shared deny lists (sulfite + mollusc); allergen before animal for evidence_class | Task 1 |
| Multi-ingredient matched_rules filter test (named blind spot) | Task 1 |
| Gate imports same deny_lists (no duplicate) | Task 3 |
| Gate computes dual-origin collision + umbrella (no inert bool defaults) | Task 3 |
| Collision matches canonical **and** aliases; plant-looking+alias → human | Task 3 |
| Umbrella reuses truth_anchor.is_compound_umbrella (no forked flavor/spice list) | Task 3 |
| Writer ontology-row apply/retract + write-failure leaves ledger pending | Task 4 |
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
