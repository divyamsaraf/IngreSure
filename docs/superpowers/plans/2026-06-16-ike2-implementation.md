# IKE-2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the IKE-2 ingredient resolution + compliance engine behind `IKE2_MODE`, validated in shadow mode, with a zero-false-Safe correctness guarantee.

**Architecture:** New `ike2_*` Postgres tables + a new `backend/core/knowledge/ike2/` module (input → resolver L1–L5 → compliance C1–C4 → response), running in parallel with the legacy resolver. Decisions and rationale are in `docs/superpowers/specs/2026-06-16-ike2-design.md`.

**Tech Stack:** Python 3.11, pytest, Supabase/PostgreSQL, Redis, existing `core.*` packages.

## Global Constraints

- Tests run from `backend/`: `pytest tests/...` (pytest.ini: `pythonpath = .`, `testpaths = tests`). Imports use `from core....`.
- TDD is mandatory: no production code without a failing test first (superpowers:test-driven-development).
- Correctness invariant (fail-closed): never emit firm SAFE from uncertain/untrusted knowledge. WARN→Depends, never SAFE.
- Verdict: internal 4-tier `FAIL > WARN > UNCERTAIN > SAFE`; response maps to external `NOT_SAFE/UNCERTAIN/SAFE`.
- Allergen model: full boolean flags; `animal_species` retained for halal/kosher meat species only.
- Alias uniqueness: global only for `e_number,cas_number,fda_number,iupac_name`; region-scoped otherwise.
- No runtime fuzzy; no LLM in resolver/verdict path; no Postgres cache read on hot path.
- Do not modify legacy `ingredient_*` tables or the legacy resolver during build.
- Trust gate is `core.evaluation.resolution_trust.is_trusted_for_compliance`.
- One deterministic core: compliance never forks verdict logic by audience; only the response layer varies (B2B strict+full-data, B2C severity-aware). Spec §4A.
- Restriction severity `medical|preference` on the profile; unknown defaults to `medical` (fail-closed). `may_contain`: medical→FAIL, preference→WARN+statement; always in audit. Spec §4A.
- `caution_reasons[]` is an annotation, never a verdict tier, never upgrades to SAFE. Spec §4A.
- Alcohol via `alcohol_role` (`ingredient`→FAIL, `fermentation_trace`→WARN, unknown→WARN); compound terms ("spices"/"natural flavors")→`verdict_cap=WARN`; untrusted trace→UNCERTAIN (never Avoid/SAFE). Spec §4B.
- **E-number expansion (2026-06-17):** Full 330-code catalog → generated L1 map + layer1 bulk inject. See `docs/superpowers/specs/2026-06-17-ike2-e-number-expansion-design.md`. Tier A=LOCKED, Tier B=verdict_cap WARN + compliance uncertainty gating.

---

## Task 1: IKE-2 verdict types + aggregation

**Files:**
- Create: `backend/core/knowledge/ike2/__init__.py`
- Create: `backend/core/knowledge/ike2/verdict.py`
- Test: `backend/tests/ike2/test_verdict.py`

