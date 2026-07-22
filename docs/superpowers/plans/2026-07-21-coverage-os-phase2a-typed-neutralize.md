# Coverage OS Phase 2a — Typed Neutralize Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Phase 2a — a single `neutralize.apply_policies` engine driven by ontology `role` data, thin callers in `compound_expansion` and `commodity_head`, role promotions through Phase 1 ledger/writer/gate, and dual-emit audit folding via `derived_from`.

**Architecture:** Closed `PolicyType` enum + `role_index` from ontology; `apply_policies` owns plant_mod / dairy_head / process_keep / culinary_keep (partner animalish via `deny_lists.is_animalish`). Expansion and facet call only that API. Roles promoted with human_fail_closed for role-only payloads. Private plant/keep Sets in `compound_expansion` are deleted only after roles are seeded and goldens pass.

**Tech Stack:** Python 3.11, pytest, existing Coverage OS (`deny_lists`, `hybrid_gate`, `promote_writer`, `promote_ledger`, `profile_matrix`), IKE-2 `truth_anchor` / `local_ontology` / `etl.adapt`.

**Spec:** `docs/superpowers/specs/2026-07-21-coverage-os-phase2a-typed-neutralize-design.md`

## Global Constraints

- `neutralize.apply_policies` is the **only** neutralize behavior surface; no private plant/keep Sets left in `compound_expansion` after migration completes.
- `role` values are exactly: `plant_mod` | `dairy_head` | `process_keep` | `culinary_keep`.
- `role` is the only new ontology field; plant_mod partner = `role=dairy_head` **or** `deny_lists.is_animalish(flags)` — **no** new dairy/meat keyword list in `neutralize.py`.
- Conflict: if both plant_mod and dairy_head could apply, **plant_mod wins**.
- Plant_mod emission: whole phrase + plant token; never bare dairy/meat from that pair.
- Relatedness: **`derived_from` only** (no `emission_group_id`); `display_map` = label remap only.
- Audit: one top-level card per user-typed phrase; derived hits fold into that card.
- Keep decision order inside `apply_policies`: (1) culinary/process roles → (2) plant_mod/dairy_head → (3) `truth_anchor.lookup(full_phrase)` → (4) **passthrough** `atoms=[phrase]` (no generic tear inside neutralize).
- **No-policy keyword extraction** (e.g. `garlic pasta` → `garlic`) stays in `compound_expansion` via existing `_RESTRICTED_KEYWORDS_*` / `find_sub_ingredients` — **not** reimplemented inside `neutralize.py`.
- Role-only promote → existing `human_fail_closed`; **no** new auto branch on `role`. `GateDecision.action` values are exactly `auto_promote` | `human_approval` | `rejected` (no `"human"`).
- Plant/keep Sets stay until roles seeded **and** goldens pass through `apply_policies`. `_RESTRICTED_KEYWORDS_*` are **not** deleted in 2a.
- No Phase 2b induction in this plan.

**Path sanity (verified 2026-07-21):**

| Path | Confirmed |
|------|-----------|
| `backend/core/compound_expansion.py` | `expand_compounds` → `Tuple[List[str], Dict[str, str]]` today; `_PLANT_MODIFIERS` / `_KEEP_WHOLE_SUFFIXES` / `_KEEP_AND_EXTRACT_WORDS` / `_RESTRICTED_KEYWORDS_*` / `find_sub_ingredients` |
| `backend/core/knowledge/ike2/commodity_head.py` | `_FORBIDDEN_STRIP`, `facet_reduction_candidates`, `simple_commodity_head` |
| `backend/core/knowledge/ike2/coverage_os/deny_lists.py` | `is_animalish(flags)` |
| `backend/core/knowledge/ike2/coverage_os/hybrid_gate.py` | `GateDecision.action: Literal["auto_promote","human_approval","rejected"]`; fail-closed → `action="human_approval"`, `rule_id="human_fail_closed"` |
| `backend/core/knowledge/ike2/etl/adapt.py` | `map_record(raw: dict, canonical_source: str, default_state: str)` — does not copy `role` today |
| `backend/core/parsing/chat_ingredients.py` | `PreparedChatIngredients(eval_names, compound_map={}, decomposed=None, label_text=None)`; `prepare_chat_ingredients` unpacks 2-tuple from `expand_compounds` |
| `backend/core/response_composer.py` | `build_ingredient_audit_payload(verdict, profile, ingredients, display_names=None, explanation_text="", explanation_source="template")` — no `derived_from` yet; groups use `status` in `{"avoid","depends","safe"}` |
| `backend/app.py` | Calls `build_ingredient_audit_payload(verdict=..., profile=..., ingredients=eval_ingredients, display_names=compound_map, ...)` ~L712; must also pass `derived_from` after Task 7 |

## Literal-code-trace discipline (mandatory)

