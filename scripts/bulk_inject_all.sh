#!/usr/bin/env bash
# Dry-run (default) or apply all in-repo Layer-1 dumps via IKE-2 bulk_inject.
# Usage (from repo root):
#   ./scripts/bulk_inject_all.sh            # dry-run
#   ./scripts/bulk_inject_all.sh --apply    # write to Supabase
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
DATA="$ROOT/data"
MODE="--dry-run"
if [[ "${1:-}" == "--apply" ]]; then
  MODE=""
  echo "WARNING: applying bulk_inject to live DB" >&2
fi

# dump basename -> CLI --source label (must match sources.canonical_source keys)
declare -a PAIRS=(
  "layer1_chebi.json:chebi"
  "layer1_usda_fdc.json:usda_fdc"
  "layer1_fda_gras.json:fda_gras"
  "layer1_fssai.json:fssai"
  "layer1_wikidata.json:wikidata"
  "layer1_off_taxonomy.json:open_food_facts"
  "layer1_nin.json:nin"
  "layer1_ifct.json:ifct"
  "layer1_foodex2.json:foodex2"
  "layer1_pubchem.json:pubchem"
  "layer1_e_numbers.json:e_number_catalog"
  "layer1_produce_catalog.json:produce_catalog"
  "layer1_animal_catalog.json:animal_catalog"
)

cd "$BACKEND"
failed=0
for pair in "${PAIRS[@]}"; do
  dump="${pair%%:*}"
  src="${pair##*:}"
  path="$DATA/$dump"
  if [[ ! -f "$path" ]]; then
    echo "SKIP missing $dump"
    continue
  fi
  echo "=== $dump --source $src $MODE ==="
  # shellcheck disable=SC2086
  if ! python -m core.knowledge.ike2.etl.bulk_inject "$path" --source "$src" $MODE; then
    echo "FAIL $dump" >&2
    failed=$((failed + 1))
  fi
done
exit "$failed"
