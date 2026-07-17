#!/usr/bin/env bash
# Source 7: PubChem batch fetch (no API key; rate-limited to 5 req/s).
# Run from repo root: ./scripts/download_sources_7.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> PubChem PUG REST batch (food additives + Layer 1 CAS)"
python3 "$ROOT/backend/scripts/fetch_pubchem_batch.py" "$@"

echo "==> Transform to Layer 1"
python3 "$ROOT/backend/scripts/transform_pubchem_batch.py"

echo "Done."
ls -lh "$ROOT/data/layer1_pubchem.json" "$ROOT/data/raw/pubchem/" 2>/dev/null || true