Phase 1 hid real bugs behind prose until literal code was traced against tests. Phase 2a touches the **live** expansion path. After Tasks **1**, **2**, and **7**, do not mark the task done until a reviewer (or implementing agent) pastes the **actual branch order / merge logic** into the review notes and checks it against the named tests. Soft “looks right” sign-off is insufficient.

| Gate | After task | Trace must show |
|------|------------|-----------------|
| **LCT-1** | Task 1 | `apply_policies` conflict: plant_mod checked **before** dairy_head (or equivalent early-return); both token orders |
| **LCT-2** | Task 2 | Keep decision: culinary/process → plant_mod/dairy_head → `truth_anchor.lookup` → **passthrough** `[phrase]`; no inverted `if`; no generic tear list in neutralize |
| **LCT-3** | Task 7 | `derived_from` from `PolicyResult` → expand → `PreparedChatIngredients` → `build_ingredient_audit_payload` card merge |

## File map

| Path | Responsibility |
|------|----------------|
| `backend/core/knowledge/ike2/coverage_os/neutralize.py` | `PolicyType`, `PolicyResult`, `role_index`, `apply_policies` |
| `backend/core/knowledge/ike2/coverage_os/promote_writer.py` | Persist `role` on ontology_row; role-patch on existing rows; inverse |
| `backend/core/knowledge/ike2/etl/adapt.py` | Pass `role` through `map_record` |
| `backend/core/knowledge/ike2/stores/local_ontology.py` | Add `role` to `_NON_FLAG_ROW_KEYS`; expose role on facts / index |
| `backend/core/compound_expansion.py` | Thin wrap over `apply_policies`; return `derived_from_map`; delete private Sets last |
| `backend/core/knowledge/ike2/commodity_head.py` | Shared culinary keep via neutralize helpers; no parallel strip set for seeded heads |
| `backend/core/parsing/chat_ingredients.py` | Plumb `derived_from_map` on `PreparedChatIngredients` |
| `backend/core/response_composer.py` | Fold derived atoms into source phrase cards |
| `backend/app.py` | Pass `derived_from` into audit compose if needed |
| `backend/tests/ike2/coverage_os/test_neutralize*.py` | Unit + LCT-focused tests |
| `backend/tests/ike2/coverage_os/test_phase2a_*.py` | Writer/gate/integration exit C |
| `backend/tests/test_compound_umbrella_regressions.py` (+ new goldens) | Named compound bugs |

## Dependency order (do not reorder)

```text
Task 1 apply_policies core (plant_mod / dairy_head) ── LCT-1
Task 2 culinary / process + Tier-1 fallback ────────── LCT-2
Task 3 writer + adapt + local_ontology role plumbing
Task 4 role-only gate test + seed promotions (human)
Task 5 wire compound_expansion (Sets remain until Task 5d)
Task 6 commodity_head shared keep
Task 7 derived_from → audit composer ──────────────── LCT-3
Task 8 goldens + matrix smoke + exit C integration
```

---

### Task 1: `apply_policies` core — plant_mod / dairy_head (+ LCT-1)

**Files:**
- Create: `backend/core/knowledge/ike2/coverage_os/neutralize.py`
- Test: `backend/tests/ike2/coverage_os/test_neutralize_plant_dairy.py`

**Interfaces:**
- Consumes: `deny_lists.is_animalish(flags)`, injectable `lookup_flags(token) -> dict | None` and `lookup_role(token) -> str | None` (tests pass fakes; production uses role_index + ontology/truth_anchor flags)
- Produces:
  - `PolicyType` = `Literal["plant_mod","dairy_head","process_keep","culinary_keep"]` (or Enum with those values)
  - `@dataclass PolicyResult`: `atoms: list[str]`, `policy_fired: list[str]`, `derived_from: dict[str, str]` (derived atom lower → parent phrase lower), `verdict_cap: str | None = None`
  - `build_role_index(ingredients: list[dict]) -> dict[str, str]` — maps normalized canonical (+ aliases if present) → role
  - `apply_policies(phrase: str, *, role_index: Mapping[str, str], lookup_flags: Callable[[str], Mapping | None] | None = None) -> PolicyResult`

**Conflict branch order (spec lock — LCT-1):** Inside `apply_policies`, detect plant_mod adjacency **before** committing to dairy_head keep. If a `plant_mod` role token is adjacent to an animalish/`dairy_head` partner, emit plant_mod result and **do not** also apply dairy_head tear/keep for that pair.

**Plant_mod emission (spec C):** `atoms == [phrase, plant_token]` (phrase first); `derived_from[plant_token] == phrase`; no bare dairy/meat atom.

