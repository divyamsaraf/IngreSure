# Item 37 follow-up (suite / lactates / pollution / IFCT / ortho) — 2026-10-08

## 1. Full suite + L5 hazard flip audit

| | Count |
|--|------:|
| Batch 3 cited baseline (Item 7) | **1892 passed, 4 skipped, 0 failed** |
| This run (after this follow-up) | **2833 passed, 4 skipped, 0 failed** |

Suite grew substantially since Batch 3 (new Item 11 / stem / ortho / tripwire tests). Delta is not a regression count against the same file set.

### Corpus / fixture labels whose L5 path can now Avoid

Seam change: unresolved (L5) atoms with **label-derived** hazard flags are trusted enough for Avoid (Item 34 spirit). Diff of golden JSONL labels that resolve L5 and become **NOT_SAFE** under a matching restriction:

| Label | Restriction | Hazard | Real? |
|-------|-------------|--------|-------|
| apples dried sulphured uncooked | sulfite_sensitive | sulphite | yes |
| dried sulfured fruit / sulfured | sulfite_sensitive | sulphite | yes |
| May contain: peanuts (+ variants) | peanut_allergy | peanut | yes (fail-closed on may-contain medical) |
| soy tempeh / soy miso / soy natto | soy_allergy | soy (+fungal) | yes |
| wheat koji | gluten_free | gluten | yes |
| egg noodles | vegan | egg/animal | yes |
| barley malt | gluten_free | gluten | yes |

No plant-milk / sulfate / eggplant false friends in that set. Full list written during the run (13 labels).

---

## 2. Lactates / nisin / lactic acid — WARN, not Avoid

Catalog (`e_number_catalog.json`): **E234, E270, E325, E326, E327**
- `verdict_cap: WARN`
- `uncertainty_flags` includes `source_may_be_dairy_or_fermentation_derived`
- tier **B** (was A for salts/nisin)

Regenerated `truth_anchor_e_numbers.json` + `layer1_e_numbers.json`.

Dairy_free external verdict: **UNCERTAIN** (WARN maps to UNCERTAIN in `to_external`) — never firm SAFE. Never-SAFE goldens added for nisin/E234/lactic acid/E270/sodium lactate/E325/potassium lactate/calcium lactate/E327.

---

## 3. Live asserted_flags strip + DISCOVERED + call-site lock

| | Count |
|--|------:|
| Rows with >3 false-valued asserted names (before) | **2102** |
| Stripped to true-only | **2102** (+ 8 leftovers cleaned) |
| Polluted after | **0** |

Deliberate triage negatives: none needed re-keep on those rows (ontology deliberate falses already true-only or name-normalized away).

**Fruit heads:** ontology `apples`/`apricots`/`peaches`/`pears` have `sulphite_source=false` and not asserted. Live groups are `apple`/`apricot` (singular) with `sulphite_source=false`.

**DISCOVERED vs “89 baseline”**
- INFOODS closeout reported DISCOVERED=89; that figure is **not a clean baseline** — ~80 are Phase-1 FSSAI `synthetic` demotions later shown spurious for usefulness.
- After hyphen-normalization restore of stem-triage residues: measured **91**.
- Current: **94** (80 synthetic-pattern + 14 nonsynthetic).
- Exact two names for the +2 at the 91 checkpoint are not recoverable without a saved 89 snapshot. Nonsynthetic DISCOVERED now includes: caviar, cultured buttermilk, cuttlefish, dulce de leche, flavoured milks, ghee, honey, oat, parsnip, pepsin, potato flour, potato pancakes, rennet, traditional buttermilk (churning).

**`curated_asserted_negatives=True`**
- Sole setter: `mark_curated_asserted_negatives()` in `validate.py`.
- Sole production caller: `bulk_inject --curated-asserted-negatives`.
- Locked by AST test in `test_asserted_false_pollution_guard.py`.

Also: adapt treats near-full boolean blocks as **true-only**; produce/infoods adapters no longer emit false animalish keys.

---

## 4. IFCT fish_source

**Historically: no.** `_infer_flags` set `animal_origin` from the fish group but never `fish_source`. Live `source=ifct` groups with `fish_source=true`: **0** / 324.

**Fixed** in `transform_ifct_bulk.py`: fish / shellfish from IFCT “Fish and shellfish” group + `*fish` name compounds; shellfish name tokens win for prawns/etc.

Of the **44** human-review vernaculars:
- **0** had a live `source=ifct` row of the same name (all were `source=ontology`).
- **43/44** exist in `layer1_ifct.json`.
- **27** matched group inference → flipped with `matched_ifct:…` evidence.
- **16** more matched English `*fish`/trevally/catfish aliases → flipped with `matched_ifct_alias:…`.
- **1** left: **collagen** (not fish; stays human-review / ambiguous).

---

## 5. Orthographic list renamed + allergy SAFE-side review

Renamed to `orthographic_safe_uncertain_baseline.json` (grandfathered ratchet, **not** a written review).

Allergy/medical SAFE↔UNCERTAIN pairs reviewed on the SAFE side:
- **0** FALSE-SAFE under `sulfite_sensitive` for sulfite-family spellings.
- Coverage gaps (OK): aluminium/aluminum, colour/color, sulfate vs sulph-spelling misses, acesulfame sulph-misspellings.
- **1 written REVIEW** remaining of note: `dietary fibre` SAFE vs `dietary fiber` UNCERTAIN under `gluten_free` — confirm identity (oat/bran vs grain). See `docs/item37_ortho_allergy_safe_side_review.json`.
