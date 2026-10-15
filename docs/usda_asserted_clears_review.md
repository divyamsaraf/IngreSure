# USDA reviewed asserted clears — hand skim

Frozen file: [`../data/usda_reviewed_asserted_clears.json`](../data/usda_reviewed_asserted_clears.json)
(`frozen: true`, 232 `(name, flag)` rows + 13 shellfish false friends).

Readable dump: [`usda_asserted_clears_review.tsv`](usda_asserted_clears_review.tsv).

## Hand skim (2026-10-14, full TSV)

Read all 232 lines. Shape:

| Clear flag | Count | Verdict |
|------------|------:|---------|
| `egg_source` on dairy-named rows (butter/cheese/cream/milk/yogurt/kefir/whipped topping) | ~182 | Keep — category-bleed sticky OR |
| `dairy_source` on egg-named rows | ~27 | Keep — reverse bleed |
| `shellfish_source` / `animal_origin` on oyster-mushroom / salsify / scallop-squash / emu-ostrich “oyster” | ~13 + animal clears | Keep — false friends |
| `custard apple…` × dairy/egg/animal | 3 | Keep — fruit vs dessert custard |

No processed-form sauce/extract/paste clears. No `egg_source` clear whose name still matches `\begg\b`. No `dairy_source` clear that still hits the dairy positive lexicon. Ice-cream sandwich/sundae egg clears are sticky-OR only (no egg token in the name); acceptable under name-lexicon policy.

CI: `tests/ike2/test_usda_asserted_clears_frozen.py` — dump clears ⊆ frozen list.
