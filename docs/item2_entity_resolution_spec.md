# IngreSure — Build Specification: Item 2
## Entity identity & resolution for IKE-2

**Status:** **Core complete (Prompts 1–7).** Prompt 8 (Yam-class disambiguation ops doc) remains optional P2.  
**Companion files:** `docs/item1_item2_gap_report.md` · `docs/system_state_audit.md` §2–4 · `docs/superpowers/specs/2026-06-16-ike2-design.md` §§5–6 · Item 16 fungal/tempeh stage-log lessons · tracker rows 2 / 2.1

---

## 0. How to use this document

Item 2 is **not** “build a resolver from scratch.” Hot-path resolution (truth anchor → local ontology → DB alias + disambiguation → variant/facet synonymy → fail-closed unknown) already ships. This spec closes **identity** gaps: IKE-2-native merges, unknown-queue writes, and — critically — Item **2.1** compound decomposition that propagates **process-derived** flags (`fungal`, `fermented`), not just compositional members.

The tempeh / Jain false-SAFE class from Item 16’s primary soak is binding precedent: expanding a fermented fungal food into `soybean` + `water` stripped identity and produced SAFE under Jain. Fixes that only patch one string are insufficient; 2.1 must encode the class rule.

Keep this at `docs/item2_entity_resolution_spec.md`.

---

## 1. Current state (confirmed — act on this)

### 1.1 Schema (real tables — use these names)

| Table | Role |
|-------|------|
| `ike2_ingredient_groups` | Canonical identity + compliance flags + `knowledge_state` |
| `ike2_ingredients` | Named forms per group |
| `ike2_aliases` | Raw/normalized string → ingredient |
| `ike2_alias_disambiguation` | Region-scoped winners for known conflicts |
| `ike2_restriction_rules` | Deterministic diet/allergen rules (consumed by compliance, not resolver) |
| `ike2_unknown_queue` | Discovery queue (schema present) |
| `ike2_group_merges` | Merge audit + `rollback_snapshot` (schema present) |
| Enum `ike2_knowledge_state` | `UNCLASSIFIED \| DISCOVERED \| AUTO_CLASSIFIED \| VERIFIED \| LOCKED \| DEPRECATED` + CHECKs |

View: `ike2_v_alias_resolution` (alias → active ingredient → non-DEPRECATED group).

### 1.2 What already works

- **Resolver** (`backend/core/knowledge/ike2/resolver.py`): cache seed → L1 `truth_anchor` → L2 `local_ontology` → L3 `db.resolve_alias` / `db.disambiguate` → on miss, synonymy ladder via `variant_aliases.lookup_variant_alias` + `commodity_head` facet/head candidates → L5 uncertain (`status="uncertain"`, never SAFE).
- **Ambiguity policy:** >1 distinct ingredient for an alias with no disambiguation winner → uncertain (never silent auto-pick).
- **Input decomposition:** `ike2/input_layer.py` → `parsing/label_decomposer.decompose_label` → `compound_expansion.expand_compounds` + Coverage OS neutralize (`plant_mod` / `dairy_head` / `process_keep` / `culinary_keep`).
- **Identity flag derivation:** `flag_derive.derive_identity_flags` ORs fungal from yeast / mushroom / tempeh / mycoprotein / koji tokens (post–Item 16 class fix).
- **Tempeh class fix (shipped):** truth-anchor `tempeh` with `soy_source` + `fungal`; stopped recipe expansion that replaced tempeh with soybean+water; ontology aliases for yeast variants.
- **Variant / commodity synonymy:** curated JSON + allowlisted facet strip — no runtime fuzzy / LLM.

### 1.3 What does **not** exist yet

- **No writer** to `ike2_group_merges` — table is empty infrastructure.
- **No IKE-2 merge tooling** — `core/knowledge/merge.merge_groups` targets **legacy** `ingredients` / `ingredient_groups` / `ingredient_aliases`, not `ike2_*`.
- **No compound→member decomposition service** that creates/links member groups while OR-propagating process flags from the parent (Item **2.1**). Neutralize/`expand_compounds` extract compositional keywords; they do not systematically attach parent `fungal`/`fermented` onto children.
- Resolver L5 returns fail-closed uncertain with layer/source tags only — **does not write** `ike2_unknown_queue` (Option B; Item **18** owns the write). Enrichment still uses legacy `unknown_ingredients`.
- Design-doc L4 “regional translate” / L5 “APIs on hot path” are **not** the shipped model — regional remap lives in `normalize_ingredient_key`; APIs are offline/enrichment only. Do not “restore” hot-path APIs under Item 2.

