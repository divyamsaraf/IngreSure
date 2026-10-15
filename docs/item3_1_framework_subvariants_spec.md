# IngreSure — Build Specification: Item 3.1
## Framework sub-variants (fermentation / enzyme / fungal)

**Status:** Done (batch 1 v1) — enzyme Option A + goldens; koji-family firm Avoid remains P2.  
**Companion:** `docs/phase2_gap_analysis.md` § Item 3.1 · [`item3_1_p2_backlog_koji_family.md`](item3_1_p2_backlog_koji_family.md) · Item 16 stage log (fungal/tempeh) · `flag_derive.py` · `rules.py` Jain rows · `docs/item2_entity_resolution_spec.md` (process-flag propagation 2.1) · tracker row **3.1**

---

## 0. How to use this document

Item 3.1 closes **remaining** fermentation / enzyme / fungal sub-variant gaps after the yeast/tempeh Jain false-SAFE class was fixed. It does **not** rebuild the rule engine (Item 4) or compound decomposition (Item 2.1) — it coordinates flags, anchors, and rules those systems consume.

**Binding decisions:**

- Koji / miso / tamari / natto under Jain: **Depends (UNCERTAIN) is acceptable now**; firm Avoid is a **bounded P2 backlog** (truth-anchor pattern), not a blocker for closing 3.1’s enzyme taxonomy work.
- Process flags for compound propagation stay `{fungal, fermented}` unless Item 2.1 expands them — enzyme origin is a **separate** typed field/flag, not a substitute for `fungal`.

Keep this at `docs/item3_1_framework_subvariants_spec.md`.

---

## 1. Current state (confirmed — act on this)

| Capability | Evidence | Status |
|------------|----------|--------|
| Jain `fungal` FAIL | `rules.py` RULE_SEED; DB seeds | Live |
| Jain `fermented` WARN | `rules.py` `action: WARN`; `test_jain_fermented_warns_not_fails` | Live |
| Name → fungal | `flag_derive.py` `_FUNGAL_NAME_TOKENS` / `_FUNGAL_WHOLE_NAMES` (yeast, tempeh, koji, mushrooms, …) | Live |
| Yeast truth anchors | `truth_anchor.py` yeast family `fungal=True` | Live |
| Bare `enzymes` | Compound / `verdict_cap=WARN` — umbrella fail-closed | Partial |
| Enzyme origin subtypes | No microbial vs animal (e.g. rennet) typing | **Missing** |
| Koji/miso/tamari/natto | Often unresolved → Depends | Acceptable now; firm Avoid = P2 |

---

## 2. Purpose

Make fermentation- and enzyme-related identity **typed enough** that safety-critical diets (especially Jain + allergen-adjacent enzyme sources) cannot collapse distinct origins into an under-specified umbrella — without over-claiming firm Avoid on foods still incompletely resolved.

---

## 3. Scope

### In scope (v1)

- Define enzyme **origin** subtyping sufficient for rules: at minimum distinguish **animal-derived** vs **microbial/fermentation** vs **unknown** enzyme sources.
- Wire subtype into flag derive and/or dedicated group fields + RULE_SEED entries where a diet already cares (start with Jain / vegetarian / vegan sensitivity to animal enzymes — confirm against existing categories in Prompt 1).
- Keep bare `enzymes` fail-closed (WARN/UNCERTAIN) when subtype unknown.
- Goldens: yeast/tempeh/nutritional yeast never firm SAFE under Jain (already); add enzyme-subtype cases (animal rennet vs microbial protease).
- Document P2 backlog list: koji, miso, tamari, natto → firm Jain Avoid via anchors/flags (Depends OK until then).

### Explicitly out of scope

- Turning Depends→Avoid for koji/miso/tamari/natto in this item’s critical path (P2 backlog).
- Rewriting `evaluate()` multi-restriction logic (Item 10.1).
- Nutrition lifestyle restrictions.
- LLM classification of enzyme origin on the hot path (enrichment LLM may assist offline under Item 6 — must not be required for SAFE).

---

## 4. Target design

### 4.1 Prefer additive flags over string enums when possible

Investigate first (Prompt 1), then choose **one**:

| Option | Shape | Prefer when |
|--------|-------|-------------|
| **A (recommended)** | Boolean flags e.g. `enzyme_animal_source`, `enzyme_microbial_source` with CHECK that unknown ⇒ neither true, or uncertainty_flags | Fits existing flag×rule pattern in `RULE_SEED` |
| **B** | `enzyme_origin text` CHECK (`unknown`\|`animal`\|`microbial`\|…) | Fewer columns; needs operator/`eq` support |

