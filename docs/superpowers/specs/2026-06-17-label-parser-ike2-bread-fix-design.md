# Label Parser + IKE-2 Bread Label Fix — Design Spec

**Status:** Draft — awaiting review  
**Date:** 2026-06-17  
**Trigger:** Sourdough bread label fails IKE-2 (and partially legacy) due to parser + L1 gaps

---

## 1. Problem statement

**Input (user-provided):**

```
Ingredients: Enriched Wheat Flour [Flour, Malted Barley Flour, Reduced Iron, Niacin,
Thiamin Mononitrate (Vitamin B1), Riboflavin (Vitamin B2), Folic Acid], Water,
Sourdough (Wheat Flour), Wheat Gluten, Yeast. Contains 2% Or Less Of Each Of The Following:
Extra Virgin Olive Oil, Sea Salt, Preservatives (Calcium Propionate, Sorbic Acid),
Organic Grain Vinegar, Enzymes.
```

**Observed IKE-2 results (Vegan / Gluten-free):**

| Profile | Legacy | IKE-2 | Expected |
|---------|--------|-------|----------|
| Vegan | UNCERTAIN | UNCERTAIN | SAFE (maybe Depends on enzymes) |
| Gluten-free | NOT_SAFE | UNCERTAIN | NOT_SAFE |

**Root cause chain (systematic debugging):**

1. **Parser** (`flatten_ingredients` / `preprocess_ingredients`) handles `()` but not `[]`, does not strip `Ingredients:`, and does not split on `.` before trace clauses → malformed tokens (`ingredients enriched wheat flour [flour`, `folic acid]`, `yeast each of the following extra virgin olive oil`).
2. **IKE-2 L1** has `wheat`, `barley`, `gluten` but not compound aliases `wheat flour`, `wheat gluten`, `malted barley flour`, nor safe staples `water`, `yeast`.
3. **IKE-2 resolver** → L5 unknown for unresolved atoms → `trusted=False`.
4. **IKE-2 compliance** (`_verdict_for`): untrusted → always `UNCERTAIN`, never `FAIL` — so gluten-free cannot reach NOT_SAFE even when gluten is obvious.

Legacy benefits from `ontology.json` for some tokens (e.g. `wheat flour`); IKE-2 does not.

---

## 2. Goals / Non-goals

### Goals

- Parse FDA-style labels with **square brackets**, `Ingredients:` prefix, and `Contains 2% or less` trace sections.
- IKE-2 **gluten-free** on this label → `NOT_SAFE` (trusted resolution of wheat/barley/gluten).
- IKE-2 **vegan** on this label → `SAFE` or `WARN` at worst (not aggregate `UNCERTAIN` solely from `water`/`yeast`).
- **Zero false-Safe** preserved (IKE-2 invariant).
- TDD: failing tests first for parser + IKE-2 golden row.

### Non-goals

- Full FDA parser rewrite or OCR pipeline changes.
- Bulk DB seed of entire ontology into `ike2_*` tables (separate initiative).
- Changing IKE-2 untrusted→UNCERTAIN policy globally (by design).
- Fixing intent-detector typos (`ski am milk`) — out of scope.

---

## 3. Approaches considered

### A. Parser fix + L1 alias expansion (recommended)

- Extend `_split_by_parentheses` to treat `[` `]` like `(` `)` (shared helper).
- Strip leading `Ingredients:` / `INGREDIENTS:` (case-insensitive).
- Split major segments on `.` when followed by trace introducers (`Contains 2% or less`, etc.).
- Add L1 truth-anchor aliases: `wheat flour`, `wheat gluten`, `malted barley flour`, `enriched wheat flour`, `water`, `yeast`; compound `enzymes` with `verdict_cap=WARN`.
- **Pros:** Surgical, helps legacy + IKE-2, matches existing patterns.  
- **Cons:** L1 must be maintained for common staples.

### B. Normalizer suffix stripping (`wheat flour` → `wheat`)

- Add rules in `normalize_ingredient_key` to strip ` flour`, ` gluten` when base grain is known.
- **Pros:** Fewer L1 entries.  
- **Cons:** Risky false positives (`rice flour` vs `rice`, `corn starch`); violates fail-closed for ambiguous cases.

### C. Fall back to legacy ontology in IKE-2 resolver

