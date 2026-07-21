#!/usr/bin/env python3
"""
Fetch Wikidata food additives and ingredients → IngreSure staging JSON.

Queries the public Wikidata SPARQL endpoint for items not already present in
OFF or USDA staging files (when available).

Output: data/wikidata_staging.json

Run from repo root:
  python backend/scripts/fetch_wikidata_ingredients.py
  python backend/scripts/fetch_wikidata_ingredients.py --skip-fetch --additives data/raw/wikidata_e_number_additives.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
sys.path.insert(0, str(_backend))

from core.external_apis.wikidata_sparql import WIKIDATA_SPARQL_URL

_DEFAULT_OUTPUT = _repo / "data" / "wikidata_staging.json"
_DEFAULT_OFF_STAGING = _repo / "data" / "off_staging.json"
_DEFAULT_USDA_STAGING = _repo / "data" / "usda_staging.json"

WIKIDATA_HEADERS = {
    "User-Agent": "IngreSure-DB-Builder/1.0 (food safety app; divyam.saraf@gmail.com)",
    "Accept": "application/sparql-results+json",
}

QUERY_FOOD_ADDITIVES = """
SELECT DISTINCT ?item ?itemLabel ?eNumber ?casNumber ?inChI WHERE {
  ?item wdt:P31/wdt:P279* wd:Q189567 .
  OPTIONAL { ?item wdt:P628 ?eNumber . }
  OPTIONAL { ?item wdt:P231 ?casNumber . }
  OPTIONAL { ?item wdt:P234 ?inChI . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
ORDER BY ?eNumber
LIMIT 3000
""".strip()

QUERY_FOOD_INGREDIENTS = """
SELECT DISTINCT ?item ?itemLabel ?casNumber WHERE {
  {
    ?item wdt:P31/wdt:P279* wd:Q25403900 .
  } UNION {
    ?item wdt:P31/wdt:P279* wd:Q2736424 .
  } UNION {
    ?item wdt:P31/wdt:P279* wd:Q14565201 .
  }
  OPTIONAL { ?item wdt:P231 ?casNumber . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
}
LIMIT 5000
""".strip()

_QID_LABEL_RE = re.compile(r"^Q\d+$", re.I)
_E_NUMBER_RE = re.compile(r"^E?\s*(\d{3,4}[A-Za-z]?)$", re.I)


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unknown"


def _binding_value(binding: dict[str, Any], key: str) -> str | None:
    node = binding.get(key)
    if not isinstance(node, dict):
        return None
    value = node.get("value")
    return str(value).strip() if value else None


def _qid_from_uri(uri: str) -> str:
    if "/entity/" in uri:
        return uri.rsplit("/", 1)[-1]
    return uri


def _format_e_number(raw: str) -> str:
    s = raw.strip().upper().replace(" ", "")
    if not s.startswith("E"):
        s = f"E{s}"
    m = _E_NUMBER_RE.match(s)
    return m.group(0).upper().replace(" ", "") if m else s


def run_sparql(query: str, *, timeout: int = 180) -> dict[str, Any]:
    resp = requests.get(
        WIKIDATA_SPARQL_URL,
        params={"query": query},
        headers=WIKIDATA_HEADERS,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict) or "results" not in data:
        raise ValueError("Unexpected SPARQL response shape")
    return data


def _load_staging_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    names: set[str] = set()
    for ing in payload.get("ingredients") or []:
        if not isinstance(ing, dict):
            continue
        cn = (ing.get("canonical_name") or "").strip().lower()
        if cn:
            names.add(cn)
    return names


def _build_ingredient(
    *,
    label: str,
    qid: str,
    e_number: str | None,
    cas_number: str | None,
    inchi: str | None,
) -> dict[str, Any]:
    canonical = label.lower().strip()
    seen_aliases: set[str] = set()
    aliases: list[str] = []

    for alias in [label, e_number]:
        if not alias:
            continue
        alias = alias.strip()
        key = alias.lower()
        if key not in seen_aliases:
            aliases.append(alias)
            seen_aliases.add(key)

    return {
        "id": slugify(label),
        "canonical_name": canonical,
        "aliases": aliases,
        "animal_origin": False,
        "plant_origin": False,
        "synthetic": False,
        "fungal": False,
        "insect_derived": False,
        "egg_source": False,
        "dairy_source": False,
        "gluten_source": False,
        "soy_source": False,
        "sesame_source": False,
        "nut_source": None,
        "alcohol_content": None,
        "root_vegetable": False,
        "onion_source": False,
        "garlic_source": False,
        "fermented": False,
        "uncertainty_flags": ["requires_classification"],
        "derived_from": [],
        "contains": [],
        "may_contain": [],
        "regions": ["Global"],
        "_source": "wikidata",
        "_wikidata": qid,
        "_cas_number": cas_number,
        "_inchi": inchi,
        "_e_number": e_number,
    }


def _merge_ingredient(existing: dict[str, Any], incoming: dict[str, Any]) -> None:
    seen = {a.lower() for a in existing.get("aliases") or []}
    for alias in incoming.get("aliases") or []:
        if alias.lower() not in seen:
            existing.setdefault("aliases", []).append(alias)
            seen.add(alias.lower())

    for field in ("_cas_number", "_inchi", "_e_number"):
        if existing.get(field) is None and incoming.get(field) is not None:
            existing[field] = incoming[field]


def parse_bindings(
    bindings: list[dict[str, Any]],
    *,
    existing_names: set[str],
    stats: dict[str, int],
) -> dict[str, dict[str, Any]]:
    by_qid: dict[str, dict[str, Any]] = {}

    for binding in bindings:
        stats["rows_processed"] += 1
        item_uri = _binding_value(binding, "item")
        label = _binding_value(binding, "itemLabel")
        if not item_uri or not label:
            stats["skipped_missing_fields"] += 1
            continue

        if _QID_LABEL_RE.match(label):
            stats["skipped_qid_label"] += 1
            continue

        if len(label) < 3 or len(label) > 100:
            stats["skipped_name_length"] += 1
            continue

        canonical = label.lower().strip()
        if canonical in existing_names:
            stats["skipped_existing"] += 1
            continue

        qid = _qid_from_uri(item_uri)
        e_raw = _binding_value(binding, "eNumber")
        e_number = _format_e_number(e_raw) if e_raw else None
        cas_number = _binding_value(binding, "casNumber")
        inchi = _binding_value(binding, "inChI")

        ing = _build_ingredient(
            label=label,
            qid=qid,
            e_number=e_number,
            cas_number=cas_number,
            inchi=inchi,
        )

        if qid in by_qid:
            _merge_ingredient(by_qid[qid], ing)
        else:
            by_qid[qid] = ing
            stats["unique_wikidata"] += 1

    return by_qid


def fetch_and_parse(
    *,
    skip_fetch: bool,
    additives_path: Path | None,
    ingredients_path: Path | None,
    existing_names: set[str],
    timeout: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    stats: dict[str, int] = {
        "rows_processed": 0,
        "skipped_missing_fields": 0,
        "skipped_qid_label": 0,
        "skipped_name_length": 0,
        "skipped_existing": 0,
        "unique_wikidata": 0,
        "query1_rows": 0,
        "query2_rows": 0,
    }
    by_qid: dict[str, dict[str, Any]] = {}

    def ingest(data: dict[str, Any]) -> None:
        nonlocal by_qid
        bindings = (data.get("results") or {}).get("bindings") or []
        parsed = parse_bindings(bindings, existing_names=existing_names, stats=stats)
        for qid, ing in parsed.items():
            if qid in by_qid:
                _merge_ingredient(by_qid[qid], ing)
            else:
                by_qid[qid] = ing

    if skip_fetch:
        if not additives_path or not additives_path.exists():
            print("Error: --skip-fetch requires --additives file", file=sys.stderr)
            raise SystemExit(1)
        additives_data = json.loads(additives_path.read_text(encoding="utf-8"))
        stats["query1_rows"] = len((additives_data.get("results") or {}).get("bindings") or [])
        ingest(additives_data)
        if ingredients_path and ingredients_path.exists():
            ingredients_data = json.loads(ingredients_path.read_text(encoding="utf-8"))
            stats["query2_rows"] = len((ingredients_data.get("results") or {}).get("bindings") or [])
            ingest(ingredients_data)
    else:
        print("Query 1: food additives with properties...")
        additives_data = run_sparql(QUERY_FOOD_ADDITIVES, timeout=timeout)
        stats["query1_rows"] = len((additives_data.get("results") or {}).get("bindings") or [])
        print(f"  Received {stats['query1_rows']} rows")
        if additives_path:
            additives_path.parent.mkdir(parents=True, exist_ok=True)
            additives_path.write_text(
                json.dumps(additives_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        ingest(additives_data)

        time.sleep(1)

        print("Query 2: food ingredients broadly...")
        ingredients_data = run_sparql(QUERY_FOOD_INGREDIENTS, timeout=timeout)
        stats["query2_rows"] = len((ingredients_data.get("results") or {}).get("bindings") or [])
        print(f"  Received {stats['query2_rows']} rows")
        if ingredients_path:
            ingredients_path.parent.mkdir(parents=True, exist_ok=True)
            ingredients_path.write_text(
                json.dumps(ingredients_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        ingest(ingredients_data)

    return by_qid, stats


def _assign_unique_ids(ingredients: list[dict[str, Any]]) -> None:
    seen_ids: dict[str, int] = {}
    for ing in ingredients:
        base_id = ing["id"]
        if base_id in seen_ids:
            seen_ids[base_id] += 1
            ing["id"] = f"{base_id}_{seen_ids[base_id]}"
        else:
            seen_ids[base_id] = 1


def _print_summary(stats: dict[str, int], total: int) -> None:
    print(f"Query 1 rows:                  {stats['query1_rows']}")
    print(f"Query 2 rows:                  {stats['query2_rows']}")
    print(f"Total bindings processed:      {stats['rows_processed']}")
    print(f"Valid Wikidata ingredients:    {total}")
    print(f"Skipped (missing fields):      {stats['skipped_missing_fields']}")
    print(f"Skipped (QID label, no English): {stats['skipped_qid_label']}")
    print(f"Skipped (name length):         {stats['skipped_name_length']}")
    print(f"Skipped (already in OFF/USDA): {stats['skipped_existing']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch Wikidata ingredients/additives to staging JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help=f"Staging output (default: {_DEFAULT_OUTPUT.relative_to(_repo)})",
    )
    parser.add_argument(
        "--off-staging",
        type=Path,
        default=_DEFAULT_OFF_STAGING,
        help="OFF staging JSON for deduplication",
    )
    parser.add_argument(
        "--usda-staging",
        type=Path,
        default=_DEFAULT_USDA_STAGING,
        help="USDA staging JSON for deduplication",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Parse existing SPARQL JSON files instead of live queries",
    )
    parser.add_argument(
        "--additives",
        type=Path,
        default=_repo / "data" / "raw" / "wikidata_additives_sparql.json",
        help="Optional path to save/load query 1 raw JSON",
    )
    parser.add_argument(
        "--ingredients",
        type=Path,
        default=_repo / "data" / "raw" / "wikidata_ingredients_sparql.json",
        help="Optional path to save/load query 2 raw JSON",
    )
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    existing_names = _load_staging_names(args.off_staging) | _load_staging_names(args.usda_staging)
    if existing_names:
        print(
            f"Loaded {len(existing_names)} canonical names from OFF/USDA staging for dedup",
            file=sys.stderr,
        )

    try:
        by_qid, stats = fetch_and_parse(
            skip_fetch=args.skip_fetch,
            additives_path=args.additives,
            ingredients_path=args.ingredients,
            existing_names=existing_names,
            timeout=args.timeout,
        )
    except requests.RequestException as exc:
        print(f"Wikidata SPARQL request failed: {exc}", file=sys.stderr)
        return 1

    ingredients = sorted(by_qid.values(), key=lambda i: i["canonical_name"])
    _assign_unique_ids(ingredients)

    payload = {
        "source": "wikidata",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "total": len(ingredients),
        "ingredients": ingredients,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(ingredients)} ingredients to {args.output}")
    _print_summary(stats, len(ingredients))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