**Dairy_head (no plant_mod):** keep dairy head as sole evaluate atom for the pair (species may attach as structured hint later; 2a minimum: do not emit bare species as a second competing dairy tear — emit the full phrase as the head atom, or the dairy_head token alone if that matches locked tests below). **Locked for 2a tests:** emit the **full phrase** as the single atom when dairy_head fires without plant_mod (`yogurt goat` → `["yogurt goat"]`), with `policy_fired` containing `dairy_head`. (Species-as-flag enrichment can land in the same task if trivial via existing flags; do not invent a second eval atom for goat.)

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/ike2/coverage_os/test_neutralize_plant_dairy.py
from core.knowledge.ike2.coverage_os.neutralize import apply_policies, build_role_index


def _flags_lookup(table):
    def lookup(token: str):
        return table.get(token.lower().strip())
    return lookup


def test_plant_mod_almond_yogurt_both_orders():
    roles = {"almond": "plant_mod", "yogurt": "dairy_head"}
    flags = {
        "yogurt": {"dairy_source": True, "animal_origin": True},
        "almond": {"plant_origin": True, "tree_nut_source": True},
    }
    for phrase in ("almond yogurt", "yogurt almond"):
        r = apply_policies(phrase, role_index=roles, lookup_flags=_flags_lookup(flags))
        assert r.atoms[0] == phrase
        assert "almond" in r.atoms
        assert "yogurt" not in r.atoms  # bare dairy never emitted
        assert r.derived_from["almond"] == phrase
        assert "plant_mod" in r.policy_fired


def test_plant_mod_wins_over_dairy_head_on_plant_yogurt():
    roles = {"plant": "plant_mod", "yogurt": "dairy_head"}
    flags = {"yogurt": {"dairy_source": True, "animal_origin": True}}
    r = apply_policies(
        "plant yogurt", role_index=roles, lookup_flags=_flags_lookup(flags),
    )
    assert "plant_mod" in r.policy_fired
    assert "dairy_head" not in r.policy_fired
    assert "yogurt" not in r.atoms


def test_dairy_head_yogurt_goat_both_orders_no_bare_goat_dairy_tear():
    roles = {"yogurt": "dairy_head"}
    flags = {
        "yogurt": {"dairy_source": True, "animal_origin": True},
        "goat": {"animal_origin": True, "animal_species": "goat"},
    }
    for phrase in ("yogurt goat", "goat yogurt"):
        r = apply_policies(phrase, role_index=roles, lookup_flags=_flags_lookup(flags))
        assert r.atoms == [phrase]
        assert "dairy_head" in r.policy_fired
        assert "goat" not in r.atoms


def test_plant_mod_partner_via_is_animalish_without_dairy_head_role():
    """Partner need not have role=dairy_head — flags via is_animalish suffice."""
    roles = {"coconut": "plant_mod"}  # milk has no role
    flags = {"milk": {"dairy_source": True, "animal_origin": True}}
    r = apply_policies(
        "coconut milk", role_index=roles, lookup_flags=_flags_lookup(flags),
    )
    assert "plant_mod" in r.policy_fired
    assert "milk" not in r.atoms
    assert "coconut" in r.atoms
    assert r.derived_from["coconut"] == "coconut milk"


def test_build_role_index_reads_role_field():
    idx = build_role_index([
        {"canonical_name": "Almond", "role": "plant_mod"},
        {"canonical_name": "yogurt", "role": "dairy_head", "aliases": ["yoghurt"]},
    ])
    assert idx["almond"] == "plant_mod"
    assert idx["yogurt"] == "dairy_head"
    assert idx["yoghurt"] == "dairy_head"
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd backend && python -m pytest tests/ike2/coverage_os/test_neutralize_plant_dairy.py -v
```

Expected: import / not found errors for `neutralize`.

- [ ] **Step 3: Minimal implementation**

Implement `neutralize.py` with:
1. Normalize phrase → tokens.
2. Scan adjacent pairs (i, i+1) both orders conceptually (check both `(tokens[i], tokens[i+1])` roles/flags).
3. **If** any token has `role_index=="plant_mod"` and adjacent partner is `role_index=="dairy_head"` OR `is_animalish(lookup_flags(partner))` → return plant_mod PolicyResult (**return immediately** — this is the conflict win).
4. **Elif** any token has `role_index=="dairy_head"` and len(tokens)>=2 with a partner → return dairy_head full-phrase keep.
5. Else return passthrough `PolicyResult(atoms=[phrase], policy_fired=[], derived_from={})` for now (culinary/process in Task 2).

Default `lookup_flags`: if None, try `truth_anchor.lookup` then `local_ontology.lookup` and read `.flags` (guard ImportError in unit tests by always injecting in tests).

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd backend && python -m pytest tests/ike2/coverage_os/test_neutralize_plant_dairy.py -v
```

- [ ] **Step 5: LCT-1 gate (do not skip)**

Paste the conflict-resolution block from `apply_policies` into the PR/review notes. Confirm plant_mod branch returns before dairy_head. Confirm tests cover both orders + plant yogurt.

- [ ] **Step 6: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/neutralize.py \
  backend/tests/ike2/coverage_os/test_neutralize_plant_dairy.py
