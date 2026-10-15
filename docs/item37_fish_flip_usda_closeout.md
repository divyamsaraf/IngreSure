# Item 37 — verdict exposure, flips, USDA-at-source (closeout)

## 1. Verdict-level exposure (report first, land-meat filtered)

Union of **63** INFOODS matches + **8** ontology fish/seafood + **148** USDA lexicon = **219** names.

FINDING rule applied only after excluding land-meat/poultry (incl. emu/ostrich *oyster* cuts).

### Before flips

| Restriction | n (non-land-meat) | SAFE | UNCERTAIN | NOT_SAFE | FINDING (SAFE) |
|-------------|------------------:|-----:|----------:|---------:|---------------:|
| fish_allergy | 219* | 10 | 129 | 80 | **10** (8 ontology seafood + emu/ostrich oyster†) |
| shellfish_allergy | 219* | 78 | 129 | 12 | 6 seafood-named SAFEs |

\*First pass had not yet excluded emu/ostrich oyster; †those are land-meat cuts.

The 10 fish SAFEs were the actionable exposure. Most USDA lexicon rows were already UNCERTAIN/NOT_SAFE via name derive or prior flags; the ontology 8 were firm false-SAFE under L2.

### After flips + USDA reinject

| Restriction | n (non-land-meat) | SAFE | UNCERTAIN | NOT_SAFE | FINDING |
|-------------|------------------:|-----:|----------:|---------:|--------:|
| fish_allergy | 216 | **0** | 128 | 88 | **0** |
| shellfish_allergy | 216 | 72‡ | 128 | 16 | **0** |

‡Fish rows correctly SAFE under shellfish (cross-species), not findings.

Full row table: `docs/item37_fish_verdict_exposure.json`.

## 2. Same-day flips (unambiguous)

- Replay: ontology-seeded and live-seeded **0 demotions**.
- Live inject: 71 updated (8 ontology + 63 matches), DISCOVERED diff empty.
- **L2 note:** live DB alone was not enough for the 8 ontology names — `resolve` hits `L2_local_ontology` first. Also patched `data/ontology.json` (fish; generic `seafood` → both kinds).
- Evidence sidecar: `docs/item37_fish_flip_evidence.json`.

Post-check: canned herring/mackerel/sardines/sprats → fish Avoid; canned/dried/salted/smoked seafood → both Avoid; `fish cod atlantic raw` → fish Avoid / shellfish SAFE; dungeness crab → both Avoid.

## 3. USDA at the source

- Layer-1 dump did **not** keep `foodCategory`; raw FDC JSON does (`Finfish and Shellfish Products`).
- Transform now derives `fish_source` / `shellfish_source` from category + name (true-only emit), via `_fish_shellfish_from_name_and_category`.
- Regenerated dump: **182** fish + **60** shellfish.
- Dry-runs 0 demotions; live inject 0 rejects / 0 demotions.
- No-kind bucket: **852 → 625**; USDA fish/shellfish-shaped remaining in no-kind: **0** (was 148 lexicon hits).

## 4. Housekeeping

**Synthetic restore 77 vs ~80:** Phase-1 listed **82** demotions; **77** were `synthetic false→true`. Restore touched those 77. The other **5** were non-synthetic and correctly untouched:

| Name | Trigger |
|------|---------|
| dulce de leche | usda:egg_source |
| potato pancakes | usda:root_vegetable |
| ghee | ifct:plant_origin |
| honey | usda:plant_origin |
| potato flour | usda:root_vegetable |

**`synthetic` comment** added on `Ingredient.synthetic` (`ingredient_schema.py`) and `BOOL_FLAGS` (`adapt.py`): FSSAI-inferred, unreliable, read by no rule.

## Artifacts

- `docs/item37_fish_flip_usda_ops.json`
- `docs/item37_fish_verdict_exposure.json`
- `docs/item37_fish_flip_evidence.json`
- `data/layer1_item37_fish_flip.json`
- `data/layer1_usda_fdc.json` (regenerated)
- `backend/scripts/item37_fish_flip_usda_ops.py`
