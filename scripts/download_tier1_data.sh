#!/usr/bin/env bash
# Download Tier 1 bulk ingredient datasets (free, no API key).
# Run from repo root: ./scripts/download_tier1_data.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW="$ROOT/data/raw"
mkdir -p "$RAW"

echo "==> OFF ingredients taxonomy"
curl -L --fail --retry 3 \
  -o "$RAW/off_ingredients_taxonomy.json" \
  "https://static.openfoodfacts.org/data/taxonomies/ingredients.json"

echo "==> USDA FDC Foundation Foods"
curl -L --fail --retry 3 \
  -o "$RAW/fdc_foundation.zip" \
  "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_foundation_food_json_2024-10-31.zip"

echo "==> USDA FDC SR Legacy"
curl -L --fail --retry 3 \
  -o "$RAW/fdc_sr_legacy.zip" \
  "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_json_2021-10-28.zip"

echo "==> Unzipping USDA archives"
unzip -o -q "$RAW/fdc_foundation.zip" -d "$RAW"
unzip -o -q "$RAW/fdc_sr_legacy.zip" -d "$RAW"

echo "Done. Raw files in data/raw/"
ls -lh "$RAW"/*.json "$RAW"/*.zip 2>/dev/null || true
