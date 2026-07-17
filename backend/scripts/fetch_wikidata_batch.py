#!/usr/bin/env python3
"""
Fetch Wikidata food additives / ingredients via SPARQL (batch, no per-item API calls).

Saves raw SPARQL JSON to data/raw/:
  - wikidata_e_number_additives.json
  - wikidata_food_ingredients.json

Run from repo root:
  python backend/scripts/fetch_wikidata_batch.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
sys.path.insert(0, str(_backend))

from core.external_apis.wikidata_sparql import (
    WIKIDATA_HEADERS,
    WIKIDATA_SPARQL_URL,
    QUERY_E_NUMBER_ADDITIVES,
    QUERY_FOOD_INGREDIENTS,
)

_RAW = _repo / "data" / "raw"
_DEFAULT_E_OUT = _RAW / "wikidata_e_number_additives.json"
_DEFAULT_FOOD_OUT = _RAW / "wikidata_food_ingredients.json"


def run_sparql(query: str, *, timeout: int = 120) -> dict:
    """Execute SPARQL and return parsed JSON results."""
    resp = requests.get(
        WIKIDATA_SPARQL_URL,
        params={"query": query},
        headers={**WIKIDATA_HEADERS, "Accept": "application/sparql-results+json"},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict) or "results" not in data:
        raise ValueError("Unexpected SPARQL response shape")
    return data


def _binding_count(data: dict) -> int:
    return len((data.get("results") or {}).get("bindings") or [])


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-fetch Wikidata ingredient SPARQL results")
    parser.add_argument("--e-out", type=Path, default=_DEFAULT_E_OUT)
    parser.add_argument("--food-out", type=Path, default=_DEFAULT_FOOD_OUT)
    parser.add_argument("--skip-e-numbers", action="store_true")
    parser.add_argument("--skip-food", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    args.e_out.parent.mkdir(parents=True, exist_ok=True)

    if not args.skip_e_numbers:
        print("Fetching E-number additives (P628)...")
        t0 = time.time()
        e_data = run_sparql(QUERY_E_NUMBER_ADDITIVES, timeout=args.timeout)
        with args.e_out.open("w", encoding="utf-8") as f:
            json.dump(e_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  Wrote {_binding_count(e_data)} rows to {args.e_out} ({time.time()-t0:.1f}s)")

    if not args.skip_food:
        print("Fetching food ingredients (Q25403900 + E-numbers)...")
        t0 = time.time()
        food_data = run_sparql(QUERY_FOOD_INGREDIENTS, timeout=args.timeout)
        with args.food_out.open("w", encoding="utf-8") as f:
            json.dump(food_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  Wrote {_binding_count(food_data)} rows to {args.food_out} ({time.time()-t0:.1f}s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