**Interfaces:**
- Produces: `Verdict` (`Enum`: `FAIL, WARN, UNCERTAIN, SAFE`); `aggregate(verdicts: list[Verdict]) -> Verdict` (most severe wins); `to_external(v: Verdict) -> str` (→ `"NOT_SAFE"|"UNCERTAIN"|"SAFE"`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/ike2/test_verdict.py
from core.knowledge.ike2.verdict import Verdict, aggregate, to_external


def test_aggregate_most_severe_wins():
    assert aggregate([Verdict.SAFE, Verdict.WARN, Verdict.SAFE]) == Verdict.WARN
    assert aggregate([Verdict.SAFE, Verdict.FAIL, Verdict.WARN]) == Verdict.FAIL
    assert aggregate([Verdict.SAFE, Verdict.SAFE]) == Verdict.SAFE
    assert aggregate([]) == Verdict.UNCERTAIN


def test_warn_maps_to_depends_never_safe():
    assert to_external(Verdict.WARN) == "UNCERTAIN"
    assert to_external(Verdict.UNCERTAIN) == "UNCERTAIN"
    assert to_external(Verdict.FAIL) == "NOT_SAFE"
    assert to_external(Verdict.SAFE) == "SAFE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/ike2/test_verdict.py -v`
Expected: FAIL — `ModuleNotFoundError: core.knowledge.ike2.verdict`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/core/knowledge/ike2/verdict.py
from enum import IntEnum


class Verdict(IntEnum):
    SAFE = 0
    UNCERTAIN = 1
    WARN = 2
    FAIL = 3


def aggregate(verdicts):
    if not verdicts:
        return Verdict.UNCERTAIN
    return max(verdicts)


_EXTERNAL = {
    Verdict.FAIL: "NOT_SAFE",
    Verdict.WARN: "UNCERTAIN",
    Verdict.UNCERTAIN: "UNCERTAIN",
    Verdict.SAFE: "SAFE",
}


def to_external(v):
    return _EXTERNAL[v]
```

(Add empty `backend/core/knowledge/ike2/__init__.py`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/ike2/test_verdict.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/__init__.py backend/core/knowledge/ike2/verdict.py backend/tests/ike2/test_verdict.py
git commit -m "feat(ike2): verdict types + most-severe aggregation"
```

---

## Task 2: Truth Anchor module

**Files:**
- Create: `backend/core/knowledge/ike2/truth_anchor.py`
- Test: `backend/tests/ike2/test_truth_anchor.py`

**Interfaces:**
- Consumes: nothing (hardcoded dict).
- Produces: `lookup(normalized_key: str) -> Optional[TruthAnchorFact]` where `TruthAnchorFact` has `canonical_name: str`, flags dict, `knowledge_state="LOCKED"`. Start with the safety-critical set (gelatin→pork/animal, carmine/E120→insect/animal, lard→pork, isinglass→fish, shellac→insect, ethanol→alcohol). Full ~80-entry list filled during this task.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/ike2/test_truth_anchor.py
from core.knowledge.ike2.truth_anchor import lookup


def test_gelatin_is_animal_and_locked():
    fact = lookup("gelatin")
    assert fact is not None
    assert fact.flags["animal_origin"] is True
    assert fact.knowledge_state == "LOCKED"


def test_carmine_e120_is_insect():
    for key in ("carmine", "e120", "cochineal"):
        fact = lookup(key)
        assert fact is not None, key
        assert fact.flags["insect_derived"] is True


def test_unknown_key_returns_none():
    assert lookup("totally_unknown_thing_xyz") is None
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && pytest tests/ike2/test_truth_anchor.py -v`
Expected: FAIL — module/function missing.

- [ ] **Step 3: Minimal implementation**

```python
# backend/core/knowledge/ike2/truth_anchor.py
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class TruthAnchorFact:
    canonical_name: str
    flags: dict
    knowledge_state: str = "LOCKED"


def _f(**kw):
    return kw


_ANCHORS: dict[str, TruthAnchorFact] = {}


def _add(keys, canonical, flags):
    fact = TruthAnchorFact(canonical_name=canonical, flags=flags)
    for k in keys:
        _ANCHORS[k] = fact


_add(["gelatin", "gelatine"], "gelatin", _f(animal_origin=True))
_add(["carmine", "e120", "cochineal", "carminic acid"], "carmine",
     _f(animal_origin=True, insect_derived=True))
_add(["lard", "tallow"], "animal_fat", _f(animal_origin=True, animal_species="pig"))
_add(["isinglass"], "isinglass", _f(animal_origin=True, animal_species="fish", fish_source=True))
_add(["shellac", "e904"], "shellac", _f(animal_origin=True, insect_derived=True))
_add(["ethanol", "ethyl alcohol"], "ethanol", _f(alcohol_content=1.0))
# ... extend to the full ~80-entry safety-critical list during this task ...


def lookup(normalized_key: str) -> Optional[TruthAnchorFact]:
    return _ANCHORS.get(normalized_key)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && pytest tests/ike2/test_truth_anchor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/truth_anchor.py backend/tests/ike2/test_truth_anchor.py
git commit -m "feat(ike2): truth anchor override dictionary"
```

---

## Task 3: SQL migration for `ike2_*` schema + constraints

**Files:**
- Create: `supabase/migrations/20260616000000_ike2_schema.sql`
- Test: `backend/tests/ike2/test_ike2_schema_constraints.py` (runs against local Supabase)

**Interfaces:**
- Produces tables in §5 of the spec, with CHECK constraints and the two alias unique indexes.

- [ ] **Step 1: Write the failing test** (constraints reject illegal rows)

```python
# backend/tests/ike2/test_ike2_schema_constraints.py
import os
import pytest
from core.knowledge.ingredient_db import get_supabase_client  # existing client helper

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL"), reason="needs local supabase"
)


def test_insect_implies_animal_constraint(db_admin):
    # inserting insect_derived=True with animal_origin=False must be rejected
    with pytest.raises(Exception):
        db_admin.table("ike2_ingredient_groups").insert({
            "canonical_name": "bad_insect_row",
            "animal_origin": False,
            "insect_derived": True,
        }).execute()


def test_verified_requires_source(db_admin):
    with pytest.raises(Exception):
        db_admin.table("ike2_ingredient_groups").insert({
            "canonical_name": "bad_verified_row",
            "knowledge_state": "VERIFIED",
            "primary_source_url": None,
        }).execute()
