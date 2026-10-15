#!/usr/bin/env python3
"""Transform FAO/INFOODS AnFooD2.0 → Layer-1 JSON (Item 11).

Downloads the workbook if missing, emits via InfoodsAnfoodAdapter + license gate.

  python backend/scripts/transform_infoods_anfood.py
  python backend/scripts/transform_infoods_anfood.py --input path/to/AnFooD2.0.xlsx
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
sys.path.insert(0, str(_backend))

from core.knowledge.ike2.etl.adapters.infoods_anfood import (  # noqa: E402
    InfoodsAnfoodAdapter,
    write_layer1_dump,
)

_DEFAULT_URL = (
    "https://www.fao.org/fileadmin/templates/food_composition/documents/AnFooD2.0.xlsx"
)
_DEFAULT_XLSX = _repo / "data" / "raw" / "infoods" / "AnFooD2.0.xlsx"
_DEFAULT_OUT = _repo / "data" / "layer1_infoods_anfood.json"


def _ensure_xlsx(path: Path, url: str, *, download: bool) -> Path:
    if path.is_file():
        return path
    if not download:
        raise SystemExit(f"AnFooD workbook not found: {path} (pass --download)")
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} → {path}")
    urllib.request.urlretrieve(url, path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=_DEFAULT_XLSX)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUT)
    parser.add_argument("--url", default=_DEFAULT_URL)
    parser.add_argument(
        "--download",
        action="store_true",
        help="download AnFooD2.0.xlsx when --input is missing",
    )
    args = parser.parse_args()

    xlsx = _ensure_xlsx(args.input, args.url, download=args.download)
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("openpyxl required: pip install openpyxl", file=sys.stderr)
        return 1

    rows = write_layer1_dump(
        args.output,
        adapter=InfoodsAnfoodAdapter(xlsx_path=xlsx),
    )
    if not rows:
        print(
            "No rows emitted (license deny or empty workbook). "
            "Check license_allowlist.json source_licenses.infoods.",
            file=sys.stderr,
        )
        return 1
    print(f"Wrote {len(rows)} groups to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
