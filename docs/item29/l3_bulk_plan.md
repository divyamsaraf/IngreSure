# Item 29 — L3 bulk plan

Bulk groups **add hazard detection**. They never clear an existing true flag (IKE-2 reconcile is most-restrictive OR). They are not a clearance path and must not be treated as one.

Do not run this plan against production from Track F.

---

## Sources in this tree

Committed `data/layer1_*.json` dumps (not examples / one-off patches):

| Order after ontology seed | Dump | CLI `--source` | Canonical | Tier | Default state | Count |
|---------------------------|------|----------------|-----------|------|---------------|------:|
| 1 | `layer1_foodex2.json` | `foodex2` | `foodex2` | 2 | DISCOVERED | 1,258 |
| 2 | `layer1_animal_catalog.json` | `animal_catalog` | `animal_catalog` | 2 | DISCOVERED | 7 |
| 3 | `layer1_pubchem.json` | `pubchem` | `pubchem` | 2 | DISCOVERED | 296 |
| 4 | `layer1_wikidata.json` | `wikidata` | `wikidata` | 2 | DISCOVERED | 3,041 |
| 5 | `layer1_nin.json` | `nin` | `nin` | 3 | AUTO_CLASSIFIED | 82 |
| 6 | `layer1_ifct.json` | `ifct` | `ifct` | 3 | AUTO_CLASSIFIED | 540 |
| 7 | `layer1_usda_fdc.json` | `usda_fdc` | `usda` | 3 | AUTO_CLASSIFIED | 3,613 |
| 8 | `layer1_infoods_anfood.json` | `infoods_anfood` | `infoods` | 3 | AUTO_CLASSIFIED | 621 |
| 9 | `layer1_chebi.json` | `chebi` | `chebi` | 3 | DISCOVERED | 18,010 |
| 10 | `layer1_produce_catalog.json` | `produce_catalog` | `produce_catalog` | 3 | AUTO_CLASSIFIED | 8 |
| 11 | `layer1_fda_gras.json` | `fda_gras` | `fda` | 4 | AUTO_CLASSIFIED | 1,414 |
| 12 | `layer1_fssai.json` | `fssai` | `fssai` | 4 | AUTO_CLASSIFIED | 913 |
| 13 | `layer1_e_numbers.json` | `e_number_catalog` | `e_number_catalog` | 4 | LOCKED | 330 |
| — | `layer1_off_taxonomy.json` | `open_food_facts` | `openfoodfacts` | 1 | DISCOVERED | 5,054 |

`open_food_facts` is listed last among crowd sources on purpose: skip it for a first production L3 pass (lowest trust, largest DISCOVERED flood). ChEBI is optional and large; same advice.

**First production L3 slice (this report’s dry-run set):** FoodEx2 → NIN → FDA GRAS.

Ontology seed is **before** this table (`python scripts/seed_ike2_ontology.py`). Ontology is tier 4 / AUTO_CLASSIFIED.

---

## Why this order

Reconcile (`backend/core/knowledge/ike2/etl/reconcile.py`):

- New groups: the first insert owns `source` and `knowledge_state`.
- Existing groups: boolean hazards OR together. A later source cannot turn a true into false unless it is equal-or-higher tier **and** ships that flag in `asserted_flags`.
- `VERIFIED` / `LOCKED` rows ignore lower-tier overwrites.

Low-tier first, then higher-tier, then LOCKED catalog: later sources can **add** hazards on collisions; they cannot silently clear. FoodEx2 lands DISCOVERED (cannot drive firm SAFE). NIN/FDA land AUTO_CLASSIFIED. That is detection, not clearance.

---

## Replay proof (per source)

Proof is local and in-memory. No injection.

1. **Count-check** the committed dump against the expected count.
2. **Adapter replay** when inputs exist (transform in memory, do not overwrite `data/layer1_*.json` unless an operator asks).
3. **Inject dry-run twice** on `_CollectWriter`:
   - first pass: inserts + updates vs the seed
   - second pass: `inserted == 0` (idempotent upsert keys: group `canonical_name`, ingredient `(group, normalized_name)`, alias `(normalized_alias, ingredient, region)`)
4. **Hazard invariant:** no seed-true flag becomes false after the pass.

Commands:

```bash
cd backend
# count + ontology-seeded + live-seeded in-memory replays (this track)
python scripts/item29_dry_run_l3_sources.py

# equivalent one-source CLI (still --dry-run; still no DB write)
python -m core.knowledge.ike2.etl.bulk_inject \
  ../data/layer1_fda_gras.json --source fda_gras --dry-run
python -m core.knowledge.ike2.etl.bulk_inject \
  ../data/layer1_nin.json --source nin --dry-run
python -m core.knowledge.ike2.etl.bulk_inject \
  ../data/layer1_foodex2.json --source foodex2 --dry-run
```

Adapter rebuild (operator, local files only):

```bash
# raw downloads are gitignored under data/raw/
./scripts/download_sources_5_6.sh
python backend/scripts/transform_fda_gras_bulk.py   # expect 1,414
python backend/scripts/transform_nin_bulk.py        # expect 82
python backend/scripts/transform_foodex2_bulk.py    # expect 1,258
```

---

## Expected counts (first slice)

| Source | Expected groups | This tree |
|--------|----------------:|----------:|
| FDA GRAS | 1,414 | 1,414 (`data/layer1_fda_gras.json`) |
| NIN | 82 | 82 (`data/layer1_nin.json`; transform input `data/nin_indian_ingredients.json` also 82) |
| FoodEx2 | 1,258 | 1,258 (`data/layer1_foodex2.json`) |

See `docs/item29/reports/l3_dry_run.json` for insert/update/reject splits vs ontology seed and vs a live-shaped seed.

---

## Rollback note

Bulk is additive OR-merge. There is **no safe “un-inject this source”**. Rolling back L3 means restoring a snapshot of `ike2_ingredient_groups` / `ike2_ingredients` / `ike2_aliases` taken **before** the bulk. Do not `DELETE WHERE source = …` — colliding rows may have OR’d flags from the bulk into an ontology group.

Migrations are forward-only. If `20261014000000` (or any pending file) mis-renders the view, restore the pre-`db push` snapshot; do not auto-down.

Suggested operator sequence on **staging** (not this track):

1. Snapshot `ike2_*` (and confirm restriction_rules = 52).
2. Apply pending migrations through `20261014000000`.
3. Ontology seed.
4. Same-seed reference (see `same_seed_reference.md`).
5. Optional first-slice bulk in the order above, one source per snapshot.
6. If a source mis-flags: restore that snapshot. Do not ship a “clearance” patch as a bulk dump.