Do **not** invent both.

### 4.2 Rule sketch (illustrative — confirm in Prompt 1)

- Vegetarian / vegan / Jain: `enzyme_animal_source` → FAIL (or existing animal_origin implication if CHECK ties them).
- Unknown enzyme umbrella: retain `verdict_cap` / UNCERTAIN — never SAFE.
- `fermented` remains WARN under Jain (unchanged).
- `fungal` remains FAIL under Jain (unchanged).

### 4.3 Derive + anchors

- Extend `flag_derive` **only** for high-confidence name tokens (e.g. “rennet”, “animal rennet”) — fail-closed, no fuzzy.
- Truth-anchor curated rows for common enzyme labels used in goldens.
- Compound foods: Item **2.1** must OR process flags; enzyme animal subtype must also survive expansion or keep-whole (same tempeh class lesson).

### 4.4 P2 backlog (track, do not block)

| Food | Target under Jain | Interim |
|------|-------------------|---------|
| koji, miso, tamari, natto | Firm Avoid (fungal and/or fermented identity complete) | Depends / UNCERTAIN OK |

Detail + Item 2.1 link: [`item3_1_p2_backlog_koji_family.md`](item3_1_p2_backlog_koji_family.md). Prompt 6 (anchors) not authorized in batch 1.

---

## 5. Safety invariants

1. Unknown enzyme origin → never firm SAFE under diets that forbid animal enzymes.
2. Do not mark microbial enzymes as animal (false Avoid) without evidence.
3. Do not weaken existing fungal FAIL / fermented WARN Jain behavior.
4. No hot-path LLM for subtype.
5. P2 firm-Avoid foods must not be silently marked SAFE while still Depends.

---

## 6. Numbered build prompts for Cursor

**Prompt 1** — Investigate: how bare `enzymes` is represented today (truth_anchor / ontology / compounds); which restriction categories should gain enzyme-animal rules; recommend Option A vs B with schema impact. No behavior change.

**Prompt 2** — Schema + RULE_SEED (+ migration seed) for chosen representation; CHECK implications if tying to `animal_origin`.

**Prompt 3** — `flag_derive` + truth anchors for rennet / documented animal enzyme labels; unit tests.

**Prompt 4** — Goldens: animal enzyme → Avoid under vegan/vegetarian/Jain as specified; microbial or unknown → not firm SAFE where required; existing yeast/tempeh Jain never-SAFE still green.

**Prompt 5** — Docs: P2 backlog table for koji/miso/tamari/natto; link Item 2.1 for process-flag OR; stage log.

**Prompt 6** — (P2, separate authorization) Truth-anchor / flag pass for koji/miso/tamari/natto firm Jain Avoid — same pattern as tempeh.

---

## 7. Success criteria

- [x] Enzyme unknown cannot firm-SAFE under targeted diets.
- [x] Animal vs microbial (or chosen) subtype represented and tested.
- [x] Jain fungal/fermented regressions still pass.
- [x] P2 backlog explicitly listed (koji/miso/tamari/natto).
- [x] Tracker Item 3.1 Notes point here.

### Stage log

| When | Notes |
|------|-------|
| 2026-09-17 | Draft; Depends OK for common fermented foods; enzyme subtype is the v1 gap. |
| 2026-09-17 | **Prompt 1 done.** Bare enzymes = compound WARN; Option A recommended. |
| 2026-09-17 | **Prompt 2 done.** Migration `20260918010000_ike2_enzyme_origin_flags.sql`. `RULE_SEED` / `VALID_FLAG_COLUMNS` / `BOOL_FLAGS` / validate / `is_animalish` for Option A. Next: Prompt 3 flag_derive + anchors. |
| 2026-09-17 | **Prompt 3 done.** `flag_derive` animal-enzyme tokens; truth anchors rennet/pepsin gain `enzyme_animal_source`; bare enzymes stay compound WARN. Tests: `test_enzyme_flag_derive.py`. |
| 2026-09-18 | **Prompt 4 done.** Goldens `test_enzyme_goldens.py` (animal rennet/pepsin Avoid; microbial not false Avoid; bare enzymes never firm SAFE; yeast/tempeh Jain never-SAFE). |
| 2026-09-18 | **Prompt 5 done.** P2 backlog doc [`item3_1_p2_backlog_koji_family.md`](item3_1_p2_backlog_koji_family.md) + Item 2.1 link. Prompt 6 (firm Avoid anchors) **not** authorized. Item **3.1** v1 closed for batch 1. |
