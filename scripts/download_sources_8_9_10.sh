#!/usr/bin/env bash
# Tier 3 India sources: FSSAI (Source 8), NIN (Source 9), IFCT 2017 (Source 10).
# Run from repo root: ./scripts/download_sources_8_9_10.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IFCT="$ROOT/data/raw/ifct2017"
mkdir -p "$IFCT" "$ROOT/data/raw/fssai"

echo "==> IFCT 2017 compositions CSV (NIN/ICMR — open mirror)"
curl -L --fail --retry 3 -o "$IFCT/index.csv" \
  "https://unpkg.com/@ifct2017/compositions@1.0.0/index.csv"

echo "==> FSSAI Appendix A PDF (permitted additives)"
curl -L --fail --retry 3 -o "$ROOT/data/raw/fssai/appendix_a.pdf" \
  "https://fssai.gov.in/upload/uploadfiles/files/Appendix%20A(2).pdf"
python3 "$ROOT/backend/scripts/extract_fssai_additives.py"

echo "==> Transform all Tier 3 sources"
python3 "$ROOT/backend/scripts/transform_fssai_bulk.py"
python3 "$ROOT/backend/scripts/transform_nin_bulk.py"
python3 "$ROOT/backend/scripts/transform_ifct_bulk.py"

echo "Done."
ls -lh "$IFCT/index.csv" "$ROOT/data/layer1_fssai.json" "$ROOT/data/layer1_nin.json" "$ROOT/data/layer1_ifct.json" 2>/dev/null || true