---

## 2. Purpose of this component

Ensure every raw ingredient atom resolves to a **stable, auditable identity** (or fail-closed uncertainty), and that **compound foods cannot lose process identity** when decomposed into members — so compliance flags like Jain `fungal` and alcohol `fermentation_trace` remain correct.

---

## 3. Scope

### In scope

- Document the shipped resolver contract (tiers, fail-closed rules) as the baseline — change only where gaps below require it.
- Item **2.1**: process-aware compound decomposition (composition **and** process-flag propagation).
- IKE-2 group merge CLI/API that writes `ike2_*` + `ike2_group_merges.rollback_snapshot`.
- Optional: resolver L5 enqueue into `ike2_unknown_queue` (or hard deferral note to Item 18 with a single tracked decision).
- Goldens / regression tests for tempeh, yeast, yeast extract, koji, miso-class fermentation, and “compound expands but fungal retained” cases.
- Seed / ops guidance for `ike2_alias_disambiguation` (data, not new algorithm).

### Explicitly out of scope

- Bulk SourceAdapter / produce / animal ingest (Item 1 / 17).
- Restriction rule completeness / Jain sub-variants beyond identity flags (Item 3 / 3.1) — except Item 2 must not strip flags those rules need.
- Coverage OS promote daemon / induction (Item 4) — reuse neutralize; do not rebuild.
- Hot-path LLM or edit-distance fuzzy match.
- Deleting legacy `merge.py` before IKE-2 merge exists and is verified (strangler: add IKE-2 path first).
- Changing verdict vocabulary or compliance aggregation (owned elsewhere).

---

## 4. Target design

### 4.1 Resolver contract (baseline — preserve)

Per normalized atom after input_layer decomposition:

1. Cache lookup  
2. L1 Truth Anchor (wins)  
3. L2 Local ontology file  
4. L3 DB alias via `ike2_v_alias_resolution` + `ike2_alias_disambiguation`  
5. Synonymy ladder: variant aliases → allowlisted facet/head candidates → re-enter tiers  
6. Else uncertain — never SAFE  

Malicious / incomplete DB rows (`canonical_name` missing or required origin fields absent) → uncertain.

### 4.2 Item 2.1 — Compound decomposition with process flag propagation

**Problem class:** A compound term may be expanded into compositional members (e.g. soy product → soybean). If the parent carries **process** identity (`fungal`, `fermented`, alcohol role), members that lack those flags produce false-SAFE under diets that key off process, not composition.

**Rules:**

1. **Prefer keep-whole** for known process foods when expansion would drop process identity (tempeh precedent). Document the keep-whole registry (truth-anchor / role / neutralize `process_keep` / explicit denylist of recipe expansions).
2. When expansion **does** emit members, compute:

   ```text
   member_flags = member_flags OR parent_process_flags
   parent_process_flags ⊆ { fungal, fermented, … agreed set }
   ```

   Propagation is **OR-only** (never clear a member’s existing positive flag). It does **not** invent animal/allergen composition the parent did not imply — process set is explicit and small.
3. If members are persisted as separate groups (offline ops), write an auditable link: either decomposition metadata on the parent group **or** a dedicated structure — **do not** overload `ike2_group_merges` (that table is merge-from→into with rollback). Prefer a new optional column/JSONB on groups **or** a small `ike2_group_members` table only if Prompt 1 shows merges cannot represent the relationship without confusion.
4. Label path (`decompose_label` / `expand_compounds`) and any future offline compound splitter must share the same propagation helper so bridge and IKE-2 cannot drift.
5. Umbrella compounds (`spices`, `natural flavors`) remain `verdict_cap=WARN` / never firm-SAFE — decomposition must not make them SAFE by expanding to empty/unknown children.

