# Item 42 — The 26 USDA SAFE rows (not false-SAFEs)

**Verdict table rows:** USDA allergen-true + `*_inferred` that resolve **SAFE** under the matching restriction — dairy 15, egg 6, shellfish 5.

## Finding

Every one of the 26 answers at **`L2_local_ontology`** with **`flag_on_ci=false`**. The live USDA row carries a **false-positive** allergen bit; L2 does not; the matching restriction correctly clears.

| Live flag (wrong) | Names | Why live true | Why SAFE is correct |
|-------------------|-------|---------------|---------------------|
| `dairy_source` (15) | egg duck/goose/quail/turkey…, egg white/yolk/whole… | USDA category “Dairy and Egg Products” bleeds dairy onto eggs | Eggs are not dairy; L2 has no `dairy_source` |
| `egg_source` (6) | butter, cheeses, milks, whipped topping | Same category bleed (egg onto dairy) | Dairy is not egg; L2 has no `egg_source` |
| `shellfish_source` (5) | emu/ostrich oyster, oyster mushroom, salsify (vegetable oyster), squash scallop | Name token `oyster` / `scallop` without plant override | Not shellfish; L2 has no `shellfish_source` |

**Same-day:** none. These are not missing hazards on the production path — they are L2 correctly refusing live false positives. The live USDA false positives remain a transform/precision debt (Item 42 kind-split + category evidence), not an ontology patch list.

Artifact: `docs/item42_safe_inferred_26.json`.