git commit -m "feat(coverage-os): neutralize plant_mod/dairy_head apply_policies"
```

---

### Task 2: culinary_keep / process_keep + Tier-1 fallback (+ LCT-2)

**Files:**
- Modify: `backend/core/knowledge/ike2/coverage_os/neutralize.py`
- Test: `backend/tests/ike2/coverage_os/test_neutralize_keep_fallback.py`

**Interfaces:**
- Extends `apply_policies` keep decision. For `process_keep` only: a **function-local** restricted extract list may extract bases (e.g. chicken) — owned by neutralize, not re-exported, **not** used for the no-policy default case.
- **Design lock (passthrough, not tear):** When no culinary/process/plant_mod/dairy_head fires and Tier-1 miss, `apply_policies` returns Task 1 passthrough: `atoms=[phrase]`, `policy_fired=[]`, `derived_from={}`. Do **not** invent a generic keyword-tear list inside `neutralize.py`. Garlic-style extraction is Task 5 / `compound_expansion` via existing `_RESTRICTED_KEYWORDS_*`.
- Produces: commodity_head may call `apply_policies` and inspect `policy_fired` (Task 6).

**Locked order for LCT-2 (literal):**

1. culinary_keep / process_keep (roles) — culinary wins over tearing wine from vinegar
2. plant_mod / dairy_head (Task 1)
3. `truth_anchor.lookup(full_phrase)` keep → fire audit tag `tier1_keep` in `policy_fired`
4. **passthrough** `[phrase]` (not tear)

- [ ] **Step 1: Failing tests**

```python
# backend/tests/ike2/coverage_os/test_neutralize_keep_fallback.py
from unittest.mock import patch
from core.knowledge.ike2.coverage_os.neutralize import apply_policies


def test_culinary_keep_wine_vinegar_no_wine_tear():
    roles = {"vinegar": "culinary_keep"}
    r = apply_policies("wine vinegar", role_index=roles, lookup_flags=lambda t: None)
    assert r.atoms == ["wine vinegar"]
    assert "wine" not in r.atoms
    assert "culinary_keep" in r.policy_fired


def test_process_keep_emits_phrase_and_base():
    roles = {"mechanically": "process_keep", "separated": "process_keep"}
    flags = {"chicken": {"animal_origin": True, "animal_species": "chicken"}}
    r = apply_policies(
        "mechanically separated chicken",
        role_index=roles,
        lookup_flags=lambda t: flags.get(t),
    )
    assert "mechanically separated chicken" in r.atoms
    assert "chicken" in r.atoms
    assert r.derived_from.get("chicken") == "mechanically separated chicken"
    assert "process_keep" in r.policy_fired


def test_tier1_fallback_keep_when_no_role():
    roles = {}
    fake = object()
    with patch(
        "core.knowledge.ike2.coverage_os.neutralize.truth_anchor_lookup",
        return_value=fake,
    ):
        r = apply_policies("fish oil", role_index=roles, lookup_flags=lambda t: None)
    assert r.atoms == ["fish oil"]
    assert "tier1_keep" in r.policy_fired


def test_no_role_no_tier1_passthrough_garlic_pasta():
    """No-policy default is passthrough — NOT keyword tear inside neutralize."""
    roles = {}
    with patch(
        "core.knowledge.ike2.coverage_os.neutralize.truth_anchor_lookup",
        return_value=None,
    ):
        r = apply_policies(
            "garlic pasta",
            role_index=roles,
            lookup_flags=lambda t: None,
        )
    assert r.atoms == ["garlic pasta"]
    assert r.policy_fired == []
    assert r.derived_from == {}
```

For `tier1_keep`: add `"tier1_keep"` to `policy_fired` when Tier-1 fallback fires — audit tag only, not a `PolicyType` / `role` value. Document in module docstring.

- [ ] **Step 2: Run — FAIL**

```bash
cd backend && python -m pytest tests/ike2/coverage_os/test_neutralize_keep_fallback.py -v
```

- [ ] **Step 3: Implement keep branches in order above**

Expose `truth_anchor_lookup = truth_anchor.lookup` as a module-level alias for patching.

- [ ] **Step 4: Run — PASS**

- [ ] **Step 5: LCT-2 gate**

Paste the keep-decision `if/elif` chain. Confirm order matches Global Constraints (culinary/process → plant_mod/dairy_head → Tier-1 → passthrough). Confirm `test_tier1_fallback_keep_when_no_role` proves roles-miss → Tier-1, culinary test proves roles-hit skips Tier-1, and `test_no_role_no_tier1_passthrough_garlic_pasta` proves **no** generic tear list in neutralize.

- [ ] **Step 6: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/neutralize.py \
  backend/tests/ike2/coverage_os/test_neutralize_keep_fallback.py
git commit -m "feat(coverage-os): culinary/process keep and Tier-1 fallback order"
```

---

### Task 3: Writer + ETL + local_ontology `role` plumbing

