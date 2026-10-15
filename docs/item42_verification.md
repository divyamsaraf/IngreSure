# Item 42 — Verification (full suite, golden, precision, roots, CI)

**Date:** 2026-10-13  
**Baseline suite:** 2847 passed, 4 skipped (pre-exclusion / pre-reinject).  
**After verification work:** **2859 passed, 4 skipped** (+12).  
**After trust-ceiling / asserted-clear follow-up:** **2869 passed, 4 skipped**.

## 1. Assertion changelog (old → new; none deleted or loosened)

| Test | Old assertion | New assertion |
|------|---------------|---------------|
| `test_safety_invariants.test_untrusted_never_safe_or_fail` → renamed `test_untrusted_never_safe` | `verdict not in (SAFE, FAIL)` | `verdict != SAFE`; if `FAIL`, restriction ∈ medical set |
| `test_safety_invariants.test_untrusted_peanut_true_is_uncertain_not_fail` → `test_untrusted_peanut_true_is_fail_item42` | external `UNCERTAIN` | external `NOT_SAFE` |
| `test_compliance.test_untrusted_trace_is_uncertain_not_avoid` → `test_untrusted_trace_lifestyle_rule_stays_uncertain` | peanut+trace untrusted → UNCERTAIN | vegan+trace untrusted → UNCERTAIN (lifestyle still capped) |

**Added (policy-changed, never toward SAFE):**

- `tests/ike2/test_item42_inferred_fail_stands.py` — FAIL stands for allergy/medical; clean inferred → UNCERTAIN; vegan/halal/kosher/jain + animal_origin inferred → UNCERTAIN.
- `tests/ike2/test_usda_false_friend_exclusions.py` — oyster mushroom / emu oyster / squash scallop / salsify not shellfish; dairy↔egg category disambiguation; lexicon expansions; Layer-1 asserted clears for sticky OR.
- `tests/ike2/test_item41_42_replay_ci.py` — in-memory replay: (a) no true hazard → SAFE; (b) `live_true && l2_false` empty after replay.
- `tests/ike2/test_item42_trust_ceiling.py` — `category_derived` keeps group SAFE ceiling; breaded fish/shellfish never firm-SAFE under gluten/egg/dairy.
- `tests/ike2/test_usda_asserted_clear_guard.py` — asserted clears enumerated-only; oyster sauce / eggnog cannot clear.

No assertions were deleted or relaxed toward SAFE. Three policy-changed tests (e.g. peanut untrusted `UNCERTAIN` → `NOT_SAFE`) are listed above — direction is never toward SAFE.

## 2. Golden / label fixture verdict diff

Artifact: [`item42_golden_verdict_diff.json`](item42_golden_verdict_diff.json).

- Golden corpus + must-never-be-safe: **0** `UNCERTAIN → NOT_SAFE` flips (cases resolve via L1/L2; trusted path unchanged).
- Production L3 blast (inferred + flag on CI): see §5.

## 3. Religious diet policy check

Intended: under `trusted=False` + `animal_origin=True`, **vegan, halal, kosher, and Jain** all stay **UNCERTAIN** (not in `_ALLERGY_MEDICAL`). Confirmed in code and `test_untrusted_halal_kosher_jain_animal_origin_stay_uncertain`.

## 4. USDA flag precision (L1/L2 answering layer)

Artifact: [`item42_usda_precision_after_reinject.json`](item42_usda_precision_after_reinject.json).

After false-friend asserted clears + re-inject:

- USDA groups answered by L1/L2: **856**
- Per-flag agree / group-true-only / layer-true-only: see JSON.
- Remaining `group_true_only` after clears is residual name/ontology drift (not the oyster-mushroom / dairy↔egg class bugs).

### Code attribution

| Visible error | Cause | Vintage |
|---------------|-------|---------|
| shellfish on oyster mushroom / emu oyster / squash scallop / salsify | Item-37 `_SHELLFISH_NAME` matcher | **This week** (regression) — fixed `_SHELLFISH_FALSE_FRIEND` + asserted clears |
| dairy flagged on eggs / egg flagged on dairy | Original FDC category `"Dairy and Egg Products"` set both bits | **Original** — fixed name disambiguation + asserted clears |

## 5. Blast radius recount (1259 → after re-inject)

Artifact: [`item42_blast_radius_after_reinject.json`](item42_blast_radius_after_reinject.json).

| Metric | Count |
|--------|------:|
| Prior softened FAIL (flag on CI, untrusted, UNCERTAIN) | **1259** |
| Post re-inject L3 + `*inferred*` + flag on CI → **NOT_SAFE** | **1073** |
| Still UNCERTAIN with flag on CI | **0** |
| Δ vs 1259 | **−186** |

Drop drivers: (1) fish/shellfish marker split (`usda_fdc_category_derived` is trusted — no longer in the inferred blast); (2) sticky false-friend / dairy↔egg clears. Remaining 1073 are allergy/medical firm Avoids on inferred L3 rows (safe direction).

## 6. Root causes

### INFOODS kind mapping

Artifact: [`item42_infoods_kind_classes.json`](item42_infoods_kind_classes.json).

Among fish/shellfish INFOODS groups: **32 bivalve**, **4 cephalopod**, **1 gastropod** name-class hits. **0** remain fish-only among those classes after the scallop name-lexicon fix.

`american sea scallop` was fish-only because sheet-09 subgroup was empty/wrong; `flags_for_sheet` only set shellfish from subgroup tokens. Fix: name lexicon (`scallop`, etc.) when subgroup misses.

### Shellfish lexicon

USDA + INFOODS now match: crayfish, crawfish, langoustine, krill, yabby (plus prior crustacean/mollusc tokens). Covered by `test_real_shellfish_lexicon_expansions`.

### OFF ancestry coverage

Artifact: [`item42_off_ancestry_coverage.json`](item42_off_ancestry_coverage.json).

| | |
|--|--:|
| Universe (ontology ∪ live groups) | **6913** |
| Matched to OFF `en:` node | **612** |
| Match rate | **8.85%** |
| Unmatched hazard-prone names (lexicon hit) | **966** (sample in JSON) |

## 7. CI

`.github/workflows/ci.yml` step **Item 41/42 replay CI** runs `tests/ike2/test_item41_42_replay_ci.py` (in-memory FakeWriter: ontology + dumps, no Supabase).

Item 41 option-C note updated in [`item41_l2_l3_dual_store_authority.md`](item41_l2_l3_dual_store_authority.md): the shared replay harness closes the “need seeded Supabase for the guard” objection.