- On L5 miss, consult `ontology.json` before unknown.
- **Pros:** Broad coverage quickly.  
- **Cons:** Blurs IKE-2 layer boundaries; harder to audit; not in IKE-2 design.

**Recommendation:** **A** only.

---

## 4. Design

### 4.1 Shared parser changes

**Files:** `backend/core/parsing/ingredient_parser.py`, `backend/core/normalization/parser.py`

1. **`_normalize_label_prefix(raw)`** — strip `^\s*ingredients\s*:\s*` (case-insensitive).
2. **`_split_brackets_and_parens(text)`** — unify `[`/`]` with `(`/`)` in `_split_by_parentheses` (rename to `_split_by_nesting` or extend in place).
3. **Sentence / trace split** — before comma split, split on `\.\s+(?=contains\s+2%|\<2%)` so `Yeast.` and `Contains 2% or less...` are separate segments.
4. **Comma regex** — update to respect both bracket types: `,(?![^(\[]*[\)\]])`.

Both `flatten_ingredients` and `preprocess_ingredients` use the same nesting logic (DRY: extract shared helper module or import from one place).

### 4.2 IKE-2 L1 truth anchor

**File:** `backend/core/knowledge/ike2/truth_anchor.py` (regenerate `truth_anchor_e_numbers.json` only if e-number entries touched — not needed here)

Add aliases:

| Aliases | Canonical | Flags |
|---------|-----------|-------|
| `wheat flour`, `enriched wheat flour`, `flour` (only when nested — prefer explicit aliases) | `wheat` | `gluten_source=True`, `AUTO_CLASSIFIED` |
| `wheat gluten` | `gluten` | `gluten_source=True` |
| `malted barley flour` | `barley` | `gluten_source=True` |
| `water` | `water` | no allergen flags, `AUTO_CLASSIFIED` |
| `yeast` | `yeast` | `fungal=True`, `AUTO_CLASSIFIED` (vegan OK) |
| `enzymes` | `enzymes` | compound: `verdict_cap=WARN` |

Do **not** add bare `flour` without qualifier — too ambiguous.

### 4.3 Expected outcomes after fix

**Parsed atoms (representative):** `wheat`, `barley`, `water`, `wheat flour`, `wheat gluten`, `yeast`, `olive oil`, `sea salt`, `calcium propionate`, `sorbic acid`, `vinegar`, `enzymes`, vitamins/minerals.

| Profile | IKE-2 aggregate |
|---------|-----------------|
| `gluten_free` | `NOT_SAFE` (wheat/barley/gluten trusted) |
| `vegan` | `SAFE` or `WARN` (enzymes capped) |
| `jain` | `WARN`/`UNCERTAIN` (yeast fermented/fungal rules — acceptable) |

### 4.4 Testing strategy (TDD)

1. **Parser:** `tests/test_parser_and_profile.py` — new test with exact user bread string; assert no `[`/`]` in tokens; assert `wheat flour`, `wheat gluten`, `malted barley flour`, `enzymes` present; trace items after `2% or less` marked trace where applicable.
2. **IKE-2:** `tests/ike2/test_pipeline_e2e.py` or new `tests/ike2/test_bread_label.py` — golden rows for gluten_free NOT_SAFE, vegan not UNCERTAIN-from-water.
3. **Regression:** `pytest tests/ike2/ tests/test_parser_and_profile.py` — all pass.

### 4.5 Verification (before completion)

```bash
cd backend
python3 -m pytest tests/test_parser_and_profile.py tests/ike2/test_bread_label.py -v
python3 -m pytest tests/ike2/ -q
# Manual shadow compare
python3 -c "..."  # bread label gluten_free + vegan IKE2_SHADOW lines
```

---

## 5. Success criteria

- [ ] Bread label parses without bracket artifacts or merged yeast/trace token.
- [ ] IKE-2 `gluten_free` → `NOT_SAFE` on bread label (engine test, no API).
- [ ] IKE-2 `vegan` → not `UNCERTAIN` only because of `water`/`yeast`.
- [ ] Existing parser and IKE-2 tests unchanged or improved; no false-Safe regressions in `tests/ike2/test_golden_safety_budget.py`.

---

## 6. Out of scope follow-ups

- RLS policies blocking `ike2_shadow_diffs` inserts on local Supabase.
- Seeding full ontology into IKE-2 L3 DB.
- Intent detector period handling for multi-sentence queries.