**Acceptance examples (non-exhaustive):**

| Input | Must not happen | Expected |
|-------|-----------------|----------|
| `tempeh` | Expand to soybean+water only; Jain SAFE | Resolves with `fungal=True` → Jain NOT_SAFE / Avoid |
| `yeast` / `yeast extract` | Empty flags | `fungal=True` |
| Compound that legitimately expands | Children lose parent `fermented`/`fungal` | Children OR-inherit process flags **or** parent kept whole |

### 4.3 IKE-2 merges

- New module (e.g. `ike2/etl/merge_groups.py` or `ike2/identity/merge.py`) operating on `ike2_ingredient_groups` / `ike2_ingredients` / `ike2_aliases`.
- On success: insert `ike2_group_merges(from_group_id, into_group_id, rollback_snapshot)`.
- Snapshot must be sufficient to undo alias reassignment + superseded pointers.
- Most-restrictive flag merge on keeper (same spirit as `reconcile.py`).
- Legacy `merge.py` left in place until a later cleanup item; do not silently dual-write.

### 4.4 Unknown queue

**Decision (2026-09-17): Option B — explicit deferral to Item 18.**

- Do **not** add L5 writes to `ike2_unknown_queue` under Item 2.
- Fix resolver/docs comments that claim “enqueue” so they do not lie.
- Item **18** (with Celery Beat Item **23**) owns the real write path + worker cutover to `ike2_unknown_queue` in one place.

Do not enqueue E-numbers to APIs; do not resolve via LLM on the hot path.

---

## 5. Safety invariants (non-negotiable)

1. Ambiguous alias without region/disambiguation winner → uncertain — never silent pick.  
2. Unknown / malformed / untrusted resolution → never SAFE.  
3. Process identity (`fungal`, `fermented`) must survive compound expansion or the compound must stay whole.  
4. Merges never drop a positive safety flag on the keeper (most-restrictive OR).  
5. No hot-path fuzzy match or LLM.  
6. `ike2_group_merges` rows are append-only audit; rollback uses snapshot, not silent DELETE of history.

---

## 6. Sub-items

| ID | Title | Deliverable |
|----|-------|-------------|
| **2** | Identity ops baseline | IKE-2 merge + (queue write or explicit deferral); docs match shipped resolver |
| **2.1** | Process-aware compound decomposition | Shared propagation helper + keep-whole registry + goldens (tempeh/yeast/koji class) |

---

## 7. Numbered build prompts for Cursor

**Prompt 1** — Investigate and report (no behavior change): (a) confirm resolver L5 does not write `ike2_unknown_queue`; (b) confirm nothing INSERTs into `ike2_group_merges`; (c) trace `tempeh` through `expand_compounds` / neutralize / truth_anchor / `flag_derive` and document why Jain is safe today; (d) list every call site of `expand_compounds` / `decompose_label`. Record findings in this file before Prompt 2. **Queue fork already decided: Option B** (defer to Item 18).

**Prompt 2** — Extract a pure helper `propagate_process_flags(parent_flags: dict, member_flags: dict) -> dict` (OR-only on the agreed process flag set). Unit tests: fungal parent + plain soy member → member fungal; fermented parent preserved; never clears member positives; does not copy `dairy_source` unless included in the agreed set (default: **exclude** compositional allergens from process set).

**Prompt 3** — Item **2.1** wire-up: integrate the helper into `expand_compounds` / neutralize passthrough paths (and any keep-whole short-circuit). Add regression tests: `tempeh` does not expand to identity-less soybean; if a test compound is configured to expand, children carry parent process flags. Re-run `must_never_be_safe` fungal/tempeh/yeast cases.

**Prompt 4** — Keep-whole / anti-recipe registry: centralize foods that must not recipe-expand (tempeh and documented peers). Prefer data/role-driven config over scattered string compares. Test that adding a keep-whole entry prevents destructive expansion.

**Prompt 5** — Implement IKE-2 `merge_groups` writing `ike2_*` + `ike2_group_merges.rollback_snapshot`. Dry-run flag required. Tests with fake/supabase mock: aliases retargeted, mergee superseded, flags OR-merged, snapshot round-trip documented.

