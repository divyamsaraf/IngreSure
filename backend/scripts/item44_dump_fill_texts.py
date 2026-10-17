#!/usr/bin/env python3
"""Fill gitignored ingredient texts for existing Item 44 ID lists from the OFF dump.

Streams the bulk JSONL once; writes matching codes to
``backend/.local_reports/item44_dump_ingredients.jsonl``. Does not rewrite ID files.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent

_DUMP_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"
_FREQ_PATH = _REPO / "data" / "item44_off_freq_product_ids.json"
_EVAL_PATH = _REPO / "data" / "item44_off_product_ids.json"
_TEXTS_PATH = _BACKEND / ".local_reports" / "item44_dump_ingredients.jsonl"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--texts-out", type=Path, default=_TEXTS_PATH)
    ap.add_argument("--max-lines", type=int, default=None)
    args = ap.parse_args(argv)

    want = set()
    for path in (_FREQ_PATH, _EVAL_PATH):
        data = json.loads(path.read_text(encoding="utf-8"))
        for p in data.get("products") or []:
            want.add(str(p["code"]))
    print(f"want codes={len(want)}", flush=True)

    found: dict[str, dict] = {}
    # Resume from existing file
    if args.texts_out.exists():
        with args.texts_out.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                code = str(row.get("code") or "")
                if code in want and (row.get("ingredients_text") or "").strip():
                    found[code] = row
        print(f"resume have={len(found)}", flush=True)

    if len(found) >= len(want):
        print("already complete", flush=True)
        return 0

    import requests

    missing = want - set(found)
    with requests.get(
        _DUMP_URL,
        headers={"User-Agent": "IngreSure-Item44DumpFill/1.0 (research; ODbL)"},
        stream=True,
        timeout=(60, 600),
    ) as resp:
        resp.raise_for_status()
        print(
            f"dump open date={resp.headers.get('Last-Modified')} "
            f"missing={len(missing)}",
            flush=True,
        )
        resp.raw.decode_content = False
        with gzip.GzipFile(fileobj=resp.raw) as gz:
            for i, line in enumerate(gz, 1):
                if args.max_lines is not None and i > args.max_lines:
                    break
                if i % 500_000 == 0:
                    print(f"lines={i} found={len(found)}/{len(want)}", flush=True)
                    _flush(args.texts_out, found)
                if not missing:
                    break
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                code = str(obj.get("code") or "").strip()
                if code not in missing:
                    continue
                text = (obj.get("ingredients_text") or "").strip()
                if len(text) < 8:
                    missing.discard(code)
                    continue
                found[code] = {"code": code, "ingredients_text": text}
                missing.discard(code)

    _flush(args.texts_out, found)
    print(f"done found={len(found)} still_missing={len(want - set(found))}", flush=True)
    return 0


def _flush(path: Path, found: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in found.values():
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
