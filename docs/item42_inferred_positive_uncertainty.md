# Item 42 — Inferred positives softened to UNCERTAIN (report)

**Status:** report + fix landed 2026-10-13  
**Priority:** P0  
**Companion:** Item **34** · Item **41** · [`item42_inferred_positive_fix.md`](item42_inferred_positive_fix.md) · [`item42_safe_inferred_26.md`](item42_safe_inferred_26.md) · [`item42_kind_and_capstone.md`](item42_kind_and_capstone.md) · tracker row **42**

## Mechanism (Item 34 path, different gate)

Item 34: triggered FAIL stands despite low knowledge_state. That path is never reached when trusted=False.

resolution_trust.is_trusted_for_compliance: any uncertainty flag containing 'inferred' ⇒ trusted=False for non-static sources. _verdict_for returns UNCERTAIN before the FAIL/Item-34 branch.

L1/L2 (source=static) are always trusted, so the same inferred token on an ontology/truth-anchor row would not soften FAIL — the trap is L3 DB rows.

Demo `fish cod atlantic cooked dry heat`: {'restriction': 'fish_allergy', 'verdict': 'UNCERTAIN', 'layer': 'L3_db_alias', 'trusted': False, 'flag_on_ci': True}

## Live exposure

- Groups scanned: **6913**
- Allergen-true × `*_inferred` pairs: **1453** (1453 unique name×flag)
- Softened FAIL (flag on CI, untrusted, UNCERTAIN): **1259**

### By source

- `usda`: 1012
- `infoods`: 390
- `ifct`: 51

### By source × flag (top)

- `infoods` / `fish_source`: 311
- `usda` / `dairy_source`: 225
- `usda` / `egg_source`: 214
- `usda` / `fish_source`: 183
- `usda` / `gluten_source`: 121
- `infoods` / `shellfish_source`: 78
- `usda` / `soy_source`: 69
- `usda` / `shellfish_source`: 60
- `usda` / `tree_nut_source`: 60
- `usda` / `peanut_source`: 45
- `ifct` / `egg_source`: 16
- `ifct` / `shellfish_source`: 13
- `usda` / `sesame_source`: 11
- `ifct` / `fish_source`: 10
- `usda` / `sulphite_source`: 10
- `ifct` / `gluten_source`: 7
- `usda` / `celery_source`: 7
- `usda` / `mustard_source`: 6
- `ifct` / `dairy_source`: 3
- `ifct` / `soy_source`: 2
- `infoods` / `peanut_source`: 1
- `usda` / `lupin_source`: 1

### Verdicts today (source × flag × verdict)

- `infoods` / `fish_source` → **UNCERTAIN**: 303
- `usda` / `dairy_source` → **UNCERTAIN**: 203
- `usda` / `egg_source` → **UNCERTAIN**: 193
- `usda` / `fish_source` → **UNCERTAIN**: 112
- `usda` / `gluten_source` → **UNCERTAIN**: 109
- `infoods` / `shellfish_source` → **UNCERTAIN**: 76
- `usda` / `fish_source` → **NOT_SAFE**: 71
- `usda` / `soy_source` → **UNCERTAIN**: 62
- `usda` / `tree_nut_source` → **UNCERTAIN**: 48
- `usda` / `shellfish_source` → **UNCERTAIN**: 41
- `usda` / `peanut_source` → **UNCERTAIN**: 40
- `ifct` / `egg_source` → **UNCERTAIN**: 16
- `usda` / `dairy_source` → **SAFE**: 15
- `usda` / `egg_source` → **NOT_SAFE**: 15
- `usda` / `shellfish_source` → **NOT_SAFE**: 14
- `ifct` / `shellfish_source` → **UNCERTAIN**: 13
- `usda` / `gluten_source` → **NOT_SAFE**: 12
- `usda` / `tree_nut_source` → **NOT_SAFE**: 12
- `usda` / `sesame_source` → **UNCERTAIN**: 11
- `ifct` / `fish_source` → **UNCERTAIN**: 9
- `infoods` / `fish_source` → **NOT_SAFE**: 8
- `usda` / `dairy_source` → **NOT_SAFE**: 7
- `usda` / `soy_source` → **NOT_SAFE**: 7
- `ifct` / `gluten_source` → **UNCERTAIN**: 6
- `usda` / `sulphite_source` → **UNCERTAIN**: 6
- `usda` / `egg_source` → **SAFE**: 6
- `usda` / `mustard_source` → **UNCERTAIN**: 6
- `usda` / `celery_source` → **NOT_SAFE**: 5
- `usda` / `shellfish_source` → **SAFE**: 5
- `usda` / `peanut_source` → **NOT_SAFE**: 5

### USDA fish/shellfish evidence split (no raw foodCategory on Layer-1)

{'name_sniffed': 240, 'category_or_other_no_name_match': 3}

`name_sniffed` = fish/shellfish lexicon hits the canonical name. `category_or_other_no_name_match` = flag true without a name hit (the FDC `Finfish and Shellfish Products` path, or other non-name route).

## Hand-check (≤50 per source, heuristic)

- **ifct** (n=50): {'likely_true': 42, 'needs_human': 8}
- **infoods** (n=50): {'needs_human': 31, 'likely_true': 19}
- **usda** (n=50): {'likely_true': 26, 'needs_human': 24} evidence={'name_sniffed': 7}

## Policy recommendation

**inferred_caps_safe_only_for_allergy_medical**

- For allergy + medical restrictions: a triggered positive allergen flag must stand as FAIL even when uncertainty_flags contain *_inferred (Item 34 symmetry). The untrusted gate should not demote triggered FAIL.
- Keep *_inferred as a SAFE ceiling (clean pass → UNCERTAIN/WARN) so bad negatives cannot mint firm SAFE.
- Split markers: category-derived fish/shellfish (FDC foodCategory 'Finfish and Shellfish Products') is stronger evidence than a name sniff — prefer a distinct token (e.g. usda_fdc_category_derived) that does not trip the blanket inferred untrusted gate, OR treat category-derived as asserted without inferred.
- Name-sniffed allergen flags may keep a weaker marker but still must not silence FAIL for allergy/medical once the flag is true.
- Counterweight: measure precision before shipping. Prior USDA dairy_implies_animal contradictions (136) show name/category inference can false-Avoid; the hand sample below is the first cut.

Artifact: `docs/item42_inferred_positive_uncertainty.json`.
