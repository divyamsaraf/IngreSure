# Item 11 — `asserted_flags` design

**Status:** implemented (dataclass, serializers, reconcile demotion gate, adapter key-presence contract, true-only ontology backfill, Coverage OS promote writer, DB migration). Remains a **prerequisite for the next bulk injection** (JECFA / GBIF / INFOODS): those adapters must emit `asserted_flags` via the shared `map_record` path (already does) before a live inject.

**Why this exists.** `false` on an ontology / group boolean has never meant “verified no.” `Ingredient` defaults every bool to `False`, `to_dict()` always writes them, `from_dict()` / `adapt.map_record` fill missing keys with `False`. The live contradiction is already in the file: `canthaxanthin` carries `synthetic: false` and `uncertainty_flags: ["may_be_synthetic_or_animal_derived"]` on the same row. Without a marker, `reconcile()` cannot tell “new positive on unset” from “override of a real negative,” so leaving demotion alone was correct and patching demotion without this field would be wrong.

---

## 1. Meaning

`asserted_flags: list[str]` = the set of boolean flag names for which the **stored value** (true *or* false) was deliberately set by a writer that knew it was making a decision.

| Stored value | Name in `asserted_flags`? | Meaning |
|--------------|---------------------------|---------|
| `true` | yes | Known positive |
| `false` | yes | Verified negative |
| `false` | no | Unset / dataclass or adapter default |
| `true` | no | Should not appear going forward; see §5 backfill for legacy |

Absent key or empty list ≡ nothing asserted. Compliance and resolve keep reading the boolean columns exactly as today; only writers and `reconcile()` care about the marker.

This is deliberately a **name list**, not a parallel bool map and not `Optional[bool]` per flag. One field, sorted unique strings, aligned with how `uncertainty_flags` already travels.

---

## 2. Dataclass (`backend/core/ontology/ingredient_schema.py`)

Add one field next to `uncertainty_flags`:

```python
asserted_flags: list[str] = field(default_factory=list)
```

Rules:

- Only names that are boolean columns on the same object (the `Ingredient` origin/allergen/diet bools, or the parallel `BOOL_FLAGS` set on the ike2 group path — see §6).
- Store sorted unique strings on write; readers may tolerate unsorted.
- Do **not** change any existing `bool = False` defaults. The marker is additive; inventing three-state booleans would churn every consumer.

---

## 3. Serializers (both)

### 3.1 `Ingredient.to_dict` / `Ingredient.from_dict`

- `to_dict`: always emit `"asserted_flags": list(self.asserted_flags)` (empty list when none), same pattern as `uncertainty_flags`.
- `from_dict`: `asserted_flags=d.get("asserted_flags", []) or []`. Missing key → empty list (legacy rows load as “nothing asserted”).

### 3.2 Ontology / Coverage OS row shape

`data/ontology.json` ingredients today mix:

- flat booleans (bulk of rows), and
- nested `flags` plus flat copies on Coverage OS–managed rows (`promote_writer._apply_ontology_row`).

Design:

- Persist **`asserted_flags` at the ingredient row top level** (sibling of `uncertainty_flags` / `canonical_name`), not buried only inside nested `flags`.
- When Coverage OS writes nested `flags`, it may also list the keys it deliberately set in top-level `asserted_flags`. Nested `flags` stays value storage; the marker is the decision record.
- Writers that currently dump a full false-filled flag block (serializer defaults) must **not** auto-copy every key into `asserted_flags`. Only keys the writer explicitly decided.

No mass rewrite of `ontology.json` in the implementation PR beyond what §5 allows. New writes and optional cheap backfill only.

---

## 4. `reconcile()` (`backend/core/knowledge/ike2/etl/reconcile.py`)

Today: for each incoming flag, `new_val = existing_val or incoming_val`; if `new_val != existing_val` → `needs_review` and demote to `DISCOVERED`. That fires on every false→true, including defaults.

Target behavior (once marker exists):

1. Keep most-restrictive OR merge for the boolean value.
2. Merge asserted sets:  
   `merged_asserted = set(existing.asserted_flags) | set(incoming_asserted)`  
   plus: any flag whose **incoming** value was asserted and wins (or ties) stays asserted; any flag newly set true from an asserted incoming true is asserted.
3. **`needs_review` / demotion** only when the stored value changes **and** the pre-merge existing value was asserted:

   ```text
   if new_val != existing_val and flag in existing_asserted:
       needs_review = True
   ```

   So:

   - unset `false` + incoming `true` → adopt true, assert the flag, **no demotion**
   - asserted `false` + incoming `true` → adopt true (OR), **demote** (real conflict with a verified negative)
   - asserted `true` + incoming `false` → keep true (unchanged), no demotion (already ignored today)

4. Return shape: extend `ReconcileResult` with `merged_asserted_flags: list[str]` (sorted). `bulk_inject.SupabaseWriter.update_group` must persist it (column or JSON field — implementation detail; design requires the field on the group update payload, not only in memory).

5. Protected higher-tier rows: unchanged — still refuse lower-tier overwrite; no new demotion path.

Until adapters emit `asserted_flags` for keys present in the raw dump (§6), incoming asserted is empty and demotion stays as today for legacy existing asserts only. After §5’s cheap true-backfill, historical falses remain unasserted, so the next inject’s false→true additions stop demoting — which is the intended unlock.

**Do not ship the demotion gate without the marker and without adapter “key was present” tracking.** Shipping the gate alone with empty asserted everywhere would silence demotion globally, including future real verified-negative conflicts.

---

## 5. Forward-only vs backfill — decision

### Verdict

