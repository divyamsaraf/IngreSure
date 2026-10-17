#!/usr/bin/env python3
"""Build Item 44 samples from the OFF bulk JSONL dump (no live search scraping).

Streams ``openfoodfacts-products.jsonl.gz`` (ODbL), reservoir-samples
per market, writes:
  - data/item44_off_freq_product_ids.json  (3000/market, unstratified)
  - data/item44_off_product_ids.json       (stratified ~216 if --eval too)

Records dump URL + Last-Modified / Date header as ``dump_date``.
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent

_DUMP_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"
_FREQ_PATH = _REPO / "data" / "item44_off_freq_product_ids.json"
_EVAL_PATH = _REPO / "data" / "item44_off_product_ids.json"

MARKETS = {
    "india": ("en:india",),
    "us": ("en:united-states", "en:usa"),
    "uk_eu": ("en:united-kingdom", "en:france", "en:germany", "en:european-union"),
}
CATEGORIES = {
    "snacks": ("en:snacks",),
    "sauces_condiments": ("en:sauces", "en:condiments"),
    "bakery": ("en:breads", "en:biscuits"),
    "dairy_alternatives": ("en:plant-based-milk-alternatives", "en:dairy-substitutes"),
    "ready_meals": ("en:meals", "en:prepared-meals"),
    "supplements": ("en:dietary-supplements", "en:vitamins"),
}


def _market_of(countries: list[str]) -> str | None:
    tags = {c.lower() for c in countries or []}
    for market, needles in MARKETS.items():
        if any(n in tags for n in needles):
            return market
    return None


def _category_of(categories: list[str]) -> str | None:
    tags = {c.lower() for c in categories or []}
    for cat, needles in CATEGORIES.items():
        if any(n in tags for n in needles):
            return cat
    return None


def _reservoir_add(bucket: list, item, k: int, rng: random.Random, seen: int) -> int:
    """Algorithm R; ``seen`` is 1-based count of eligible items for this bucket."""
    if len(bucket) < k:
        bucket.append(item)
    else:
        j = rng.randint(1, seen)
        if j <= k:
            bucket[j - 1] = item
    return seen


def stream_sample(
    *,
    per_market_freq: int,
    per_cell_eval: int,
    seed: int,
    max_lines: int | None,
) -> dict:
    rng = random.Random(seed)
    freq_buckets: dict[str, list] = {m: [] for m in MARKETS}
    freq_seen: dict[str, int] = {m: 0 for m in MARKETS}
    eval_buckets: dict[tuple[str, str], list] = defaultdict(list)
    eval_seen: dict[tuple[str, str], int] = defaultdict(int)

    dump_date = None
    import requests

    with requests.get(
        _DUMP_URL,
        headers={"User-Agent": "IngreSure-Item44DumpSample/1.0 (research; ODbL)"},
        stream=True,
        timeout=(60, 600),
    ) as resp:
        resp.raise_for_status()
        dump_date = (
            resp.headers.get("Last-Modified")
            or resp.headers.get("Date")
            or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        print(f"dump stream open date={dump_date} bytes={resp.headers.get('Content-Length')}", flush=True)
        resp.raw.decode_content = False
        with gzip.GzipFile(fileobj=resp.raw) as gz:
            for i, line in enumerate(gz, 1):
                if max_lines is not None and i > max_lines:
                    break
                if i % 200_000 == 0:
                    print(
                        f"lines={i} freq="
                        + ",".join(
                            f"{m}:{len(freq_buckets[m])}/{freq_seen[m]}" for m in MARKETS
                        ),
                        flush=True,
                    )
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                code = str(obj.get("code") or "").strip()
                text = (obj.get("ingredients_text") or "").strip()
                if not code or len(text) < 8:
                    continue
                countries = obj.get("countries_tags") or []
                market = _market_of(countries)
                if not market:
                    continue
                item = {"code": code, "market": market}
                freq_seen[market] += 1
                _reservoir_add(
                    freq_buckets[market], item, per_market_freq, rng, freq_seen[market]
                )
                cat = _category_of(obj.get("categories_tags") or [])
                if cat:
                    key = (market, cat)
                    eval_seen[key] += 1
                    _reservoir_add(
                        eval_buckets[key],
                        {"code": code, "market": market, "category": cat},
                        per_cell_eval,
                        rng,
                        eval_seen[key],
                    )

    freq_products = []
    markets_out = {}
    for m, bucket in freq_buckets.items():
        rng.shuffle(bucket)
        picked = bucket[:per_market_freq]
        markets_out[m] = {
            "n": len(picked),
            "shortfall": max(0, per_market_freq - len(picked)),
            "eligible_seen": freq_seen[m],
        }
        freq_products.extend(picked)

    meta = {
        "seed": seed,
        "sampling": "reservoir_from_off_jsonl_dump",
        "dump_url": _DUMP_URL,
        "dump_date": dump_date,
        "odbl_attribution": (
            "Product metadata from Open Food Facts (ODbL). "
            "Only product codes are stored — not ingredient texts."
        ),
        "per_market_target": per_market_freq,
        "n_products": len(freq_products),
        "markets": markets_out,
        "products": freq_products,
        "parser_note": "Lists must be re-fetched/flattened with current flatten_ingredients.",
    }
    return {"freq": meta, "eval_buckets": dict(eval_buckets), "eval_seen": dict(eval_seen), "dump_date": dump_date}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-market", type=int, default=3000)
    ap.add_argument("--per-cell", type=int, default=12)
    ap.add_argument("--seed", type=int, default=4402)
    ap.add_argument("--max-lines", type=int, default=None, help="debug cap")
    ap.add_argument("--eval", action="store_true", help="also rewrite stratified eval IDs")
    ap.add_argument("--freq-out", type=Path, default=_FREQ_PATH)
    ap.add_argument("--eval-out", type=Path, default=_EVAL_PATH)
    args = ap.parse_args(argv)

    result = stream_sample(
        per_market_freq=args.per_market,
        per_cell_eval=args.per_cell,
        seed=args.seed,
        max_lines=args.max_lines,
    )
    args.freq_out.parent.mkdir(parents=True, exist_ok=True)
    args.freq_out.write_text(json.dumps(result["freq"], indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.freq_out} n={result['freq']['n_products']}", flush=True)

    if args.eval:
        products = []
        cells = {}
        for (market, cat), bucket in result["eval_buckets"].items():
            cells[f"{market}/{cat}"] = {
                "n": len(bucket),
                "eligible_seen": result["eval_seen"][(market, cat)],
            }
            products.extend(bucket)
        eval_meta = {
            "seed": args.seed,
            "sampling": "reservoir_stratified_from_off_jsonl_dump",
            "dump_url": _DUMP_URL,
            "dump_date": result["dump_date"],
            "odbl_attribution": result["freq"]["odbl_attribution"],
            "target_per_cell": args.per_cell,
            "n_products": len(products),
            "cells": cells,
            "products": products,
            "parser_note": result["freq"]["parser_note"],
        }
        args.eval_out.write_text(json.dumps(eval_meta, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.eval_out} n={len(products)}", flush=True)

        # Keep frequency sample disjoint from the held-out eval set.
        held_codes = {p["code"] for p in products}
        freq = result["freq"]
        before = len(freq["products"])
        freq["products"] = [p for p in freq["products"] if p["code"] not in held_codes]
        removed = before - len(freq["products"])
        from collections import Counter

        mc = Counter(p["market"] for p in freq["products"])
        freq["n_products"] = len(freq["products"])
        freq["held_out_excluded"] = removed
        freq["disjoint_from_held_out"] = True
        for m in freq.get("markets") or {}:
            freq["markets"][m]["n"] = mc.get(m, 0)
        args.freq_out.write_text(json.dumps(freq, indent=2) + "\n", encoding="utf-8")
        print(
            f"rewrote {args.freq_out} n={freq['n_products']} "
            f"(excluded {removed} held-out overlaps)",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
