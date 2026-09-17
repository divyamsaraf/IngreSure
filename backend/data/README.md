# Backend data directory

Manual bulk downloads live here. Staging outputs and the merged ontology stay under repo-root `data/`.

## Manual downloads (~1–2 hours)

### OFF taxonomy (~20 MB)

```bash
curl -L "https://static.openfoodfacts.org/data/taxonomies/ingredients.json" \
  -o backend/data/off_ingredients_taxonomy.json
```

### USDA FoodData Central (~200 MB total)

1. Go to [fdc.nal.usda.gov/download-datasets.html](https://fdc.nal.usda.gov/download-datasets.html)
2. Download **Foundation Foods** JSON (latest date)
3. Download **SR Legacy** JSON
4. Unzip/rename to:
   - `backend/data/usda_foundation_foods.json`
   - `backend/data/usda_sr_legacy_foods.json`

Legacy fallback (from `./scripts/download_tier1_data.sh`):

- `data/raw/foundationDownload.json`
- `data/raw/FoodData_Central_sr_legacy_food_json_2021-10-28.json`

### ChEBI (optional — chemical names)

1. Go to [ChEBI FTP flat files](https://ftp.ebi.ac.uk/pub/databases/chebi/Flat_file_tab_delimited/)
2. Download `names.tsv.gz` and `compounds.tsv.gz`
3. Unzip to:
   - `backend/data/chebi_names.tsv`
   - `backend/data/chebi_compounds.tsv`

Then run the existing ChEBI transform: `python backend/scripts/transform_chebi_bulk.py`

### Already in repo

- `backend/data/india_ingredients_catalog.json` — manually curated India-specific ingredients

## Execution order

Run from **repo root**:

```bash
# 1. Parse all sources into staging files
python backend/scripts/parse_off_taxonomy.py
python backend/scripts/parse_usda_bulk.py
python backend/scripts/fetch_wikidata_ingredients.py   # ~2–10 min (SPARQL + rate limits)

# 2. India catalog — already present at backend/data/india_ingredients_catalog.json

# 3. Merge everything into ontology
python backend/scripts/merge_all_sources.py
# Preview without writing:
python backend/scripts/merge_all_sources.py --dry-run

# 4. Review the merge report
cat data/merge_report.json

# 5. Verify ontology count and spot-check India entries
python -c "
import json
with open('data/ontology.json') as f:
    data = json.load(f)
print(f'Total ingredients: {len(data[\"ingredients\"])}')
names = [i['canonical_name'] for i in data['ingredients']]
for check in ['asafoetida', 'paneer', 'jaggery', 'besan', 'toor dal']:
    print(f'{check}: {check in names}')
"

# 6. Incremental seed to Supabase (dry run first)
cd backend && python seed_ingredient_knowledge.py --incremental --dry-run

# 7. If dry run looks good, seed for real
cd backend && python seed_ingredient_knowledge.py --incremental
```

## Output paths

| Step | Output |
|------|--------|
| OFF parse | `data/off_staging.json` |
| USDA parse | `data/usda_staging.json` |
| Wikidata fetch | `data/wikidata_staging.json` |
| Merge | `data/ontology.json` (+ `data/ontology.json.bak`, `data/merge_report.json`) |

## Merge priority (high → low)

1. `data/ontology.json` — existing entries; **VERIFIED** / **LOCKED** never modified
2. `data/e_number_catalog.json` — skip if already present
3. `backend/data/india_ingredients_catalog.json`
4. `data/off_staging.json`
5. `data/usda_staging.json`
6. `data/wikidata_staging.json`
