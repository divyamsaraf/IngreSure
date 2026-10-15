# Item 37 Parts A–C — sulfite live closeout + stem triage + structural scans

**Date:** 2026-10-07  
**Companion:** `docs/item7_sulfite_underflag_investigation.md`, `docs/item37_stem_triage_ortho_catalog.json`

## Part A — live E220–E228 + L3 bypass

### A1 Live `ike2_ingredient_groups`

Ontology-seeded E220–E228 groups were backfilled via the normal reconcile/inject path (`e_number_catalog` / ontology, true-only asserted), **not** a direct SQL UPDATE. After strip/re-inject repair of an asserted-false re-pollution from `entry_to_ike2_row` (fixed to true-only), live rows carry `sulphite_source=true` with asserted including `sulphite_source`.

### A2 L3-only matrix (`sulfite_sensitive`)

Harness bypassed L1 file anchors (`_resolve_uncached` + truth-anchor patch). **0 SAFE** across sulfite/sulphite/(meta)bisulfite, sulfur/sulphur dioxide, E220–E228. Many **UNCERTAIN** remain where E-code aliases are ambiguous in L3 — fail-closed, not false-SAFE.

**Item 37 live bar:** Partial → **closed for the sulfite block** on local Supabase (file L1 + live groups + L3-bypass). Broader catalog trust audit still open (see corrections below).

---

## Part B — stem triage + same-day + derive

### B1 Classification counts (ontology stem∩flag≠true families)

| Class | Count | Notes |
|-------|------:|-------|
| **true_miss** (flag asserted true) | **79** | gluten 12, lupin 4, sesame 2, shellfish 9, celery 2, mustard 3, dairy 14, fish 33 |
| **false_friend** (flag asserted false) | **16** | dairy plant-milks/butters, rice semolina, shellfish stem noise, pak choi, crab≠fish |
| **ambiguous** (WARN + uncertainty, no allergen true) | **15** | mustard greens/oil/leaves, lecithins, collagen, shellfish-stem fish names |
| **remaining fish regional** | ~60 | IFCT vernacular names — classified true_miss in principle; **not** bulk-flipped (curated bar) |

Same-day unambiguous set from the user prompt is a subset of true_miss and was repaired first.

### B2 Same-day replay

| | BEFORE | AFTER |
|--|--------|-------|
| einkorn / khorasan / barley forms / idli rava | SAFE | **NOT_SAFE** |
| lupini / lupins / lupine beans | SAFE | **NOT_SAFE** |
| tahini | NOT_SAFE (L1) | NOT_SAFE |
| tahini paste | SAFE | **NOT_SAFE** |
| crustaceans / mollusks | SAFE | **NOT_SAFE** |

Layers after: L1 hand anchors for most canons; barley forms via L2 ontology + derive.

Live inject: `data/layer1_stem_triage_2026-10-07.json` via `--source ontology` (90 updated; 2 rejected then fixed for dual-origin / tofu yogurt). Demotions from asserted-false pollution were restored to `AUTO_CLASSIFIED`; asserted lists stripped to true-only **plus** deliberate false-friend asserts.

### B3 `derive_identity_flags`

Extended with exclusion discipline matching sulfate/acesulfame:

- gluten tokens (einkorn/khorasan/barley/rye/…; never buckwheat)
- lupin / lupine / lupini
- tahini → sesame
- dairy tokens with plant-milk / cocoa-butter / tofu-yogurt exclusions
- mustard (not greens/spinach/oil)
- celery / celeriac
- shellfish umbrella labels (crustaceans/mollusks)

Tests: `tests/ike2/test_allergen_flag_derive.py`.

`adapt.map_record` now **prefers curated `asserted_flags`** when present (ontology true-only + deliberate falses) so full-bool dumps do not re-pollute.

---

## Part C — structural (report + gate)

### C1 Orthographic-variant scan

Applied `sulf/sulph`, `aluminium/aluminum`, `colour/color`, `fibre/fiber` across ontology + catalog aliases (~6882 keys → 61 candidate pairs).

| Severity | Count |
|----------|------:|
| Any verdict mismatch (incl. SAFE/UNCERTAIN) | 544 restriction-rows / **37** unique pairs |
| **SAFE vs NOT_SAFE (firm)** | **0** |

Post-sulfite-fix, remaining mismatches are almost all **SAFE ↔ UNCERTAIN** (one spelling resolves, the other does not) — coverage asymmetry, not a firm false-SAFE split. Notable soft gaps: aluminium/aluminum silicate salts, dried *sulfured* fruit, oat fiber/fibre, acesulfame *sulph* misspellings.

**Gate:** `tests/ike2/test_orthographic_verdict_parity.py` — fails only on SAFE vs NOT_SAFE for a curated high-value pair list.

### C2 Allergen-implicit catalog audit (330 rows)

**Hypothesis:** “allergen columns are False on all 330 rows by generation default, not by decision.”

**Verdict: partially true, not absolute.**

- Core allergen keys (`gluten_source`, `mustard_source`, `sulphite_source`, …) are present on all 330 rows.
- `sesame_source` is **missing** (`null`) on catalog rows — not an explicit False.
- **16 / 330** rows have at least one allergen True (curated decisions), including:
  - E220–E228 `sulphite_source` (this thread’s fix)
  - E1105 lysozyme `egg_source=true` (correct)
  - E441 gelatine `fish_source=true` (species-uncertain animal path)
  - E966 lactitol `dairy_source`; E306/307/426/479 soy-linked
- Implicit-derivation scan (lysozyme, lecithins, lactates, nisin, gelatin):
  - Lysozyme OK (egg true).
  - Lecithins / lactates / nisin remain **all-false / undecided** — stem scan cannot see allergen links absent from the name; needs a dedicated derivation table, not name stems.

Artifact: `docs/item37_stem_triage_ortho_catalog.json`.

---

## Corrections (accepted)

1. Hand-vs-catalog agreement only covers **shared normalized keys**. sulfite ≠ sulphite keys, so the cache-thread agreement test never compared them.
2. “Curated IKE-2 flags” ≠ correct. LOCKED + tier 4 + Item 35 protection can freeze a wrong block; catalog itself needed the fix. JECFA decline stands; catalog trust needs ongoing audit.

---

## Still open (not blocking A)

Follow-up closed 2026-10-08 — see `docs/item37_followup_1_to_5.md`:
- validate_rows asserted-false pollution tripwire; DISCOVERED live = 91 (baseline 89, +2).
- Regional fish: 13 INFOODS-matched flips; 44 human-review.
- Sulfured stems → NOT_SAFE; ortho gate on all 61 pairs; lactates/nisin dairy SAFE reported.
