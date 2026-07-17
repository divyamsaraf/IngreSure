#!/usr/bin/env python3
"""
Batch-fetch PubChem food-related compounds via PUG REST.

Saves raw JSON to data/raw/pubchem/:
  - food_additive_cids.json      (CID discovery by word search + optional CAS)
  - compound_properties.json     (IUPACName, MolecularFormula, SMILES)
  - compound_synonyms.json       (synonyms per CID)

Run from repo root:
  python backend/scripts/fetch_pubchem_batch.py
  python backend/scripts/fetch_pubchem_batch.py --cas-limit 5000
  python backend/scripts/fetch_pubchem_batch.py --skip-cas --max-cids 3000
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
sys.path.insert(0, str(_backend))

from core.external_apis.pubchem_batch import (
    BATCH_PROPERTY_SIZE,
    BATCH_SYNONYM_SIZE,
    collect_cas_from_layer1,
    fetch_properties_batch,
    fetch_synonyms_batch,
    cids_from_cas_list,
    search_food_additive_cids,
    search_cids_by_name_word,
    PRIMARY_FOOD_QUERY,
)

_RAW = _repo / "data" / "raw" / "pubchem"
_CIDS_OUT = _RAW / "food_additive_cids.json"
_PROPS_OUT = _RAW / "compound_properties.json"
_SYNS_OUT = _RAW / "compound_synonyms.json"

_LAYER1_CAS_SOURCES = [
    _repo / "data" / "layer1_wikidata.json",
    _repo / "data" / "layer1_fda_gras.json",
    _repo / "data" / "layer1_chebi.json",
    _repo / "data" / "layer1_off_taxonomy.json",
    _repo / "data" / "layer1_usda_fdc.json",
]


def discover_cids(
    *,
    cas_limit: int,
    skip_cas: bool,
    max_cids: int | None,
) -> tuple[dict[str, Any], list[int]]:
    """Return metadata dict and deduplicated CID list."""
    word_results: dict[str, list[int]] = {}
    primary = search_cids_by_name_word(PRIMARY_FOOD_QUERY)
    if primary:
        word_results[PRIMARY_FOOD_QUERY] = primary
    word_results.update(search_food_additive_cids())

    cas_to_cid: dict[str, int] = {}
    if not skip_cas and cas_limit > 0:
        cas_numbers = collect_cas_from_layer1(_LAYER1_CAS_SOURCES, limit=cas_limit)
        print(f"Resolving {len(cas_numbers)} CAS numbers from Layer 1 sources...")
        t0 = time.time()
        cas_to_cid = cids_from_cas_list(cas_numbers)
        print(f"  Resolved {len(cas_to_cid)} CIDs from CAS ({time.time()-t0:.1f}s)")

    all_cids: list[int] = []
    seen: set[int] = set()
    for cids in word_results.values():
        for cid in cids:
            if cid not in seen:
                seen.add(cid)
                all_cids.append(cid)
    for cid in cas_to_cid.values():
        if cid not in seen:
            seen.add(cid)
            all_cids.append(cid)

    if max_cids is not None and len(all_cids) > max_cids:
        all_cids = all_cids[:max_cids]

    meta = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "primary_query": PRIMARY_FOOD_QUERY,
        "primary_query_cids": len(primary),
        "word_search_queries": len(word_results),
        "word_search_cids": sum(len(v) for v in word_results.values()),
        "cas_resolved": len(cas_to_cid),
        "unique_cids": len(all_cids),
        "word_results": {k: v for k, v in word_results.items()},
        "cas_to_cid": {k: v for k, v in cas_to_cid.items()},
    }
    return meta, all_cids


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-fetch PubChem food compound data")
    parser.add_argument("--cids-out", type=Path, default=_CIDS_OUT)
    parser.add_argument("--props-out", type=Path, default=_PROPS_OUT)
    parser.add_argument("--syns-out", type=Path, default=_SYNS_OUT)
    parser.add_argument("--cas-limit", type=int, default=8000,
                        help="Max CAS numbers to resolve from Layer 1 (0=skip)")
    parser.add_argument("--skip-cas", action="store_true", help="Skip CAS resolution from Layer 1")
    parser.add_argument("--max-cids", type=int, default=None, help="Cap total unique CIDs fetched")
    parser.add_argument("--skip-properties", action="store_true")
    parser.add_argument("--skip-synonyms", action="store_true")
    args = parser.parse_args()

    args.cids_out.parent.mkdir(parents=True, exist_ok=True)

    print("Discovering PubChem CIDs (word search + optional CAS)...")
    t0 = time.time()
    meta, cids = discover_cids(
        cas_limit=0 if args.skip_cas else args.cas_limit,
        skip_cas=args.skip_cas,
        max_cids=args.max_cids,
    )
    print(f"  Found {len(cids)} unique CIDs ({time.time()-t0:.1f}s)")
    if meta["primary_query_cids"] == 0:
        print("  Note: primary 'food additive' word search returned no CIDs; using curated terms + CAS.")

    with args.cids_out.open("w", encoding="utf-8") as f:
        json.dump({"meta": meta, "cids": cids}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  Wrote {args.cids_out}")

    if not cids:
        print("No CIDs to fetch.", file=sys.stderr)
        return 1

    if not args.skip_properties:
        print(f"Fetching properties (batch size {BATCH_PROPERTY_SIZE})...")
        t0 = time.time()
        props = fetch_properties_batch(cids)
        with args.props_out.open("w", encoding="utf-8") as f:
            json.dump({"meta": {"count": len(props)}, "properties": props}, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  Wrote {len(props)} property rows to {args.props_out} ({time.time()-t0:.1f}s)")

    if not args.skip_synonyms:
        print(f"Fetching synonyms (batch size {BATCH_SYNONYM_SIZE})...")
        t0 = time.time()
        syns = fetch_synonyms_batch(cids)
        with args.syns_out.open("w", encoding="utf-8") as f:
            json.dump({"meta": {"count": len(syns)}, "synonyms": {str(k): v for k, v in syns.items()}}, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  Wrote {len(syns)} synonym records to {args.syns_out} ({time.time()-t0:.1f}s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
