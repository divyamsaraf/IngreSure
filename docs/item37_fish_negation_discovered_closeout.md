# Item 37 — fish live gap, free-from negation, DISCOVERED hygiene (2026-10-08)

## 1. Fish / shellfish

### 1a Before re-inject

| Metric | Count |
|--------|------:|
| Live `source=ifct` groups | 324 |
| Of those in repaired IFCT fish/shellfish chapter (by name) | 23 |
| Chapter underflagged (`fish_source`/`shellfish_source` false) | **23** |
| Live IFCT with `fish_source=true` | **0** |
| Underflag verdicts (`fish_allergy`/`shellfish_allergy`) | 22× UNCERTAIN/UNCERTAIN, 1× NOT_SAFE/SAFE |

Same “fixed in files, not live” gap as sulfite before Part A.

### 1b Re-inject (replay proof)

- Regenerated `data/layer1_ifct.json` with fish/shellfish inference **and true-only flag emit** (false keys were tripping `asserted_flags_false_pollution` — 538/540 rejects on the first attempt).
- Ontology-seeded dry-run: **0** `needs_review` / **0** new DISCOVERED.
- Live-seeded dry-run: **0** demotions.
- Live inject: 540 updated, 0 rejected, 0 demotions; DISCOVERED diff empty.

### 1b After

| Metric | Count |
|--------|------:|
| Chapter underflagged | **0** |
| Live IFCT `fish_source=true` | **10** |
| Live IFCT `shellfish_source=true` | **13** |
| (10+13 = 23 chapter rows) | |

Samples: `pomfret black` fish=true; `prawns big` shellfish=true; `kalava` fish=true. Oyster mushroom stays non-shellfish.

### 1c Animal no-kind (report only — no flips)

| | |
|--|--:|
| `animal_origin` and no kind flag | **874** |
| by source | ifct 104, ontology 86, usda 682, infoods 2 |
| Exact alias/scientific match to live INFOODS fish/shellfish | **0** |

Unmatched names written to `docs/item37_animal_no_kind_unmatched.json`. English species names (snapper, trevally, …) remain outside stem scans; vernacular IFCT was only one slice.

### 1d Ortho allergy SAFE-side review (computed)

Replaced templated `OK: orthographic coverage gap…` stamps with per-row resolve + flag snapshot (`COMPUTED_OK` / `FINDING`).

- SAFE↔UNCERTAIN pairs reviewed: **525**
- Species-allergen false-SAFE findings in that set: **0** after IFCT/live fish flags
- `blubberlip snapper … multi coloured snapper` under `fish_allergy` is now **NOT_SAFE** (fish identity present); `… colored …` remains **UNCERTAIN** (coverage gap, not a false-SAFE)

## 2. Negation (free-from)

Probe had **56** label-derived Avoids on free-from phrases.

Fixes:
1. `_family_negated` / `is_free_from_claim` in `flag_derive.py` — suppress identity derive for the claimed family.
2. `expand_compounds` keep-whole on free-from claims — was extracting `egg` from `egg free pasta` / `peanut` from `peanut free bread` before derive ever ran.
3. Bare `gluten` added to gluten tokens (with negation for `gluten free …`).
4. **31** corpus goldens (`expected_verdict: UNCERTAIN`) for the requested phrase matrix.

## 3. DISCOVERED hygiene

| | |
|--|--|
| Dairy trio demotion cause | Asserted `dairy_source` false→true on `cultured buttermilk`, `flavoured milks`, `traditional buttermilk (churning)` (pollution-era asserted false). `dairy_source=true` is correct; demotion was spurious. |
| Dairy restore | KS → `AUTO_CLASSIFIED` via reconcile re-promote (ontology dump). |
| Phase-1 (~80) | Cleared `synthetic` via equal-tier asserted-false in reconcile + re-promote. turmeric/paprika/agar/guar/xanthan now `synthetic=false`, `AUTO_CLASSIFIED`. |
| Inject CLI | `bulk_inject` writes before/after DISCOVERED name diff; fails live runs on unexplained additions (`--allow-discovered-additions`, `--discovered-diff`). |
| DISCOVERED after | **9**: ascorbic acid, caviar, citric acid, cuttlefish, mono and diglycerides, oat, parsnip, pepsin, rennet |

Artifacts: `docs/item37_fish_negation_discovered_ops.json`, `docs/item37_ifct_inject_discovered_diff.json`, `docs/item37_phase1_restore_discovered_diff.json`, `docs/item37_ortho_allergy_safe_side_review.json`.
