#!/usr/bin/env bash
# Download Sources 5–6: FDA GRAS (SCOGS + GRAS Notices) and FoodEx2 bulk CSV.
# Run from repo root: ./scripts/download_sources_5_6.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW="$ROOT/data/raw"
FDA="$RAW/fda"
FOODEX="$RAW/foodex2"
mkdir -p "$FDA" "$FOODEX"

FDA_BASE="https://www.hfpappexternal.fda.gov/scripts/fdcc"

echo "==> FDA SCOGS database (public domain)"
curl -L --fail --retry 3 -o "$FDA/scogs.xls" \
  "$FDA_BASE/cfc/XMLService.cfm?method=downloadxls&set=SCOGS"

echo "==> FDA GRAS Notices (public domain)"
curl -L --fail --retry 3 -o "$FDA/gras_notices.xls" \
  "$FDA_BASE/cfc/XMLService.cfm?method=downloadxls&set=GRASNotices"

echo "==> FoodEx2 ontology CSV (EFSA / UK FSA via AgroPortal)"
curl -L --fail --retry 3 -o "$FOODEX/foodex2.csv.gz" \
  "https://agroportal.eu/ontologies/FOODEX2/download?format=csv"
gunzip -kf "$FOODEX/foodex2.csv.gz"

echo "Done."
ls -lh "$FDA"/*.xls "$FOODEX"/foodex2.csv