**Files:**
- Modify: `backend/core/knowledge/ike2/coverage_os/promote_writer.py` — `_apply_ontology_row`, `_retract_ontology_row`
- Modify: `backend/core/knowledge/ike2/etl/adapt.py` — `map_record`
- Modify: `backend/core/knowledge/ike2/stores/local_ontology.py` — `_NON_FLAG_ROW_KEYS`, fact loading
- Test: `backend/tests/ike2/coverage_os/test_promote_writer_role.py`
- Test: `backend/tests/ike2/coverage_os/test_adapt_role_passthrough.py`

**Role-patch rule (exit C for existing heads):**  
Existing ontology rows (yogurt, vinegar, …) are usually **not** `coverage_os_managed`. Full-row overwrite must still refuse. When payload includes `role` and the row exists:

- If `coverage_os_managed`: update `role` (+ flags if provided) as today.
- If **not** managed: **patch only `role`** (leave all other keys untouched). Set `coverage_os_role_managed=True` so demote can clear role. Inverse stores `prior_role` (previous value or `None`).
- New row create: write `role` + flags as today; `coverage_os_managed=True`.

Retract/demote: if `coverage_os_role_managed` and not full managed row → clear `role` / flag and remove `coverage_os_role_managed`; if full managed row → existing delete behavior.

- [ ] **Step 1: Failing tests**

```python
# backend/tests/ike2/coverage_os/test_promote_writer_role.py
import json
from pathlib import Path
from core.knowledge.ike2.coverage_os.promote_writer import apply_promotion, retract_promotion


def test_role_patch_on_existing_non_managed_row(tmp_path):
    ont = tmp_path / "ontology.json"
    ont.write_text(json.dumps({
        "ingredients": [{
            "canonical_name": "yogurt",
            "animal_origin": True,
            "dairy_source": True,
            "plant_origin": False,
        }]
    }))
    aliases = tmp_path / "variant_aliases.json"
    aliases.write_text(json.dumps({"aliases": {}}))
    entry = {
        "payload": {
            "write_kind": "ontology_row",
            "canonical_name": "yogurt",
            "role": "dairy_head",
            "flags": {},
            "inverse": {
                "write_kind": "ontology_row",
                "canonical_name": "yogurt",
                "prior_role": None,
                "role_patch_only": True,
            },
        }
    }
    apply_promotion(entry, ontology_path=ont, aliases_path=aliases)
    row = json.loads(ont.read_text())["ingredients"][0]
    assert row["role"] == "dairy_head"
    assert row["dairy_source"] is True  # untouched
    assert row.get("coverage_os_role_managed") is True
    assert row.get("coverage_os_managed") is not True

    retract_promotion(entry, ontology_path=ont, aliases_path=aliases)
    row2 = json.loads(ont.read_text())["ingredients"][0]
    assert "role" not in row2 or row2.get("role") in (None, "")
```

```python
# backend/tests/ike2/coverage_os/test_adapt_role_passthrough.py
from core.knowledge.ike2.etl.adapt import map_record


def test_map_record_preserves_role():
    raw = {
        "canonical_name": "vinegar",
        "role": "culinary_keep",
        "plant_origin": True,
    }
    mapped = map_record(raw, canonical_source="test", default_state="LOCKED")
    assert mapped.get("role") == "culinary_keep"
```

Also assert `role` ∉ flags dict when local_ontology loads (add test if fact API exposes `.role` or role_index builder reads raw JSON).

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement writer patch + `map_record` copy `role` + `_NON_FLAG_ROW_KEYS += ("role", "coverage_os_role_managed", "coverage_os_managed", ...)` as needed so `role` is not stuffed into `TruthAnchorFact.flags`

Check current `_NON_FLAG_ROW_KEYS` and extend minimally: at least `"role"`, `"coverage_os_role_managed"`, `"coverage_os_managed"`, `"id"`, `"aliases"`, … — only add keys this task introduces if missing; do not drive-by fix unrelated keys unless tests require.

- [ ] **Step 4: Run — PASS**

- [ ] **Step 5: Commit**

```bash
git add backend/core/knowledge/ike2/coverage_os/promote_writer.py \
  backend/core/knowledge/ike2/etl/adapt.py \
  backend/core/knowledge/ike2/stores/local_ontology.py \
  backend/tests/ike2/coverage_os/test_promote_writer_role.py \
  backend/tests/ike2/coverage_os/test_adapt_role_passthrough.py
git commit -m "feat(coverage-os): promote and load ontology role field"
```

---

### Task 4: Role-only gate + seed promotions

**Files:**
- Test: `backend/tests/ike2/coverage_os/test_hybrid_gate_role_only.py`
- Create: `backend/scripts/seed_neutralize_roles.py` (or `backend/tests/ike2/coverage_os/seed_roles_fixture.py` used by integration) — seeds via `commit_promotion` with human reviewer fields after `decide_promote` returns `human_approval`
- Modify: none of hybrid_gate.py unless a bug is found (spec: **no new auto branch**)