| Scope | Decision |
|-------|----------|
| New writes after implementation | **Required.** Every writer that deliberately sets a bool must add that name to `asserted_flags`. |
| Historical `false` | **Do not backfill.** Treating any existing false as verified would invent curation we do not have (canthaxanthin is the proof). |
| Historical `true` | **Cheap, honest optional backfill.** A true cannot come from the dataclass/adapter default; it was set by some writer. On first migration pass: for each bool column that is `true`, add that name to `asserted_flags`. Idempotent. |
| Coverage OS `reviewer_id` | **Does not retroactively assert ontology flags.** See below. |

### Why `reviewer_id` is not a flag assertion

Measured against `data/coverage_os/phase2a_role_seed_ledger.jsonl` (only promote ledger present):

- 132 `promoted` rows, all `auto: false` with `reviewer_id`.
- 120 carry `payload.flags: {}` — role-only intent.
- 12 carry a nonempty flag block; every one is `inverse.role_patch_only: true`. The only trues are `plant_origin` (12) and `fermented` (2); the accompanying falses are a full default dump (12–14 falses each).
- For non–`coverage_os_managed` rows, `promote_writer._apply_ontology_row` **returns after patching `role` only** and never writes those payload flags onto `ontology.json`.

So `reviewer_id` means “a human approved this promote ledger entry,” almost always a **role** decision. It does not mean “a human verified every boolean on the ontology row,” and it does not even mean the ledger’s false-filled flag block was applied. Using reviewer_id to mark all flags (or all falses) on those canonicals as asserted would be inventing verified negatives.

**Narrow ledger-derived backfill that would be honest if we ever need it:** only names that appear as `true` in a human (`auto: false`) promote payload *and* that were actually written to L2. Today that set is empty for role_patch_only promotions (flags not written). After writers start asserting, future human flag edits can append to `asserted_flags` at promote time — that is forward path, not retroactive.

### HIGH-confidence verified flags

“Human promoted through Coverage OS” ≠ HIGH-confidence **flag** verification given current ledger contents. HIGH-confidence for backfill is only:

1. **value is already `true`** (optional bulk backfill above), or
2. **future** explicit human/API write that sets a value and lists the name in `asserted_flags` (including intentional `false`).

No silent backfill of falses from `knowledge_state` (`VERIFIED` / `LOCKED`) either: those states were not earned by per-flag negative review under the current schema.

---

## 6. Adapter / inject contract (needed before next source)

`adapt.map_record` today builds:

```python
row = {flag: bool(raw.get(flag, False)) for flag in BOOL_FLAGS}
```

That is the same default-false problem on the **incoming** side. For the next bulk source:

1. Track which flag keys were **present** in `raw` (or explicitly set by a curated derivation such as `derive_identity_flags` / nut mapping).
2. Emit `asserted_flags` = those names only.
3. Pass that list into `reconcile` as incoming asserted; `insert_group` stores it on new rows.

Without (1)–(3), new dumps still look like “asserted false” for every omitted column and the marker buys nothing.

`BOOL_FLAGS` (ike2 group) and `Ingredient` bool fields are not identical sets (`peanut_source` / `tree_nut_source` / enzyme flags vs legacy `nut_source`). `asserted_flags` entries must be names valid on the object being written; do not invent cross-schema aliases in the list.

DB note (implementation later): `ike2_ingredient_groups` will need a column (e.g. `text[]` / JSONB) included in `_GROUP_COLUMNS`. Out of scope for this design doc’s acceptance criteria beyond “reconcile result + writer persist it.”

---

## 7. Who must write the marker (forward)

| Writer | When to add names to `asserted_flags` |
|--------|----------------------------------------|
| Human / Coverage OS promote that sets flags | Every flag key deliberately set in the payload (true or false). Role-only promotes: leave flags/asserted untouched. |
| Bulk adapters | Keys present in raw + keys set by explicit derive helpers. |
| Hand / LOCKED anchors | Every flag in the anchor payload. |
| Serializer defaults / “emit full false block” | Never. |

---

## 8. Acceptance criteria for the later implementation PR

1. Field on `Ingredient`; `to_dict` / `from_dict` round-trip; missing key → `[]`.
2. `ontology.json` rows may carry top-level `asserted_flags`; readers tolerate absence.
3. `reconcile()` returns merged asserted list; demotes only when flipping an **asserted** existing value.
4. Optional one-shot: backfill asserted names for existing `true` booleans only; zero false backfill; no reviewer_id false promotion.
5. Adapters emit asserted from key presence before the next inject is allowed to run live.
6. No demotion-rule change in a PR that does not also ship (1)–(3) and (5).
7. Tests: unset false→true no demotion; asserted false→true demotes; true backfill idempotent; role-only promote does not assert flag names.

---

## 9. Decision summary (open thread from regional expansion)

**Build `asserted_flags` before the next bulk source.** Forward writes required; historical falses stay unasserted; optional cheap backfill of historical trues only; **Coverage OS `reviewer_id` does not count as retroactive flag assertion** given current ledger semantics (role seeds, empty or unapplied flag payloads, serializer falses). That is the scoped fix that makes a later demotion gate safe instead of a silent assumption about which direction is correct.

**Live-DB audit (do not rely on the next inject to find this):** After the 2026-10-05 repair of ontology-row full-block pollution (1,698 rows asserting falses), any future bulk source should assume a **deliberate full-table `asserted_flags` audit** may still be needed on environments that were not repaired — do not wait for the next dump’s overlap to stumble into a slice of the same signature. See `docs/item11_asserted_flags_live_repair.md`. **Item 12 carry:** once observability lands, a scheduled Beat that only *reports* reappearance of that signature is the structural guarantee — park implementation there, not as a standalone Item 11 task.
