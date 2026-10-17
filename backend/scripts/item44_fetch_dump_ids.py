#!/usr/bin/env python3
"""Fetch ingredients_text for dump-based Item 44 ID lists into the product cache."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_BACKEND / "scripts"))

from item44_label_benchmark import _fetch_product

_CACHE = _BACKEND / ".local_reports" / "item44_off_product_cache.json"
_HELD = _REPO / "data" / "item44_off_product_ids.json"
_FREQ = _REPO / "data" / "item44_off_freq_product_ids.json"


def _load_cache() -> dict:
    if not _CACHE.exists():
        return {}
    return json.loads(_CACHE.read_text(encoding="utf-8"))


def _save_cache(cache: dict) -> None:
    _CACHE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE.write_text(json.dumps(cache) + "\n", encoding="utf-8")


def _has_text(cache: dict, code: str) -> bool:
    for k, v in cache.items():
        if not v:
            continue
        c = str(v.get("code") or k.split("|", 1)[0])
        if c == code and (v.get("ingredients_text") or "").strip():
            return True
    return False


def fetch_codes(codes: list[str], *, sleep: float = 0.35) -> tuple[int, int]:
    cache = _load_cache()
    fetched = 0
    skipped = 0
    for i, code in enumerate(codes, 1):
        if _has_text(cache, code):
            skipped += 1
            continue
        prod = _fetch_product(code)
        if prod and (prod.get("ingredients_text") or "").strip():
            cache[f"{code}|dump"] = prod
            fetched += 1
        if i % 25 == 0:
            _save_cache(cache)
            print(f"progress {i}/{len(codes)} fetched={fetched} skipped={skipped}", flush=True)
        time.sleep(sleep)
    _save_cache(cache)
    return fetched, skipped


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--held", action="store_true", help="fetch stratified 216")
    ap.add_argument("--freq", action="store_true", help="fetch frequency IDs missing from cache")
    ap.add_argument("--freq-limit", type=int, default=0, help="cap new freq fetches (0=all missing)")
    ap.add_argument("--sleep", type=float, default=0.35)
    args = ap.parse_args(argv)
    if not args.held and not args.freq:
        args.held = True

    if args.held:
        held = json.loads(_HELD.read_text(encoding="utf-8"))
        codes = [p["code"] for p in held.get("products") or []]
        print(f"fetching held-out n={len(codes)}", flush=True)
        f, s = fetch_codes(codes, sleep=args.sleep)
        print(f"held done fetched={f} skipped={s}", flush=True)

    if args.freq:
        freq = json.loads(_FREQ.read_text(encoding="utf-8"))
        cache = _load_cache()
        missing = [p["code"] for p in freq.get("products") or [] if not _has_text(cache, p["code"])]
        if args.freq_limit:
            missing = missing[: args.freq_limit]
        print(f"fetching freq missing n={len(missing)}", flush=True)
        f, s = fetch_codes(missing, sleep=args.sleep)
        print(f"freq done fetched={f} skipped={s}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
