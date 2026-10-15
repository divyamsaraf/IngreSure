# Item 42 follow-up — tree nut, the 47, clears provenance

**Date:** 2026-10-13  
Artifacts: [`item42_usda_tree_nut_inventory.json`](item42_usda_tree_nut_inventory.json) · [`item42_47_classification.json`](item42_47_classification.json) · [`item42_asserted_clears_218_readable.json`](item42_asserted_clears_218_readable.json) · [`item42_precision_sample_hand_labels.json`](item42_precision_sample_hand_labels.json)

## 1. Tree nut (USDA)

**What the 41% was:** the precision-sample lexicon omitted plurals (`almonds`) and tokens (`chestnut`, `pine nut`). Live USDA never had sunflower/pumpkin/sesame as `tree_nut_source` (0 hits). Category bleed was the *risk shape*, not the measured state.

**Fix:** `_tree_nut_from_name` — name lexicon only (almond, walnut, pecan, cashew, pistachio, hazelnut/filbert, macadamia, brazil nut, pine nut, chestnut, praline). **Never** category alone. **Excluded:** coconut, nutmeg, water chestnut, butternut. Seeds never match the lexicon. Transform emits `tree_nut_source` directly.

**Recount:** **63 / 63** USDA tree_nut groups agree with the fixed lexicon (100%). Inventory lists every group with FDC category + matched token.

**Also:** ontology umbrella `nuts` (aliases include USDA-shaped almond/cashew/… names) now asserts `tree_nut_source` so L2↔L3 drift closes for those aliases.

### Hand labels — soy / egg / dairy sample disagrees (17)

| Flag | n | Verdict |
|------|--:|---------|
| soy | 7 | **All real_flag** (soybean/soymilk; scan lexicon was thin) |
| egg | 6 | **All false_flag** (kefir / dessert toppings / Reddi-wip — dairy bleed) |
| dairy | 4 | **All real_flag** (ice cream / frozen yogurt / topping) |

Egg false flags remain residual sticky debt (`whipped topping frozen low fat` still drifts vs L2).

## 2. The 47

All answered **trusted=True** (mostly L2 ontology or trusted L3). Classification:

| Class | n | Action |
|-------|--:|--------|
| false_friend | 21 | Enumerated in [`data/lexicon_scan_false_friends.json`](../data/lexicon_scan_false_friends.json) |
| phrasing_noise (FSSAI) | 11 | Same exclusion list |
| real_gap | 6 | **Patched** |

**Patched (before → after under implied restriction):**

| Name | Flag | Layer |
|------|------|-------|
| chapatti flour | gluten | L2 |
| sardine oil | fish | L2 |
| bread egg / toasted / cheese / salvadoran | gluten | L3 (USDA `bread` → gluten_source) |

After patches + exclusions, lexicon SAFE scan → **0** (Item 12 report).

## 3. Clears provenance

`data/usda_reviewed_asserted_clears.json` was **emitted from the transform’s asserted_flags output**, then filtered (drop processed-form + both-case). **Not** hand-written row-by-row.

Readable dump of all clears as `(name, flag, before→after, rule)`: [`item42_asserted_clears_218_readable.json`](item42_asserted_clears_218_readable.json) (n≈221 after list refresh).

## 4. Item 12 first scheduled task

Wrapper: `backend/scripts/ike2_item12_scheduled_audits.py`

Runs report-only:

1. asserted-false signature  
2. DISCOVERED name inventory / optional diff  
3. L2↔L3 drift by name  
4. lexicon vs verdict over live groups (uses false-friend list)

Output: [`item12_scheduled_audit_report.json`](item12_scheduled_audit_report.json). Spec note: [`item12_scheduled_audits.md`](item12_scheduled_audits.md).

Remaining non-zero: **5** L2↔L3 drifts (4 sulfured dried fruit sulphite; 1 whipped-topping egg false). Lexicon SAFE count **0**.
