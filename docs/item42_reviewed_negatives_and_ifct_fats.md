# Reviewed-negatives registry + IFCT animal fats

## Registry

`data/ike2_reviewed_negatives.json` (~291 pairs) merges:

- `usda_reviewed_asserted_clears.json` (clears + shellfish false friends)
- `lexicon_scan_false_friends.json`
- deliberate asserted falses from `layer1_stem_triage_2026-10-07.json`

**Invariant (writer = audit):** an asserted false is legal only if
`(normalize(canonical_name), flag)` is on that registry. Validate runs on
incoming rows **and** on the **merged** row after reconcile. `>3` remains a
backstop (`asserted_flags_false_pollution`); curated escape relaxes count only.

## Ghee / IFCT fats

| Check | Result |
|-------|--------|
| Live `ghee` (`source=ontology`) | `plant_origin=False`, `animal_origin=True`, `dairy_source=True`; asserted `['animal_origin','dairy_source']` — cleared |
| IFCT dump `Ghee` | Was `plant_origin=True` with no animal/dairy — **fixed** in `data/layer1_ifct.json` |
| IFCT dump butter / lard / tallow / fish oil | **No such rows** in the dump |
| IFCT `Vanaspati` | `plant_origin=True` — correct (hydrogenated vegetable fat) |
| Live `source=ifct` plant+animal | **0** rows |

Re-inject IFCT when convenient so remote/local dumps stay aligned; live ontology ghee already correct.
