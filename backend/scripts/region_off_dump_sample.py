#!/usr/bin/env python3
"""Re-stream the OFF dump with country and language tags (ODbL, report-only).

Keeps code, countries_tags, languages_tags, ingredients_text plus
language-specific ingredients_text_* fields. Reservoir-samples 200 lists
per market (or all eligible if fewer). Runs to dump EOF. Does not invent
lists. Writes gitignored JSONL.
"""
from __future__ import annotations

import argparse
import gzip
import json
import random
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_DUMP_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"
_OUT = _BACKEND / ".local_reports" / "region_dump_ingredients.jsonl"
_SUMMARY = _BACKEND / ".local_reports" / "region_dump_sample_summary.json"
_PREFIX = _BACKEND / ".local_reports" / "region_dump_ingredients_prefix_uae_first200.jsonl"
_LOCAL_GZ = _BACKEND / ".local_reports" / "openfoodfacts-products.jsonl.gz"

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


def _ua_headers(extra: dict | None = None) -> dict:
    headers = {"User-Agent": "IngreSure-RegionDumpSample/1.0 (research; ODbL)"}
    if extra:
        headers.update(extra)
    return headers


def _preserve_prefix_sample(out: Path) -> None:
    if _PREFIX.exists() or not out.exists():
        return
    _PREFIX.write_bytes(out.read_bytes())
    print(f"preserved first-200 UAE prefix sample at {_PREFIX}", flush=True)


def _ensure_local_gz(dest: Path) -> tuple[Path, str | None]:
    """Download the dump to disk (resume with Range) so parse can reach EOF."""
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    dump_date = None
    with requests.head(
        _DUMP_URL, headers=_ua_headers(), timeout=60, allow_redirects=True
    ) as head:
        head.raise_for_status()
        dump_date = head.headers.get("Last-Modified") or head.headers.get("Date")
        total = int(head.headers.get("Content-Length") or 0)
    existing = dest.stat().st_size if dest.exists() else 0
    if total and existing == total:
        print(f"local dump complete bytes={existing} date={dump_date}", flush=True)
        return dest, dump_date
    extra: dict = {}
    mode = "wb"
    if existing and total and existing < total:
        extra["Range"] = f"bytes={existing}-"
        mode = "ab"
        print(f"resuming dump at byte {existing}/{total}", flush=True)
    with requests.get(
        _DUMP_URL,
        headers=_ua_headers(extra),
        stream=True,
        timeout=(60, 600),
    ) as resp:
        resp.raise_for_status()
        dump_date = (
            resp.headers.get("Last-Modified") or dump_date or resp.headers.get("Date")
        )
        if extra.get("Range") and resp.status_code != 206:
            mode = "wb"
            print("server ignored Range; restarting download", flush=True)
        print(
            f"dump download date={dump_date} bytes={resp.headers.get('Content-Length')} mode={mode}",
            flush=True,
        )
        with dest.open(mode) as fh:
            n = existing if mode == "ab" else 0
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                fh.write(chunk)
                n += len(chunk)
                if n % (256 * 1024 * 1024) < 1024 * 1024:
                    print(f"downloaded {n} bytes", flush=True)
    return dest, dump_date


def _checkpoint(path: Path, summary_path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in payload.get("rows") or []:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {k: v for k, v in payload.items() if k != "rows"}
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def _result(
    *,
    buckets: dict,
    seen: dict,
    rng: random.Random,
    per_market: int,
    seed: int,
    dump_date: str | None,
    reached_eof: bool,
    lines_read: int,
) -> dict:
    markets_out = {}
    rows = []
    for m, bucket in buckets.items():
        picked = list(bucket)
        if len(picked) > per_market:
            rng.shuffle(picked)
            picked = picked[:per_market]
        if not seen[m]:
            sampling = "none"
        elif reached_eof:
            sampling = "reservoir_to_eof" if seen[m] > per_market else "all_eligible"
        elif m == "uae" and seen[m] == len(picked):
            sampling = "first_n_non_random"
        else:
            sampling = "reservoir_prefix"
        markets_out[m] = {
            "n": len(picked),
            "shortfall": max(0, per_market - len(picked)),
            "eligible_seen": seen[m],
            "sampling": sampling,
        }
        rows.extend(picked)
    return {
        "dump_url": _DUMP_URL,
        "dump_date": dump_date,
        "seed": seed,
        "per_market_target": per_market,
        "reached_eof": reached_eof,
        "lines_read": lines_read,
        "uae_note": (
            "OFF-UAE is OFF coverage, not UAE shelves. "
            "first-200 UAE sample is non-random until reached_eof."
        ),
        "odbl_note": (
            "ODbL-1.0 tagged source. Do not promote aliases into the knowledge "
            "base until counsel signs off share-alike."
        ),
        "markets": markets_out,
        "rows": rows,
    }


def stream_sample(
    *,
    per_market: int,
    seed: int,
    max_lines: int | None,
    out: Path,
    summary: Path,
    local_gz: Path,
) -> dict:
    rng = random.Random(seed)
    buckets: dict[str, list] = {m: [] for m in MARKETS}
    seen: dict[str, int] = {m: 0 for m in MARKETS}
    dump_date = None
    reached_eof = False
    lines_read = 0
    _preserve_prefix_sample(out)
    gz_path, dump_date = _ensure_local_gz(local_gz)
    try:
        with gzip.GzipFile(filename=str(gz_path), mode="rb") as gz:
            for i, line in enumerate(gz, 1):
                lines_read = i
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
                    _checkpoint(
                        out,
                        summary,
                        _result(
                            buckets=buckets,
                            seen=seen,
                            rng=random.Random(seed),
                            per_market=per_market,
                            seed=seed,
                            dump_date=dump_date,
                            reached_eof=False,
                            lines_read=i,
                        ),
                    )
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                code = str(obj.get("code") or "").strip()
                langs = _lang_texts(obj)
                text = (
                    obj.get("ingredients_text") or langs.get("ingredients_text") or ""
                ).strip()
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
        reached_eof = max_lines is None
    except (OSError, ConnectionError, EOFError, Exception) as exc:
        print(f"stream ended early: {type(exc).__name__}: {exc}", flush=True)

    return _result(
        buckets=buckets,
        seen=seen,
        rng=rng,
        per_market=per_market,
        seed=seed,
        dump_date=dump_date,
        reached_eof=reached_eof,
        lines_read=lines_read,
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-market", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20261021)
    ap.add_argument("--max-lines", type=int, default=None)
    ap.add_argument("--out", type=Path, default=_OUT)
    ap.add_argument("--summary", type=Path, default=_SUMMARY)
    ap.add_argument("--local-gz", type=Path, default=_LOCAL_GZ)
    args = ap.parse_args(argv)

    result = stream_sample(
        per_market=args.per_market,
        seed=args.seed,
        max_lines=args.max_lines,
        out=args.out,
        summary=args.summary,
        local_gz=args.local_gz,
    )
    _checkpoint(args.out, args.summary, result)
    print(f"wrote {args.out} n={len(result['rows'])} eof={result['reached_eof']}", flush=True)
    print(json.dumps(result["markets"], indent=2), flush=True)
    short = [m for m, info in result["markets"].items() if info["shortfall"]]
    if short:
        print("SHORTFALL " + ",".join(short), flush=True)
        return 2
    if not result["reached_eof"]:
        print("INCOMPLETE dump did not reach EOF; UAE sample remains non-random", flush=True)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