- [ ] **Step 1: Gate test (documents existing fall-through)**

```python
# backend/tests/ike2/coverage_os/test_hybrid_gate_role_only.py
from core.knowledge.ike2.coverage_os.hybrid_gate import decide_promote
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key


def test_role_only_payload_is_human_fail_closed(tmp_path):
    led = PromoteLedger(tmp_path / "l.jsonl")
    d = decide_promote(
        candidate_key=candidate_key("almond", "almond"),
        candidate_name="almond",
        flags={},  # role-only: no plant_origin — cannot satisfy auto_promote predicate
        ledger=led,
        ontology={"ingredients": []},
    )
    # GateDecision.action Literal (Phase 1): auto_promote | human_approval | rejected
    assert d.action == "human_approval"
    assert d.rule_id == "human_fail_closed"
```

- [ ] **Step 2: Run — PASS (no gate code change expected)**

If empty `flags={}` somehow takes another path, adjust flags to still lack `plant_origin` truthy (e.g. `{"plant_origin": False}`) so auto_promote cannot fire — do **not** add a role auto-promote branch.

- [ ] **Step 3: Seed script**

Script reads a closed list of `(canonical_name, role)` covering today’s Sets membership needed for exit goldens (`_PLANT_MODIFIERS`, dairy heads used in goldens, `_KEEP_WHOLE_SUFFIXES` → culinary_keep, `_KEEP_AND_EXTRACT_WORDS` → process_keep). For each:

1. `decide_promote(...)` with flags from existing ontology row if any
2. Assert human for role-only / animalish
3. `commit_promotion(..., auto=False, reviewer_id="phase2a-seed", approval_rationale="phase2a role seed", ...)` with role-patch payload

Run against a **temp** ontology in tests; for real data, operator runs script with explicit paths (document in script docstring). Do not force-commit production ontology in CI without review.

- [ ] **Step 4: Integration test seed → `build_role_index` → `apply_policies` sees role**

```python
def test_seeded_role_visible_to_apply_policies(tmp_path):
    # promote almond role=plant_mod via writer on temp ontology
    # build_role_index(load json)
    # apply_policies("almond yogurt", ...) fires plant_mod
    ...
```

- [ ] **Step 5: Commit**

```bash
git add backend/tests/ike2/coverage_os/test_hybrid_gate_role_only.py \
  backend/scripts/seed_neutralize_roles.py \
  backend/tests/ike2/coverage_os/test_phase2a_role_seed.py
git commit -m "feat(coverage-os): role-only human gate proof and role seed path"
```

---

### Task 5: Wire `compound_expansion` (migration-safe)

**Files:**
- Modify: `backend/core/compound_expansion.py`
- Modify callers if return arity changes: `backend/core/parsing/chat_ingredients.py`, `backend/core/parsing/label_decomposer.py`, tests
- Test: `backend/tests/test_compound_expansion_neutralize_wire.py`

**Return type lock:**

```python
def expand_compounds(
    ingredients: List[str],
) -> Tuple[List[str], Dict[str, str], Dict[str, str]]:
    """Returns (expanded, display_map, derived_from_map)."""
```

Update all callers (today: 2-tuple unpack in `chat_ingredients.py:77` and `label_decomposer.py`). `derived_from_map` merges per-phrase `PolicyResult.derived_from`.

**Layering lock (passthrough vs keyword extract):**

| Layer | Owns |
|-------|------|
| `apply_policies` | Typed neutralize only; no-policy → `[phrase]` |
| `compound_expansion` | `"with"` split; when policies **fire**, trust `PolicyResult.atoms`; when **passthrough**, run existing `find_sub_ingredients` / `_RESTRICTED_KEYWORDS_*` (already audited; **not** a new neutralize list) |

Do **not** delete `_RESTRICTED_KEYWORDS_SINGLE` / `_RESTRICTED_KEYWORDS_BIGRAM` in 2a.

**Migration substeps (do not collapse):**

- [ ] **Step 5a:** Call `apply_policies` **alongside** existing plant/keep Sets; assert parity for seeded phrases. Keep Sets.

- [ ] **Step 5b:** Failing parity/golden tests for plant yogurt / almond yogurt emission C using engine path.

- [ ] **Step 5c:** Once Task 4 seeds exist / monkeypatched role_index, prefer `apply_policies` for neutralize; on passthrough, still call `find_sub_ingredients`.

```python
def test_expand_compounds_passthrough_still_extracts_garlic():
    """Keyword tear lives in expansion, not neutralize — garlic pasta stays covered."""
    expanded, _dmap, _derived = expand_compounds(["garlic pasta"])
    assert "garlic" in expanded
```

- [ ] **Step 5d:** Delete `_PLANT_MODIFIERS`, `_KEEP_WHOLE_SUFFIXES`, `_KEEP_AND_EXTRACT_WORDS` and dead keep helpers only. Grep — must be zero for those three. `_RESTRICTED_KEYWORDS_*` must **remain**.