```

(Provide a `db_admin` fixture in `backend/tests/ike2/conftest.py` returning a service-role client; skip if env not set.)

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && pytest tests/ike2/test_ike2_schema_constraints.py -v`
Expected: FAIL — tables do not exist yet (insert raises for the wrong reason / collection missing).

- [ ] **Step 3: Write the migration**

Author `supabase/migrations/20260616000000_ike2_schema.sql` with all `ike2_*` tables, enums, the CHECK constraints (`insect_implies_animal`, `egg/dairy/fish/shellfish_implies_animal`, `verified_requires_source`, dual-origin-requires-uncertainty), the two alias unique indexes, RLS enabled with service-role-only policies (mirror `supabase/migrations/20260306000000_enable_rls.sql`), and `ike2_v_alias_resolution` view. Include `alcohol_role TEXT NOT NULL DEFAULT 'none' CHECK (alcohol_role IN ('none','ingredient','fermentation_trace'))` on `ike2_ingredient_groups`. Apply: `supabase db reset` (local) or `supabase migration up`.

Also add a profile-side `severity` field: each user restriction carries `severity TEXT NOT NULL DEFAULT 'medical' CHECK (severity IN ('medical','preference'))`. If the current profile/restriction model has no such column, add it with default `'medical'` (fail-closed) in this migration; locate it via the existing restriction-rule/profile tables before authoring.

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && pytest tests/ike2/test_ike2_schema_constraints.py -v`
Expected: PASS (constraints reject the bad rows)

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/20260616000000_ike2_schema.sql backend/tests/ike2/conftest.py backend/tests/ike2/test_ike2_schema_constraints.py
git commit -m "feat(ike2): schema migration with safety CHECK constraints + RLS"
```

---

## Task 4: Input layer (sanitize → decompose → normalize)

**Files:**
- Create: `backend/core/knowledge/ike2/input_layer.py`
- Test: `backend/tests/ike2/test_input_layer.py`

**Interfaces:**
- Consumes: existing `normalize_ingredient_key` from `core.normalization.normalizer`.
- Produces: `to_atoms(raw: str) -> list[str]` — sanitizes, expands compounds (`"sugar (from beet)"` → `["sugar"]`; `"emulsifier (soy lecithin)"` → `["soy lecithin"]`), splits on separators, returns normalized atoms.

- [ ] **Step 1: Failing test**

```python
# backend/tests/ike2/test_input_layer.py
from core.knowledge.ike2.input_layer import to_atoms


def test_compound_parenthetical_expands_to_inner_source():
    assert "soy lecithin" in to_atoms("emulsifier (soy lecithin)")


def test_source_qualifier_reduces_to_base():
    atoms = to_atoms("sugar (from beet)")
    assert atoms == ["sugar"]


def test_splits_multiple_ingredients():
    atoms = to_atoms("water, salt, citric acid")
    assert atoms == ["water", "salt", "citric acid"]
```

- [ ] **Step 2: Run to verify fail.** `cd backend && pytest tests/ike2/test_input_layer.py -v`

- [ ] **Step 3: Minimal implementation** — implement `to_atoms` using `normalize_ingredient_key`; decomposition rules: split on `,`/`;`, for `X (Y)` decide base-vs-inner by a small qualifier set (`from`, `derived from` → base; otherwise inner is the specific ingredient).

- [ ] **Step 4: Run to verify pass.**

- [ ] **Step 5: Commit** `feat(ike2): input layer decomposition + normalization`

---

## Task 5: DB store + single-query resolution read

**Files:**
- Create: `backend/core/knowledge/ike2/stores/__init__.py`, `backend/core/knowledge/ike2/stores/db.py`
- Test: `backend/tests/ike2/test_store_db.py`

**Interfaces:**
- Produces: `resolve_alias(normalized_alias: str, region: str|None) -> Optional[GroupRow]` reading `ike2_v_alias_resolution`, filtering active rows; `disambiguate(normalized_alias, region) -> Literal["unique","ambiguous","none"]`.

- [ ] **Step 1: Failing test** (seed two rows for "yam", assert region resolves, region-less is ambiguous)

```python
# backend/tests/ike2/test_store_db.py
import os, pytest
pytestmark = pytest.mark.skipif(not os.getenv("SUPABASE_URL"), reason="needs local supabase")
from core.knowledge.ike2.stores.db import resolve_alias, disambiguate


def test_yam_resolves_by_region(seed_yam):
    g = resolve_alias("yam", region="IN")
    assert g.canonical_name == "elephant_foot_yam"


def test_yam_no_region_is_ambiguous(seed_yam):
    assert disambiguate("yam", region=None) == "ambiguous"
```

(`seed_yam` fixture inserts both candidates + disambiguation rows.)

