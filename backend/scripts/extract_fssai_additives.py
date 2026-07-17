#!/usr/bin/env python3
"""
Extract FSSAI permitted food additives from Appendix A PDF.

Downloads (if needed) and parses:
  data/raw/fssai/appendix_a.pdf

Outputs:
  data/raw/fssai/permitted_additives.json
  data/raw/fssai/prohibited_substances.json  (curated + extracted mentions)

Uses pdfplumber for table extraction + text regex fallback.

Run from repo root:
  python backend/scripts/extract_fssai_additives.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
sys.path.insert(0, str(_backend))

from core.external_apis.fssai_regulations import APPENDIX_A_PDF_URL

_RAW = _repo / "data" / "raw" / "fssai"
_PDF = _RAW / "appendix_a.pdf"
_PERMITTED_OUT = _RAW / "permitted_additives.json"
_PROHIBITED_CURATED = _repo / "data" / "fssai_prohibited_substances.json"
_PROHIBITED_OUT = _RAW / "prohibited_substances.json"

_INS_RE = re.compile(r"^(\d{3,4}[a-z]?(?:\([^)]*\))?)$", re.I)
_SKIP_NAME = re.compile(
    r"^(GMP|mg/kg|mg/Kg|Food|Table|No additives|Omitted|Recommende|Level|Note|INS|Category|"
    r"\d+\s*mg|colour|color|fatty|hydrogen|yellow|Annex|\d+\.\d+|allowed|\(.*|"
    r"\d+\s*g/kg|maximum|plain|dairy|drinks|products|excluding|including|only|following)$",
    re.I,
)
_TABLE_ROW = re.compile(
    r"\|\s*([A-Za-z][^|]{2,70}?)\s*\|\s*(\d{3,4}[a-z]?(?:\([^)]*\))?)\s*\|",
    re.I,
)
_PROHIBITED_MENTION = re.compile(
    r"(?:not permitted|prohibited|banned|shall not be used)[^.]{0,80}?([A-Za-z][A-Za-z0-9\- ]{2,40})",
    re.I,
)


def _normalize_ins(ins: str) -> str:
    return ins.strip().replace(" ", "")


def _to_e_number(ins: str) -> str | None:
    ins = _normalize_ins(ins)
    if not re.match(r"^\d", ins):
        return None
    base = re.match(r"^(\d{3,4}[a-z]?)", ins, re.I)
    if not base:
        return None
    return f"E{base.group(1).upper()}"


def _clean_name(name: str) -> str | None:
    name = re.sub(r"\s+", " ", name.replace("\n", " ")).strip(" ,-|")
    if not name or len(name) < 3 or len(name) > 80:
        return None
    if _SKIP_NAME.match(name):
        return None
    if re.search(r"\d{3,4}\s*mg", name, re.I):
        return None
    if name.startswith("(") or name.endswith(")"):
        return None
    if re.match(r"^\d", name):
        return None
    if re.match(r"^(and|after|acid and|or|the|with)\b", name, re.I):
        return None
    if name.lower().endswith(" and") or name.lower().startswith("and "):
        return None
    if re.search(r"\bwares\b|\bproducts\b|\bcategory\b|\bbeverages\b", name, re.I):
        return None
    if name.count(" ") > 6:
        return None
    return name


def _add_additive(store: dict[str, dict[str, Any]], name: str, ins: str, source: str) -> None:
    name = _clean_name(name)
    if not name:
        return
    ins = _normalize_ins(ins)
    if not _INS_RE.match(ins):
        return
    key = name.lower()
    e_num = _to_e_number(ins)
    entry = store.setdefault(key, {
        "canonical_name": name,
        "ins_number": ins,
        "e_number": e_num,
        "aliases": [],
        "sources": [],
    })
    if e_num and e_num not in entry["aliases"]:
        entry["aliases"].insert(0, e_num)
    if ins not in entry["aliases"]:
        entry["aliases"].append(ins)
    if source not in entry["sources"]:
        entry["sources"].append(source)


def _extract_from_pdf_tables(pdf_path: Path) -> dict[str, dict[str, Any]]:
    import pdfplumber

    store: dict[str, dict[str, Any]] = {}
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table:
                    if not row:
                        continue
                    cells = [re.sub(r"\s+", " ", (c or "").replace("\n", " ")).strip() for c in row if c]
                    name = ins = None
                    for cell in cells:
                        if _INS_RE.match(cell.replace(" ", "")):
                            ins = cell
                        elif re.search(r"[A-Za-z]{2,}", cell):
                            if _clean_name(cell):
                                name = cell
                    if name and ins:
                        _add_additive(store, name, ins, "pdf_table")
    return store


def _extract_from_pdf_text(pdf_path: Path) -> dict[str, dict[str, Any]]:
    import pdfplumber

    store: dict[str, dict[str, Any]] = {}
    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join((p.extract_text() or "") for p in pdf.pages)

    for m in _TABLE_ROW.finditer(full_text):
        _add_additive(store, m.group(1), m.group(2), "text_table")

    # FSSAI Appendix A layout: "Aspartame 951 600 mg/kg" or "Allura red AC 129 100 mg/kg"
    line_pat = re.compile(
        r"(?m)^([A-Za-z][A-Za-z0-9 \-'(),/]{2,55}?)\s+"
        r"(\d{3,4}[a-z]?(?:\([^)]*\))?)\s+"
        r"(?:GMP|\d+(?:,\d+)?\s*mg)",
        re.I,
    )
    for m in line_pat.finditer(full_text):
        _add_additive(store, m.group(1), m.group(2), "text_line")

    # Same pattern without line anchors (wrapped PDF text)
    inline_pat = re.compile(
        r"([A-Z][A-Za-z0-9 \-'(),/]{2,50}?)\s+"
        r"(\d{3,4}[a-z]?(?:\([^)]*\))?)\s+"
        r"(?:GMP|\d+(?:,\d+)?\s*mg/kg|\d{3,4}\s*mg)",
        re.I,
    )
    for m in inline_pat.finditer(full_text):
        _add_additive(store, m.group(1), m.group(2), "text_inline")

    return store


def _merge_stores(*stores: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for store in stores:
        for key, entry in store.items():
            if key not in merged:
                merged[key] = entry
            else:
                existing = merged[key]
                for a in entry.get("aliases") or []:
                    if a not in existing["aliases"]:
                        existing["aliases"].append(a)
                for s in entry.get("sources") or []:
                    if s not in existing["sources"]:
                        existing["sources"].append(s)
    return merged


def _load_prohibited() -> list[dict[str, Any]]:
    if not _PROHIBITED_CURATED.exists():
        return []
    data = json.loads(_PROHIBITED_CURATED.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def extract_fssai_additives(pdf_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    from_tables = _extract_from_pdf_tables(pdf_path)
    from_text = _extract_from_pdf_text(pdf_path)
    permitted = sorted(_merge_stores(from_tables, from_text).values(), key=lambda r: r["canonical_name"].lower())
    prohibited = _load_prohibited()
    return permitted, prohibited


def _download_pdf(url: str, dest: Path) -> None:
    import requests

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} ...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"  Saved to {dest} ({dest.stat().st_size // 1024} KB)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract FSSAI food additives from Appendix A PDF")
    parser.add_argument("--pdf", type=Path, default=_PDF)
    parser.add_argument("--permitted-out", type=Path, default=_PERMITTED_OUT)
    parser.add_argument("--prohibited-out", type=Path, default=_PROHIBITED_OUT)
    parser.add_argument("--download", action="store_true", help="Download PDF from FSSAI if missing")
    args = parser.parse_args()

    if not args.pdf.exists():
        if args.download:
            _download_pdf(APPENDIX_A_PDF_URL, args.pdf)
        else:
            print(f"PDF not found: {args.pdf}", file=sys.stderr)
            print("Run: python backend/scripts/extract_fssai_additives.py --download", file=sys.stderr)
            return 1

    try:
        import pdfplumber  # noqa: F401
    except ImportError:
        print("pdfplumber required: pip install pdfplumber", file=sys.stderr)
        return 1

    permitted, prohibited = extract_fssai_additives(args.pdf)
    args.permitted_out.parent.mkdir(parents=True, exist_ok=True)
    with args.permitted_out.open("w", encoding="utf-8") as f:
        json.dump({"count": len(permitted), "additives": permitted}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with args.prohibited_out.open("w", encoding="utf-8") as f:
        json.dump({"count": len(prohibited), "substances": prohibited}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(permitted)} permitted additives to {args.permitted_out}")
    print(f"Wrote {len(prohibited)} prohibited/curated substances to {args.prohibited_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