**Prompt 6** — Option B: patch resolver/docs comments that claim L5 “enqueue”; stage-log Item 18 dependency. No half-enqueue, no `ike2_unknown_queue` write from Item 2.

**Prompt 7** — Goldens / soak extras: extend deliberate corpus or ike2 golden fixtures for koji/miso/tamari/natto/yeast/tempeh under Jain — assert never SAFE; fail-closed UNCERTAIN acceptable where unresolved. Do not weaken comparator to hide NOT_SAFE→SAFE.

**Prompt 8** — (P2) Operator doc: how to seed `ike2_alias_disambiguation` for Yam-class regional conflicts; no code change required unless seeds are missing for a failing golden.

---

## 8. Keeping this file in sync

Update the stage log when Prompts 1–7 land. Tracker Items 2 / 2.1 Notes should point here.

### Stage log

| When | Stage | Notes |
|------|-------|-------|
| 2026-09-17 | **draft** | Spec reconstructed from audit + IKE-2 design §§5–6 + Item 16 fungal/tempeh lesson. Tempeh class fix already in code; general 2.1 propagation + IKE-2 merges still open. |
| 2026-09-17 | **decision** | L5 unknown-queue write = **Option B** (defer to Item 18; fix lying comments). Process-flag set for 2.1 remains `{fungal, fermented}` unless a later decision expands it. |
| 2026-09-18 | **Prompt 1 done** | Findings below. Option B confirmed by code. **Correction:** multi-token `soy tempeh` / `soy miso` / `wheat koji` / `soy natto` → false Jain SAFE via keyword-only passthrough (parse-layer). Ready for Prompt 2 helper, but Prompt 3/4 must keep parent atoms — helper alone insufficient. |
| 2026-09-21 | **Prompt 2 done** | `process_flags.propagate_process_flags` — OR-only on `{fungal, fermented}`; does not copy compositional allergens. Unit tests in `test_process_flags.py`. Wire-up = Prompt 3. |
| 2026-09-21 | **Prompt 3 done** | `expand_compounds` retains process-identity atoms (tempeh/miso/koji/natto/…) dropped by keyword extract; `member_flags_with_parent_process` OR-wires `{fungal, fermented}` from parent. Regression: `soy tempeh` keeps tempeh + Jain not SAFE; garlic-pasta Phase 2a baseline unchanged. |
| 2026-09-21 | **Prompt 4 done** | `data/ike2_keep_whole.json` + `keep_whole.is_keep_whole` — anti-recipe denylist. `flatten_ingredients` keeps whole over `PROCESSED_FOOD_TO_BASE`; `expand_compounds` process-identity tokens load from same registry. Test: add entry → blocks destructive expansion. |
| 2026-09-22 | **Prompt 5 done** | `ike2/merge_groups.py` — dry-run default; apply ORs bool flags, retargets colliding aliases, moves unique ingredients, supersedes mergee, inserts `ike2_group_merges.rollback_snapshot`. Fake-store tests; legacy `merge.py` untouched. |
| 2026-09-22 | **Prompt 6 done** | Option B executed: resolver module + L5 comments no longer claim “enqueue”; document Item **18** (+ Beat **23**) as sole owner of `ike2_unknown_queue` writes. No half-enqueue. Tests: L5 miss stays uncertain with zero queue inserts. |
| 2026-09-22 | **Prompt 7 done** | Jain fermentation goldens: `must_never_be_safe.jsonl` + `test_fermentation_jain_goldens.py` cover koji/miso/tamari/natto/yeast/tempeh and compound forms. Never firm SAFE; UNCERTAIN/WARN OK for unresolved/fermented-only. Tempeh/yeast stay firm NOT_SAFE. Firm Avoid for miso-class remains Item 3.1 P2 backlog. |
| 2026-09-22 | **core complete** | Prompts 1–7 close Item 2 / 2.1 P0/P1. **Prompt 8 deferred** (optional P2 ops doc). |

### Prompt 1 findings (2026-09-18)

#### (a) Resolver L5 ↔ `ike2_unknown_queue`