- [ ] **Step 2–4:** Run fail → implement reads against the view + `ike2_alias_disambiguation` → run pass.

- [ ] **Step 5: Commit** `feat(ike2): db store with region-scoped alias resolution`

---

## Task 6: Resolver L1–L5 orchestration

**Files:**
- Create: `backend/core/knowledge/ike2/resolver.py`
- Test: `backend/tests/ike2/test_resolver.py`

**Interfaces:**
- Consumes: `truth_anchor.lookup`, `stores.db.resolve_alias/disambiguate`, existing Redis/LRU cache, `is_trusted_for_compliance`.
- Produces: `resolve(atom: str, region: str|None) -> ResolvedIngredient` with fields `group`, `source`, `confidence_band`, `trusted: bool`, `resolution_layer: str`, `status: Literal["resolved","uncertain"]`.

- [ ] **Step 1: Failing tests** (the safety-critical behaviors)

```python
# backend/tests/ike2/test_resolver.py
from core.knowledge.ike2.resolver import resolve


def test_truth_anchor_overrides_db(monkeypatch):
    # even if DB says gelatin is plant, truth anchor wins
    import core.knowledge.ike2.stores.db as db
    monkeypatch.setattr(db, "resolve_alias", lambda *a, **k: _plant_gelatin())
    r = resolve("gelatin", region=None)
    assert r.group.flags["animal_origin"] is True
    assert r.resolution_layer == "L1_truth_anchor"


def test_unknown_ingredient_is_uncertain_not_safe(monkeypatch):
    import core.knowledge.ike2.stores.db as db
    monkeypatch.setattr(db, "resolve_alias", lambda *a, **k: None)
    monkeypatch.setattr(db, "disambiguate", lambda *a, **k: "none")
    r = resolve("totally_unknown_xyz", region=None)
    assert r.status == "uncertain"


def test_ambiguous_alias_no_region_uncertain(monkeypatch):
    import core.knowledge.ike2.stores.db as db
    monkeypatch.setattr(db, "disambiguate", lambda *a, **k: "ambiguous")
    r = resolve("yam", region=None)
    assert r.status == "uncertain"
```

(`_plant_gelatin()` builds a fake GroupRow with animal_origin=False.)

- [ ] **Step 2–4:** Run fail → implement L1→L2→L3(+disambiguation)→L4→L5 in order; ambiguous-no-region and miss both return `status="uncertain"`; set `trusted` via `is_trusted_for_compliance` → run pass.

- [ ] **Step 5: Commit** `feat(ike2): L1-L5 resolver with fail-closed unknown/ambiguous handling`

---

## Task 7: Compliance C1–C4

**Files:**
- Create: `backend/core/knowledge/ike2/compliance.py`
- Test: `backend/tests/ike2/test_compliance.py`

**Interfaces:**
- Consumes: `ResolvedIngredient`, profile (with per-restriction `severity`), `ike2_restriction_rules` (inject as list for tests), `Verdict`.
- Produces: `evaluate(resolved, profile, rules) -> ComplianceResult` where `ComplianceResult` has `verdict: Verdict`, `matched_contains[]`, `matched_may_contain[]`, `caution_reasons[]`, and a per-restriction breakdown. C1 truth-anchor recheck → C2 rule eval (gated by `min_knowledge_state`) → C3 uncertainty propagation (severity/trace, alcohol_role, compound `verdict_cap`, untrusted→UNCERTAIN, DISCOVERED→WARN) → C4 `aggregate` most-severe across all restrictions × ingredients. Tests below assert `.verdict`.

- [ ] **Step 1: Failing tests** (uncertainty propagation + caps)