```bash
rg "_PLANT_MODIFIERS|_KEEP_WHOLE_SUFFIXES|_KEEP_AND_EXTRACT_WORDS" backend/
# expected: no matches
rg "_RESTRICTED_KEYWORDS_" backend/core/compound_expansion.py
# expected: still present
```

- [ ] **Step 5e:** Commit after 5d

```bash
git commit -m "feat: compound_expansion thin-wraps neutralize.apply_policies"
```

**Skeleton for wired expand (after 5c):**

```python
from core.knowledge.ike2.coverage_os.neutralize import apply_policies, build_role_index

def _role_index():
    # load ontology ingredients once (cache); tests may monkeypatch
    ...

def expand_compounds(ingredients):
    expanded, display_map, derived_from_map = [], {}, {}
    for ing in ingredients:
        # preserve existing "with" split first
        ...
        result = apply_policies(ing, role_index=_role_index())
        if result.policy_fired:
            atoms = result.atoms
        else:
            # passthrough: existing keyword extract (not a neutralize invent)
            subs = find_sub_ingredients(ing)
            atoms = subs if subs else [ing]
        for atom in atoms:
            expanded.append(atom)
            display_map[atom.lower()] = ing
        for child, parent in result.derived_from.items():
            derived_from_map[child.lower()] = parent.lower()
    return expanded, display_map, derived_from_map
```

---

### Task 6: `commodity_head` shared culinary keep

**Files:**
- Modify: `backend/core/knowledge/ike2/commodity_head.py`
- Test: `backend/tests/ike2/test_commodity_head_culinary_keep.py`

- [ ] **Step 1:** Failing test: `facet_reduction_candidates("wine vinegar")` must not strip to `wine` when `vinegar` has `culinary_keep` in role_index (inject/patch role_index).

- [ ] **Step 2:** Replace uses of `_FORBIDDEN_STRIP` for keep decisions with a helper that asks neutralize (e.g. if `apply_policies(name).policy_fired` contains `culinary_keep` / `process_keep` / `tier1_keep`, do not strip). Do not leave a second divergent culinary frozenset for vinegar/lecithin/sauce once roles cover them. Residual strip entries that are **not** culinary_keep (butter, oil, …) may remain until a later phase — document in code comment as Phase 2a residual if still needed for head geometry.

- [ ] **Step 3:** PASS + commit

```bash
git commit -m "feat(ike2): commodity_head defers culinary keep to neutralize"
```

---

### Task 7: `derived_from` → audit composer (+ LCT-3)

**Files:**
- Modify: `backend/core/parsing/chat_ingredients.py` — add `derived_from_map: dict[str, str] = field(default_factory=dict)` to `PreparedChatIngredients`; unpack 3-tuple from `expand_compounds`
- Modify: `backend/app.py` (~L613 `compound_map = prepared.compound_map`; ~L712 audit call) — also take `prepared.derived_from_map` and pass `derived_from=...`
- Modify: `backend/core/response_composer.py` — add kw-only optional `derived_from: Optional[Dict[str, str]] = None` to existing signature
- Test: `backend/tests/test_audit_derived_from_fold.py`

**Verified signature to extend (do not invent a parallel API):**

```python
def build_ingredient_audit_payload(
    verdict: ComplianceVerdict,
    profile: Any,
    ingredients: List[str],
    display_names: Optional[Dict[str, str]] = None,
    explanation_text: str = "",
    explanation_source: str = "template",
    derived_from: Optional[Dict[str, str]] = None,  # ADD
) -> Dict[str, Any]:
```

**Verified groups shape:** `groups` entries are `{"status": "avoid"|"depends"|"safe", "items": [{"name": ..., ...}, ...]}`.

**Card merge rule (spec):**

- Evaluate atoms independently (compliance unchanged aside from receiving all atoms).
- When building avoid/depends/safe **cards**, if atom `A` has `derived_from[A] == P`, do not create a top-level card for `A`; merge `A`’s restriction hits into the card for parent `P` (display name = user phrase via `display_names` / `compound_map`).
- Paste `almond yogurt, sugar` → **two** top-level cards.

- [ ] **Step 1: Failing test**

```python
from core.response_composer import build_ingredient_audit_payload


def test_almond_yogurt_single_avoid_card_when_almond_triggers():
    # Build a minimal ComplianceVerdict where both "almond yogurt" and "almond"
    # appear in triggered_ingredients with tree-nut restriction on almond.
    # (Fill verdict fields to match ComplianceVerdict used elsewhere in composer tests.)
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=profile,
        ingredients=["almond yogurt", "almond", "sugar"],
        display_names={
            "almond yogurt": "almond yogurt",
            "almond": "almond yogurt",
            "sugar": "sugar",
        },
        derived_from={"almond": "almond yogurt"},
    )
    avoid_names = [
        i["name"]
        for g in payload["groups"]
        if g["status"] == "avoid"
        for i in g["items"]
    ]
    assert sum(1 for n in avoid_names if "almond" in n.lower()) == 1
    all_names = [i["name"] for g in payload["groups"] for i in g["items"]]
    assert any("sugar" in n.lower() for n in all_names)
```