**Does not write.** Miss path returns `_uncertain("L5_unknown_queue", "unknown_queue")` only — layer/source tags for offline prioritization; no DB insert (`resolver.py`). **Prompt 6 (2026-09-22):** comments/docs corrected; Item **18** (+ Beat **23**) owns real `ike2_unknown_queue` write + worker cutover. Enrichment still targets legacy `unknown_ingredients` until then.

#### (b) `ike2_group_merges` writers

**No Python INSERTs.** Table exists in `20260616000000_ike2_schema.sql` only. `core/knowledge/merge.merge_groups` targets **legacy** `ingredient_groups` / aliases — not `ike2_*`.

#### (c) Tempeh → Jain never-SAFE (why today — and where it still leaks)

**Bare `tempeh` is protected** (verified end-to-end → Jain **NOT_SAFE**):

| Step | Behavior |
|------|----------|
| `expand_compounds(["tempeh"])` | Single-token path → **passthrough** `['tempeh']` (no recipe expand). |
| `PROCESSED_FOOD_TO_BASE` | Tempeh **intentionally absent** (comment: Rhizopus identity); `tofu` *is* expanded to soybean+water. |
| Neutralize | Not reached for single-token tempeh. |
| `truth_anchor` | `tempeh` → `soy_source=True`, `fungal=True`, `LOCKED`. |
| `flag_derive` / seam | Name token `tempeh` → `fungal=True` (belt-and-braces). |
| Compliance | Jain `fungal` FAIL → **NOT_SAFE**. |

**Live gap (parse layer, not hypothetical):** multi-token phrases that contain a restricted keyword *and* a fungal food collapse to the keyword only — parent token discarded before resolve:

| Input | Atoms produced | Jain verdict |
|-------|----------------|--------------|
| `tempeh` | `['tempeh']` | FAIL |
| `soy tempeh` / `organic soy tempeh` | `['soy']` | **SAFE** (false) |
| `soy miso` / `barley miso` | `['soy']` / `['barley']` | **SAFE** (false) |
| `soy natto` | `['soy']` | **SAFE** (false) |
| `wheat koji` | `['wheat']` | **SAFE** (false) |

Cause: `expand_compounds` passthrough (`find_sub_ingredients`) emits only `_RESTRICTED_KEYWORDS_SINGLE` hits; `tempeh`/`miso`/`koji`/`natto` are not in that set, so they are dropped. **Prompt 2’s `propagate_process_flags` alone cannot fix this** — there is no surviving parent to OR from. Prompt 3/4 must keep the parent atom (or consult it) in that branch; keep-whole registry is not enough for prefixed forms.

#### (d) Call sites

**`expand_compounds`**

| Location | Role |
|----------|------|
| `core/parsing/label_decomposer.py` | Nested compound names inside labels |
| `core/parsing/chat_ingredients.py` | Simple-list path |
| `core/compound_expansion.py` | Definition |
| Tests: `test_compound_expansion_neutralize_wire`, `test_phase2a_*`, `test_compound_umbrella_regressions`, coverage_os matrix/exit | |

**`decompose_label`**

| Location | Role |
|----------|------|
| `core/knowledge/ike2/input_layer.py` | IKE-2 chat/evaluate atomization |
| `core/parsing/chat_ingredients.py` | Label-shaped pastes |
| `core/parsing/label_decomposer.py` | Definition |
| Tests: label corpus/OCR/parser/stress, diet matrix, fixtures | |

#### Option B

Confirmed: **no** Item 2 write to `ike2_unknown_queue`; defer to Item 18 (+ Beat 23). Prompt 6 = comment/doc honesty only.

---

## 9. Success criteria

- [ ] Documented resolver behavior matches code (no phantom hot-path API tier).  
- [ ] Process-flag propagation helper exists, tested, and wired into compound expansion.  
- [ ] Tempeh / yeast / yeast-extract / documented fermentation-class goldens never SAFE under Jain.  
- [ ] IKE-2 merge writes `ike2_group_merges` with rollback snapshots.  
- [ ] L5 explicitly deferred to Item 18 with comments fixed (Option B — no Item 2 write path).  
- [ ] Legacy merge module unchanged until a later cleanup item.  
