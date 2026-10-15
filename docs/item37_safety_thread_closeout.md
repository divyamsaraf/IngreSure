# Item 37 safety thread — closeout (synthetic / no-kind / adapt)

Closes the post-reinject push. Standing version of these scans belongs in **Item 12** as a scheduled audit (asserted-false signature, animal no-kind name diff, DISCOVERED name diff, stem-vs-flag over live groups), ahead of Batch 4 (12, 13, 14) and the thin Item 8 spec.

## 1. Synthetic restore → minimal form

**Does anything read `synthetic`?** No. It is listed in `VALID_FLAG_COLUMNS` but no `RULE_SEED` row triggers on it. Caps / uncertainty use text flags like `may_be_synthetic_or_animal_derived`, not the boolean.

**Blanket asserted-false was wrong.** The Phase-1 restore set `synthetic=false` + asserted that false on ~77 FSSAI-demotion rows without per-row evidence. That is the move the asserted_flags design forbids.

**Switched to minimal form** (direct patch, not reconcile asserted-false):

| State | `synthetic` | asserted? | KS |
|-------|-------------|-----------|-----|
| After Phase-1 demotion | `true` (FSSAI OR) | typically true-only after strip | `DISCOVERED` |
| After blanket restore (reverted) | `false` | **yes** (`synthetic` in asserted_flags) | `AUTO_CLASSIFIED` |
| After minimal | `true` (dump value) | **no** | `AUTO_CLASSIFIED` |

Per-row table: `docs/item37_synthetic_nokind_adapt_followup.json` → `1_synthetic.rows`.

**Focus**

- `canthaxanthin`: uncertainty `may_be_synthetic_or_animal_derived` kept; synthetic dump-true **unasserted** (contradiction visible again via uncertainty, not a verified negative).
- `polyglycerol esters of fatty acids`: uncertainty `animal_or_plant_fatty_acid_source` kept; same minimal form.
- turmeric / paprika / agar / guar / xanthan: same — dump `synthetic=true` unasserted; nothing reads it, so verdict paths unchanged.

## 2. Animal no-kind bucket (report only)

Live `animal_origin` + no kind flag: **852** (down from 874 after IFCT fish/shellfish flags).

### 2a INFOODS split-match

Split live INFOODS fish/shellfish aliases on `,;` / `aka` into **phrase-level** common names and binomials (no bare-token index — that falsely matched `meat`→tuna / `liver`→cod liver).

| Match mode | Count |
|------------|------:|
| Exact name = INFOODS part | 0 |
| Multi-word INFOODS tokens ⊆ live name | **63** |

Examples: `crustaceans crab dungeness raw` ↔ `dungeness crab`; `fish cod atlantic raw` ↔ `atlantic cod`. Full list in the followup JSON / `item37_animal_no_kind_hand_read.json`.

### 2b Hand / lexicon read

| Source | Count | Tags |
|--------|------:|------|
| ontology | 86 | land_meat 31; **fish_suspect 8** (canned herring/mackerel/sardines/sprats/seafood, dried/salted/smoked seafood); dairy 1; other 46 |
| ifct | 82 | **land_meat 63**, other_animal 19 — no residual fish/shellfish lexicon hits after IFCT reinject |
| usda | ~682 | lexicon fish/shellfish suspects **148** (mostly `fish …` / `crustaceans …` composition rows still lacking kind flags) |

### 2c COMPUTED_OK vs FINDING rules

Printed in followup JSON `finding_rules`:

- **COMPUTED_OK**: SAFE-side has no matching species-allergen identity for the restriction. Cross-species SAFE is OK (fish under `shellfish_allergy` without `shellfish_source`).
- **FINDING (`fish_allergy`)**: SAFE + (`fish_source` OR `animal_species` fish*) **or** SAFE + `animal_origin` + **no kind flag** (unflagged-fish shape). **Yes — that shape is a FINDING.**
- **FINDING (`shellfish_allergy`)**: SAFE + shellfish identity only. Bare `animal_origin` is **not** a FINDING under shellfish.

No flips applied from this report.

## 3. Adapt root fix

`map_record`: unless the dump ships `asserted_flags`, **assert trues only**. Sparse false keys are values, not verified negatives. Curated falses still go through explicit `asserted_flags` (+ `curated_asserted_negatives` for the tripwire escape).

Test: `test_sparse_false_keys_are_not_asserted` — 12 false keys, none asserted.

`validate_rows` / `asserted_flags_false_pollution` stays the **second line**.

## Artifacts

- `docs/item37_synthetic_nokind_adapt_followup.json`
- `docs/item37_animal_no_kind_hand_read.json`
- `backend/scripts/item37_synthetic_nokind_adapt_followup.py`