- [ ] **Step 2: Implement merge in composer**

- [ ] **Step 3: PASS**

- [ ] **Step 4: LCT-3 gate**

Trace and paste:
1. `expand_compounds` fills `derived_from_map`
2. `prepare_chat_ingredients` copies onto `PreparedChatIngredients.derived_from_map`
3. `app.py` passes `derived_from=prepared.derived_from_map` into `build_ingredient_audit_payload`
4. Composer skips top-level row for keys present as derived children

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: fold derived_from atoms into parent audit cards"
```

---

### Task 8: Exit criteria C — goldens, matrix smoke, round-trip

**Files:**
- Test: `backend/tests/ike2/coverage_os/test_phase2a_exit.py`
- Extend: `backend/tests/test_compound_umbrella_regressions.py` / new `backend/tests/ike2/test_phase2a_compound_goldens.py`
- Run: `backend/scripts/run_profile_matrix.py` on a small compound-tear corpus fixture

- [ ] **Step 1: Golden bugs**

```python
@pytest.mark.parametrize("phrase,forbidden", [
    ("plant yogurt", ["yogurt"]),  # bare dairy not alone without phrase — adjust to emission C
    ("yogurt plant", ["yogurt"]),
    ("almond yogurt", ["yogurt"]),
    ("wine vinegar", ["wine"]),
    ("soy lecithin", ["soy"]),
])
def test_phase2a_compound_goldens(phrase, forbidden):
    expanded, dmap, derived = expand_compounds([phrase])
    for bad in forbidden:
        # bare dairy/wine/soy must not appear without parent keep — culinary keeps whole only
        if phrase.endswith(("vinegar", "lecithin")):
            assert expanded == [phrase]
        else:
            assert bad not in expanded or phrase in expanded
```

Tighten assertions to match emission C exactly (phrase present; bare dairy absent; plant present with derived_from).

- [ ] **Step 2: Writer/ledger round-trip** (promote → apply_policies → demote → behavior restored) in `test_phase2a_exit.py`

- [ ] **Step 3: Matrix smoke**

Add fixture paste list of ~10–20 compounds; run matrix helper; assert no new Safe on culinary vinegar/lecithin/sauce cells vs baseline snapshot file `backend/tests/ike2/coverage_os/fixtures/phase2a_matrix_baseline.json` (create baseline on first green run; commit it).

- [ ] **Step 4: Full coverage_os + compound regression suite**

```bash
cd backend && python -m pytest tests/ike2/coverage_os/ tests/test_compound_umbrella_regressions.py tests/test_audit_derived_from_fold.py -v
```

- [ ] **Step 5: Commit**

```bash
git commit -m "test(coverage-os): Phase 2a exit criteria goldens and matrix smoke"
```

- [ ] **Step 6: Exit checklist (all must be true)**

- [ ] No `_PLANT_MODIFIERS` / `_KEEP_WHOLE_*` / `_KEEP_AND_EXTRACT_*` in `compound_expansion.py`
- [ ] `_RESTRICTED_KEYWORDS_*` still present (no-policy keyword extract layer)
- [ ] LCT-1, LCT-2, LCT-3 signed off with pasted code
- [ ] Role-only → `human_approval` + `human_fail_closed` test green
- [ ] Role round-trip via writer green
- [ ] Goldens + matrix smoke green
- [ ] No induction / 2b code in `coverage_os/`
- [ ] `apply_policies` no-policy path is passthrough only (no generic tear list in neutralize)

---

## Spec coverage self-review

| Spec requirement | Task |
|------------------|------|
| `apply_policies` single API | 1–2 |
| plant_mod emission C + both orders | 1 |
| plant_mod wins conflict | 1 + LCT-1 |
| Partner via `is_animalish` | 1 |
| dairy_head both orders | 1 |
| culinary/process keep | 2 |
| Tier-1 fallback order | 2 + LCT-2 |
| `derived_from` only + display_map | 5, 7 |
| Audit one card / fold derived | 7 + LCT-3 |
| `role` on ontology + ETL | 3 |
| Role-only human_fail_closed | 4 |
| Seed via ledger/writer | 4, 8 |
| Migration: Sets until seeds+goldens | 5a–5d |
| commodity_head shared keep | 6 |
| Exit C goldens + matrix + round-trip | 8 |
| No-policy keyword extract stays in expansion | 5 (layering lock) |
| Passthrough default in neutralize | 1, 2 |
| `human_approval` (not `"human"`) | 4 |
| Path-sanity verified signatures | Global Constraints |