```python
# backend/tests/ike2/test_compliance.py
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.verdict import Verdict


def test_unclassified_never_safe(rule_vegan):
    r = _resolved(animal_origin=False, knowledge_state="UNCLASSIFIED", trusted=False)
    assert evaluate([r], profile=_vegan(), rules=[rule_vegan]) != Verdict.SAFE


def test_discovered_pass_caps_to_warn(rule_vegan):
    r = _resolved(animal_origin=False, knowledge_state="DISCOVERED", trusted=True)
    assert evaluate([r], profile=_vegan(), rules=[rule_vegan]) == Verdict.WARN


def test_verdict_cap_caps_to_warn(rule_vegan):
    r = _resolved(animal_origin=False, knowledge_state="VERIFIED", trusted=True, verdict_cap="WARN")
    assert evaluate([r], profile=_vegan(), rules=[rule_vegan]) == Verdict.WARN


def test_untrusted_resolution_never_safe(rule_vegan):
    r = _resolved(animal_origin=False, knowledge_state="VERIFIED", trusted=False)
    assert evaluate([r], profile=_vegan(), rules=[rule_vegan]) != Verdict.SAFE


def test_animal_fails_vegan(rule_vegan):
    r = _resolved(animal_origin=True, knowledge_state="LOCKED", trusted=True)
    assert evaluate([r], profile=_vegan(), rules=[rule_vegan]).verdict == Verdict.FAIL


def test_medical_may_contain_fails_preference_warns(rule_peanut):
    r = _resolved(peanut_source=True, trusted=True, trace=True)  # may_contain peanut
    assert evaluate([r], _profile("peanut", "medical"), [rule_peanut]).verdict == Verdict.FAIL
    assert evaluate([r], _profile("peanut", "preference"), [rule_peanut]).verdict == Verdict.WARN


def test_unknown_severity_defaults_medical(rule_peanut):
    r = _resolved(peanut_source=True, trusted=True, trace=True)
    assert evaluate([r], _profile("peanut", severity=None), [rule_peanut]).verdict == Verdict.FAIL


def test_alcohol_ingredient_fails_trace_warns(rule_no_alcohol):
    ing = _resolved(alcohol_role="ingredient", trusted=True)
    ferm = _resolved(alcohol_role="fermentation_trace", trusted=True)
    assert evaluate([ing], _profile("alcohol", "medical"), [rule_no_alcohol]).verdict == Verdict.FAIL
    assert evaluate([ferm], _profile("alcohol", "medical"), [rule_no_alcohol]).verdict == Verdict.WARN


def test_compound_term_caps_to_warn(rule_jain):
    r = _resolved(canonical="spices", knowledge_state="VERIFIED", trusted=True, verdict_cap="WARN")
    assert evaluate([r], _profile("jain", "preference"), [rule_jain]).verdict == Verdict.WARN


def test_untrusted_trace_is_uncertain_not_avoid(rule_peanut):
    r = _resolved(peanut_source=True, trusted=False, trace=True)  # low-confidence inferred trace
    assert evaluate([r], _profile("peanut", "medical"), [rule_peanut]).verdict == Verdict.UNCERTAIN
```

(Helpers `_resolved(...)`, `_profile(restriction, severity)`, `_vegan()`, and `rule_*` fixtures build minimal objects.)

- [ ] **Step 2–4:** Run fail → implement C1 (truth-anchor recheck) → C2 (rule eval gated by `min_knowledge_state`) → C3 (UNCLASSIFIED/untrusted-definite never SAFE; DISCOVERED pass→WARN; apply `verdict_cap`; trace×severity: medical→FAIL, preference→WARN; alcohol_role: ingredient→FAIL, fermentation_trace→WARN; untrusted trace→UNCERTAIN; populate `caution_reasons`) → C4 (`aggregate` across all restrictions × ingredients) → run pass.

- [ ] **Step 5: Commit** `feat(ike2): compliance C1-C4 with conservative uncertainty propagation`

---

## Task 8: Response layer + IdentityAssembler

**Files:**
- Create: `backend/core/knowledge/ike2/response.py`
- Test: `backend/tests/ike2/test_response.py`

**Interfaces:**
- Produces: `assemble(resolved, result: ComplianceResult, profile, mode="b2c") -> dict` with `external_verdict` (via `to_external`), `audit[]` (one `triggered` flag per ingredient from a single `is_triggered(resolved, profile)` shared with compliance), `caution_reasons[]`, `schema_version`. `mode="b2b"` additionally returns the full breakdown (`matched_contains`, `matched_may_contain`, per-restriction `severity`, raw 4-tier) and applies the strict default (trace→NOT_SAFE) for the headline; `mode="b2c"` keeps the severity-aware verdict from compliance and renders `caution_reasons` as plain-language statements. The deterministic core (compliance) is identical for both; only presentation differs.

- [ ] **Step 1: Failing test** (Yam-class audit + mode behavior)

```python
# backend/tests/ike2/test_response.py
from core.knowledge.ike2.response import assemble, is_triggered
from core.knowledge.ike2.verdict import Verdict


def test_non_triggering_ingredient_not_marked_triggered():
    yam = _resolved(canonical="sweet_potato", animal_origin=False)
    payload = assemble([yam], _result(Verdict.SAFE), profile=_jain())
    card = next(c for c in payload["audit"] if c["canonical_name"] == "sweet_potato")
    assert card["triggered"] is False


def test_external_verdict_mapping():
    payload = assemble([], _result(Verdict.WARN, caution=["may_contain_trace"]), profile=_jain())
    assert payload["external_verdict"] == "UNCERTAIN"
    assert "may_contain_trace" in payload["caution_reasons"]


def test_b2b_mode_exposes_full_breakdown_and_strict_headline():
    r = _result(Verdict.WARN, matched_may_contain=["peanut"])  # preference trace → WARN in core
    payload = assemble([], r, profile=_pref_peanut(), mode="b2b")
    assert payload["matched_may_contain"] == ["peanut"]
    assert payload["external_verdict"] == "NOT_SAFE"  # b2b strict treats trace as trigger
```

