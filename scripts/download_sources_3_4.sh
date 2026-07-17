#!/usr/bin/env bash
# Download Tier 1 bulk sources (OFF, USDA) + Sources 3–4 (Wikidata via Python, ChEBI TSV).
# Run from repo root: ./scripts/download_sources_3_4.sh
# For full Tier 1 including OFF/USDA: ./scripts/download_tier1_data.sh first (or use download_all_sources.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW="$ROOT/data/raw"
CHEBI="$RAW/chebi"
mkdir -p "$CHEBI"

CHEBI_BASE="https://ftp.ebi.ac.uk/pub/databases/chebi/flat_files"

echo "==> ChEBI flat files (CC BY 4.0)"
for f in compounds.tsv.gz names.tsv.gz database_accession.tsv.gz chemical_data.tsv.gz reference.tsv.gz relation.tsv.gz; do
  echo "    $f"
  curl -L --fail --retry 3 -o "$CHEBI/$f" "$CHEBI_BASE/$f"
  gunzip -kf "$CHEBI/$f"
done

echo "==> Wikidata SPARQL batch (CC0)"
python3 "$ROOT/backend/scripts/fetch_wikidata_batch.py"

echo "Done."
ls -lh "$CHEBI"/*.tsv 2>/dev/null | head -10
ls -lh "$RAW"/wikidata_*.json 2>/dev/null || true
