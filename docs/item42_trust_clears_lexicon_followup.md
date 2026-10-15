# Item 42 follow-up — trust ceiling, asserted clears, live lexicon

**Date:** 2026-10-13  
Companions: [`item42_trust_leak_scan.json`](item42_trust_leak_scan.json) · [`item42_asserted_clears_audit.json`](item42_asserted_clears_audit.json) · [`item42_live_lexicon_scan.json`](item42_live_lexicon_scan.json) · [`../data/usda_reviewed_asserted_clears.json`](../data/usda_reviewed_asserted_clears.json)

## 1. Trust leak (marker split)

**Bug:** `usda_fdc_category_derived` omitted `inferred`, so `is_trusted_for_compliance` returned true for whole groups. Kind evidence is per-flag; breaded/battered/creamed finfish rows could firm-SAFE under gluten/egg/dairy.

**Fix:**

- `is_trusted_for_compliance`: any `category_derived` token ⇒ untrusted (group SAFE ceiling). Item 42 still lets allergy/medical FAIL stand.
- Transform: category-only kind rows emit `usda_fdc_category_derived` **and** `usda_fdc_bulk_inferred`.
- Test: `test_breaded_fish_shellfish_never_safe_under_gluten_egg_dairy`.

**Scan after fix:** firm SAFE with processed-name hint + missing flag on category_derived candidates → **0**.

## 2. Asserted clears

**Capability risk:** transform-emitted asserted false clears sticky OR trues — opposite of reconcile’s “never drop a positive.”

**Fix:** clears only from reviewed list [`data/usda_reviewed_asserted_clears.json`](../data/usda_reviewed_asserted_clears.json). Shellfish false friends are an enumerated name set (not a broad oyster regex). `asserted_clear_allowed` refuses lexicon hits unless listed.

**Audit:** **218** asserted clears in dump; **all** on reviewed list; **0** processed-form (sauce/extract/paste/powder/oil/broth/canned) or both-case (eggnog/custard/quiche/soufflé) clears. Full `(name, flag, rule)` inventory in the JSON artifact.

**Cap:** a wrong clear still leaves the group untrusted → UNCERTAIN, not SAFE.

## 3. Live-group lexicon scan (6,913)

Name-implied hazard vs absent flag vs production SAFE under the implied restriction:

| Family | SAFE (flag absent) |
|--------|-------------------:|
| gluten_source | 16 |
| dairy_source | 13 |
| shellfish_source | 10 |
| fish_source | 7 |
| soy_source | 1 |
| **total** | **47** |

OFF-unmatched hazard-prone names with SAFE: **33** (listed first in the JSON). Many are intentional false friends (oyster mushroom, almond/hemp milk) or FSSAI phrasing noise (`for use in shrimps…`); residual real gaps stay for standing audits.

### L3-only USDA false-Avoid precision (≤50/family, lexicon heuristic)

| Flag | n | lexicon agrees | disagrees |
|------|--:|---------------:|----------:|
| fish_source | 50 | 49 | 1 |
| shellfish_source | 38 | 38 | 0 |
| dairy_source | 50 | 46 | 4 |
| egg_source | 50 | 44 | 6 |
| gluten_source | 50 | 49 | 1 |
| soy_source | 50 | 43 | 7 |
| tree_nut_source | 49 | 20 | 29 |
| peanut_source | 41 | 41 | 0 |
| sesame_source | 13 | 13 | 0 |

L1/L2 precision (856 shielded) remains biased; L3 sample is the independent check for firm Avoids. Tree-nut disagrees need human review (broad name/category bleed).

## 4. Labelling

Verification changelog wording: **policy-changed, never toward SAFE** (not “tighten only”).

## 5. Hard-sweep exit

After this follow-up: stop hard sweeps. Standing audits = CI replay (repo drift) + `scripts/ike2_item12_scheduled_audits.py` (see [`item12_scheduled_audits.md`](item12_scheduled_audits.md)). Beat/alerting still belongs to Item 12 proper.

Tree-nut / 47 / clears provenance: [`item42_tree_nut_and_47_followup.md`](item42_tree_nut_and_47_followup.md).