- [ ] **Step 2–4:** Run fail → implement `is_triggered` (single source of truth), `assemble` with `mode`, and `caution_reasons` passthrough → run pass.

- [ ] **Step 5: Commit** `feat(ike2): response layer + IdentityAssembler (fixes Yam-class audit bug)`

---

## Task 9: ETL — staging load + reject quarantine

**Files:**
- Create: `backend/core/knowledge/ike2/etl/seed_from_ontology.py`
- Create: `backend/core/knowledge/ike2/etl/validate.py`
- Test: `backend/tests/ike2/test_etl_validate.py`

**Interfaces:**
- Produces: `validate_rows(rows) -> tuple[list[ok], list[reject]]` applying the same CHECK predicates in Python before merge; merge writes ok→prod, reject→`stg_rejects`.

- [ ] **Step 1: Failing test**

```python
# backend/tests/ike2/test_etl_validate.py
from core.knowledge.ike2.etl.validate import validate_rows


def test_reject_row_quarantined_batch_continues():
    rows = [
        {"canonical_name": "ok_milk", "animal_origin": True, "dairy_source": True},
        {"canonical_name": "bad", "animal_origin": False, "insect_derived": True},
    ]
    ok, rejects = validate_rows(rows)
    assert [r["canonical_name"] for r in ok] == ["ok_milk"]
    assert rejects[0]["violated_constraint"] == "insect_implies_animal"
```

- [ ] **Step 2–4:** Run fail → implement `validate_rows` mirroring CHECK predicates → run pass.

- [ ] **Step 5: Commit** `feat(ike2): ETL validate + reject quarantine`

---

## Task 10: ETL — source-conflict reconciliation

**Files:**
- Create: `backend/core/knowledge/ike2/etl/reconcile.py`
- Test: `backend/tests/ike2/test_etl_reconcile.py`

**Interfaces:**
- Produces: `reconcile(existing: GroupRow, incoming: dict, incoming_source: str) -> ReconcileResult` with `merged_flags`, `knowledge_state`, `needs_review: bool`, applying precedence + most-restrictive.

- [ ] **Step 1: Failing test**

```python
# backend/tests/ike2/test_etl_reconcile.py
from core.knowledge.ike2.etl.reconcile import reconcile


def test_conflict_takes_most_restrictive_and_flags_review():
    existing = _group(dairy_source=False, knowledge_state="AUTO_CLASSIFIED", source="usda")
    res = reconcile(existing, {"dairy_source": True}, incoming_source="openfoodfacts")
    assert res.merged_flags["dairy_source"] is True       # most restrictive wins
    assert res.needs_review is True
    assert res.knowledge_state in ("DISCOVERED", "UNCLASSIFIED")  # dropped


def test_lower_tier_cannot_override_verified():
    existing = _group(dairy_source=True, knowledge_state="VERIFIED", source="human")
    res = reconcile(existing, {"dairy_source": False}, incoming_source="openfoodfacts")
    assert res.merged_flags["dairy_source"] is True       # higher tier preserved
```

- [ ] **Step 2–4:** Run fail → implement precedence table + most-restrictive + knowledge_state drop → run pass.

- [ ] **Step 5: Commit** `feat(ike2): ETL source-conflict reconciliation policy`

---

## Task 11: Shadow comparator + `IKE2_MODE` wiring

**Files:**
- Modify: `backend/core/config.py` (add `IKE2_MODE`)
- Create: `backend/core/knowledge/ike2/shadow/comparator.py`
- Modify: `backend/core/knowledge/canonicalizer.py` (shadow hook only; legacy still drives output)
- Test: `backend/tests/ike2/test_shadow_comparator.py`

**Interfaces:**
- Produces: `compare(legacy_verdict, ike2_verdict, ...) -> dict` row for `ike2_shadow_diffs`; classifies `match` and `false_safe_regression` (legacy/expected NOT_SAFE while ike2 SAFE).

- [ ] **Step 1: Failing test**

```python
# backend/tests/ike2/test_shadow_comparator.py
from core.knowledge.ike2.shadow.comparator import compare


def test_flags_false_safe_regression():
    row = compare(legacy_verdict="NOT_SAFE", ike2_verdict="SAFE", raw_input="x")
    assert row["false_safe_regression"] is True


def test_match_when_equal():
    row = compare(legacy_verdict="SAFE", ike2_verdict="SAFE", raw_input="x")
    assert row["match"] is True
    assert row["false_safe_regression"] is False
```

