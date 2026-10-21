#!/usr/bin/env python3
"""Re-stream the OFF dump with country and language tags (ODbL, report-only).

Keeps code, countries_tags, languages_tags, ingredients_text plus
language-specific ingredients_text_* fields. Reservoir-samples at least
200 lists per market. Does not invent lists. Writes gitignored JSONL.
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
import sys
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
_DUMP_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"
_OUT = _BACKEND / ".local_reports" / "region_dump_ingredients.jsonl"
_SUMMARY = _BACKEND / ".local_reports" / "region_dump_sample_summary.json"

MARKETS = {
    "india": ("en:india",),
    "usa": ("en:united-states", "en:usa"),
    "canada": ("en:canada",),
    "uk": ("en:united-kingdom", "en:great-britain", "en:england"),
    "australia": ("en:australia",),
    "new_zealand": ("en:new-zealand",),
    "uae": ("en:united-arab-emirates", "en:uae"),
    "eu_fr": ("en:france",),
    "eu_de": ("en:germany",),
    "eu_es": ("en:spain",),
    "eu_it": ("en:italy",),
    "eu_nl": ("en:netherlands",),
    "eu_pl": ("en:poland",),
}


def _market_of(countries: list) -> str | None:
    tags = {str(c).lower() for c in countries or []}
    for market, needles in MARKETS.items():
        if any(n in tags for n in needles):
            return market
    return None


def _lang_texts(obj: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in obj.items():
        if not key.startswith("ingredients_text") or not isinstance(value, str):
            continue
        text = value.strip()
        if text:
            out[key] = text
    return out


def _reservoir_add(bucket: list, item, k: int, rng: random.Random, seen: int) -> None:
    if len(bucket) < k:
        bucket.append(item)
        return
    j = rng.randint(1, seen)
    if j <= k:
        bucket[j - 1] = item


def stream_sample(*, per_market: int, seed: int, max_lines: int | None) -> dict:
    rng = random.Random(seed)
    buckets: dict[str, list] = {m: [] for m in MARKETS}
    seen: dict[str, int] = {m: 0 for m in MARKETS}
    dump_date = None
    import requests

    with requests.get(
        _DUMP_URL,
        headers={"User-Agent": "IngreSure-RegionDumpSample/1.0 (research; ODbL)"},
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
                        "lines="
                        + str(i)
                        + " "
                        + ",".join(f"{m}:{len(buckets[m])}/{seen[m]}" for m in MARKETS),
                        flush=True,
                    )
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                code = str(obj.get("code") or "").strip()
                langs = _lang_texts(obj)
                text = (obj.get("ingredients_text") or langs.get("ingredients_text") or "").strip()
                if not code or len(text) < 8:
                    continue
                market = _market_of(obj.get("countries_tags") or [])
                if not market:
                    continue
                seen[market] += 1
                _reservoir_add(
                    buckets[market],
                    {
                        "code": code,
                        "market": market,
                        "countries_tags": obj.get("countries_tags") or [],
                        "languages_tags": obj.get("languages_tags") or [],
                        "ingredients_text": text,
                        "ingredients_text_by_lang": langs,
                        "source": "openfoodfacts",
                        "license": "ODbL-1.0",
                    },
                    per_market,
                    rng,
                    seen[market],
                )

    markets_out = {}
    rows = []
    for m, bucket in buckets.items():
        rng.shuffle(bucket)
        picked = bucket[:per_market]
        markets_out[m] = {
            "n": len(picked),
            "shortfall": max(0, per_market - len(picked)),
            "eligible_seen": seen[m],
        }
        rows.extend(picked)
    return {
        "dump_url": _DUMP_URL,
        "dump_date": dump_date,
        "seed": seed,
        "per_market_target": per_market,
        "odbl_note": (
            "ODbL-1.0 tagged source. Do not promote aliases into the knowledge "
            "base until counsel signs off share-alike."
        ),
        "markets": markets_out,
        "rows": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-market", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20261021)
    ap.add_argument("--max-lines", type=int, default=None)
    ap.add_argument("--out", type=Path, default=_OUT)
    ap.add_argument("--summary", type=Path, default=_SUMMARY)
    args = ap.parse_args(argv)

    result = stream_sample(
        per_market=args.per_market,
        seed=args.seed,
        max_lines=args.max_lines,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for row in result["rows"]:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {k: v for k, v in result.items() if k != "rows"}
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out} n={len(result['rows'])}", flush=True)
    print(json.dumps(summary["markets"], indent=2), flush=True)
    short = [m for m, info in summary["markets"].items() if info["shortfall"]]
    if short:
        print("SHORTFALL " + ",".join(short), flush=True)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