- [ ] **Step 2–4:** Run fail → implement `compare`; wire `IKE2_MODE=shadow` so legacy output is returned unchanged and a diff row is logged async → run pass. Verify legacy path untouched: `cd backend && pytest tests/test_compliance_engine.py tests/test_yam_jain_audit.py -v` (must stay green).

- [ ] **Step 5: Commit** `feat(ike2): shadow comparator + IKE2_MODE wiring (legacy unaffected)`

---

## Task 12: Golden corpus harness + safety-budget gate

**Files:**
- Create: `backend/tests/ike2/golden/corpus.jsonl` (labeled rows)
- Create: `backend/tests/ike2/test_golden_safety_budget.py`

**Interfaces:**
- Each corpus row: `{raw_input, profile, region, severity, expected_verdict, rationale, source_url}`. `expected_verdict ∈ {SAFE, UNCERTAIN, NOT_SAFE}` (external 3-tier); optional `expected_internal` (4-tier).

- [ ] **Step 1: Write the gate test** (fails until engine + corpus exist)

```python
# backend/tests/ike2/test_golden_safety_budget.py
import json, pathlib
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.input_layer import to_atoms
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.verdict import to_external

CORPUS = pathlib.Path(__file__).parent / "golden" / "corpus.jsonl"


def _run_case(case):
    atoms = to_atoms(case["raw_input"])
    resolved = [resolve(a, case.get("region")) for a in atoms]
    # rules loaded from ike2_restriction_rules for the profile in real run
    return to_external(evaluate(resolved, case["profile"], rules=_rules_for(case["profile"])))


def test_zero_false_safe_regressions():
    false_safes = []
    for line in CORPUS.read_text().splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        got = _run_case(case)
        if got == "SAFE" and case["expected_verdict"] == "NOT_SAFE":
            false_safes.append(case["raw_input"])
    assert false_safes == [], f"FALSE-SAFE regressions: {false_safes}"
```

- [ ] **Step 2:** Run → fails (engine/corpus incomplete). Seed corpus from the regression set (Yam/Jain, E120, halal pork, fish+shellfish, medical-vs-preference `may_contain`, alcohol ingredient-vs-trace, "spices"/"natural flavors" compound) plus coverage matrix.

- [ ] **Step 3–4:** Iterate engine until `test_zero_false_safe_regressions` passes with a corpus covering every restriction category × knowledge_state × ambiguous alias.

- [ ] **Step 5: Commit** `test(ike2): golden corpus + zero-false-safe gate`

---

## Task 13: Full test sweep + shadow soak readiness

- [ ] **Step 1:** Run the entire IKE-2 suite and the legacy suites together:

Run: `cd backend && pytest tests/ike2-v && pytest tests/test_compliance_engine.py tests/test_yam_jain_audit.py tests/test_restrictions_comprehensive.py -v`
Expected: all PASS; legacy unchanged.

- [ ] **Step 2:** Enable `IKE2_MODE=shadow` in staging; confirm `ike2_shadow_diffs` populates and `false_safe_regression` count is queryable.

- [ ] **Step 3: Commit / tag** `chore(ike2): shadow-ready`

---

## Cutover (post-implementation, gated)

Follow the spec §8 gates. Do not promote to `primary` until: 0 false-Safe on golden, 0 false-Safe on a 7-day shadow soak, latency gates met. Sequence: `shadow` (staging 2wk) → `primary` (staging QA) → `primary`+`fallback` (prod) → monitor 30d → `primary` only. Rollback = set `IKE2_MODE=fallback` or `off`.

## Self-Review (writing-plans)

- **Spec coverage:** every Correctness-Contract guarantee maps to a test (Tasks 6–8, 12); allergen booleans (Task 3), alias scoping/disambiguation (Tasks 3, 5, 6), verdict map (Task 1), severity/trace + alcohol + compound + untrusted-trace (Task 7), presentation modes + caution (Task 8), ETL reject + conflict (Tasks 9, 10), shadow gate vs ground truth (Tasks 11, 12).
- **§4A/§4B coverage:** one-core/two-presentation (Task 8 `mode`), severity default-medical (Tasks 3, 7), `caution_reasons` non-tier (Tasks 7, 8), alcohol_role + compound `verdict_cap` + trace provenance (Task 7).
- **Placeholders:** Truth Anchor full list (Task 2) and corpus rows (Task 12) are explicitly content-to-fill during their tasks, not hidden TODOs.
- **Type consistency:** `Verdict`, `ResolvedIngredient`, `to_external`, `is_triggered`, `is_trusted_for_compliance` referenced consistently across tasks.

---

## Activation Hardening (post-build)

Status of the steps that make IKE-2 safe to switch on, beyond the per-task build above.

**Done:**
- **Coverage guard.** `compliance.evaluate` now degrades any profile restriction with no matching rule to `UNCERTAIN` (`uncovered_restriction:<name>` caution), closing a latent false-SAFE that would activate the moment rules were partially seeded. `backend/core/knowledge/ike2/compliance.py`.
- **Rule seed + loader.** `core/knowledge/ike2/rules.py` is the single source of truth (`RULE_SEED`, `seeded_rules()`, `load_rules()`), mapping the DB row shape (`category/field/action`) to the compliance shape (`restriction/kind/trigger_flag/min_knowledge_state`). Live seed in `supabase/migrations/20260617000000_ike2_seed_restriction_rules.sql` (idempotent via a `(category, field, coalesce(region,'GLOBAL'))` unique index). Scope: boolean allergen/medical flags, alcohol rule, and multi-field religious/lifestyle rules (`animal_species`, `meat_fish_derived`, `alcohol_content`) aligned with `data/restrictions.json`.
- **Live-row safety test.** `tests/ike2/test_resolution_safety_db.py` seeds a real peanut group, resolves it through the actual `ike2_v_alias_resolution` view, and asserts non-SAFE end to end (skips without local Supabase).
- **Shadow wiring.** `core/knowledge/ike2/shadow/runner.py` runs the full IKE-2 pipeline when `IKE2_MODE=='shadow'`, logging divergences (and the `false_safe_regression` flag) to `ike2_shadow_diffs`. Hooked into `core/bridge.py::run_new_engine_chat`; fail-safe so the legacy verdict is never altered. No-op when `IKE2_MODE` is `off`.
- **Trace / `may_contain`.** `input_layer.parse_atoms` detects product-level trace sections (same markers as `bridge.preprocess_ingredient_list`); `seam.to_compliance_input(..., trace=atom.trace)` and `shadow/runner.py` pass trace through to compliance (medical trace → FAIL).
- **Truth Anchor expansion.** `truth_anchor.py` holds ~80 LOCKED safety-critical facts (allergens, E-numbers, alcohol, pork/cow/shellfish, insect-derived); `test_truth_anchor.py` guards count and key flags. Full 330-code E-number pipeline: [E-Number Expansion Design](../specs/2026-06-17-ike2-e-number-expansion-design.md).
- **Golden corpus.** `tests/ike2/golden/corpus.jsonl` (53+ labeled rows: allergens, halal/kosher/jain/vegetarian, alcohol, unknown fail-closed, trace); `test_golden_safety_budget.py` runs resolver → `to_compliance_input` → `seeded_rules()` → `evaluate`; `test_zero_false_safe_regressions` is the cutover gate.
- **Label corpus shadow.** 457 rows in `tests/fixtures/labels/corpus.jsonl`; `scripts/ike2_label_corpus_shadow.py` enforces ≥85% match + zero false-Safe (CI). Current: ~99.5% match, 1 benign mismatch (`may_contain_3`: legacy SAFE vs IKE-2 UNCERTAIN — not false-Safe).
- **E-number catalog.** Full pipeline per [E-Number Expansion Design](../specs/2026-06-17-ike2-e-number-expansion-design.md); CI drift check on `truth_anchor_e_numbers.json` + `layer1_e_numbers.json`.
- **Gelatin halal/kosher (June 2026).** IKE-2 `_species_is_porcine()` matches `animal_species` containing `porcine`; legacy `data/restrictions.json` adds `contains porcine` rules. Fixes gelatin (`bovine/porcine/fish depending on source`) incorrectly returning SAFE for halal/kosher.
- **Stress harness.** `tests/fixtures/labels/stress_label.py` + `scripts/stress_test_long_label.py` — 200+ ingredient labels with junk; legacy/IKE-2 verdict parity and latency benchmarks.

**Staging shadow soak (operational, not a fixed wait):**

1. Set `IKE2_MODE=shadow` in staging env (`backend/core/config.py` reads the env var).
2. Deploy; legacy output is unchanged; divergences append to `ike2_shadow_diffs`.
3. Monitor regressions on demand or via cron:

```bash
cd backend && python scripts/ike2_shadow_soak_report.py --days 7
cd backend && python scripts/ike2_shadow_soak_report.py --days 7 --fail-on-regression  # CI gate
```

Cutover gate: `false_safe_regression` count must stay **0** over the soak window before promoting to `primary` (per spec §8).

**Open (tracked):** `primary` / `fallback` cutover modes in `bridge.py`; L2 cache, L4 regional layer, L5 API enrichment on the hot path; 7-day staging shadow soak (operational).

**Test suite (June 2026):** **1193** backend tests collected. IKE-2 subdirectory: resolver, compliance, rules, shadow, ETL, E-numbers, golden, pipeline e2e. Run `pytest tests/ike2/ -v` and CI shadow gate before any cutover discussion.
