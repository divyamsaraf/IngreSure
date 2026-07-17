#!/usr/bin/env python3
"""
Transform FDA GRAS bulk exports (SCOGS + GRAS Notices) → Layer 1 ingest JSON.

Inputs (after ./scripts/download_sources_5_6.sh):
  data/raw/fda/scogs.xls
  data/raw/fda/gras_notices.xls
  data/fda_gras_manual_us.json  (curated US-only substances without E-numbers)

Output: data/layer1_fda_gras.json

License: US government public domain.

Run from repo root:
  python backend/scripts/transform_fda_gras_bulk.py
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
sys.path.insert(0, str(_backend))

from core.normalization.normalizer import normalize_ingredient_key, is_plausible_e_number_code

_SCOGS_IN = _repo / "data" / "raw" / "fda" / "scogs.xls"
_GRAS_IN = _repo / "data" / "raw" / "fda" / "gras_notices.xls"
_MANUAL_IN = _repo / "data" / "fda_gras_manual_us.json"
_DEFAULT_OUTPUT = _repo / "data" / "layer1_fda_gras.json"

_T_CELL = re.compile(r'^=T\("(.+)"\)$')
_HTML_TAG = re.compile(r"<[^>]+>")
_PLANT_HINTS = re.compile(
    r"gum|starch|inulin|oligosaccharide|pectin|cellulose|alginate|carrageenan|"
    r"lecithin|oil|extract|fiber|fibre|sugar|honey|molasses|protein|milk|"
    r"flour|grain|seed|bean|fruit|herb|spice|plant|algae|yeast",
    re.I,
)
_SYNTH_HINTS = re.compile(
    r"acid|sulfate|sulphate|phosphate|benzoate|sorbate|nitrite|nitrate|"
    r"hydroxide|oxide|chloride|carbonate|acetate|lactate|stearate|"
    r"paraben|gallate|hydroquinone|peroxide|silicate|aluminum|aluminium|"
    r"TBHQ|BHT|BHA|EDTA|MSG|aspartame|sucralose|acesulfame|saccharin|"
    r"monoglyceride|diglyceride|polysorbate|propylene glycol|glycerol|"
    r"enzyme|culture|ferment",
    re.I,
)


def _clean_cell(raw: str | None) -> str:
    if not raw:
        return ""
    val = raw.strip().strip('"')
    m = _T_CELL.match(val)
    if m:
        return m.group(1).strip()
    return val


def _strip_html(text: str) -> str:
    return _HTML_TAG.sub("", html.unescape(text)).strip()


def _split_aliases(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[;,/]", raw)
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        a = _strip_html(p).strip()
        if not a:
            continue
        n = normalize_ingredient_key(a)
        if n and n not in seen:
            out.append(a)
            seen.add(n)
    return out


def _infer_flags(name: str, *, synthetic_hint: bool | None = None) -> dict[str, Any]:
    plant = bool(_PLANT_HINTS.search(name))
    synth = bool(_SYNTH_HINTS.search(name))
    if synthetic_hint is True:
        synth = True
    if synthetic_hint is False:
        synth = False
    if synth and not plant:
        plant = False
    return {
        "plant_origin": plant and not synth,
        "animal_origin": bool(re.search(r"milk|cheese|whey|casein|egg|fish|meat|gelatin|collagen", name, re.I)),
        "synthetic": synth and not plant,
        "uncertainty_flags": ["fda_gras_inferred"],
    }


def _row_from_substance(
    name: str,
    aliases: list[str],
    *,
    cas: str | None = None,
    source_detail: str | None = None,
    **flags: Any,
) -> dict[str, Any]:
    canon = _strip_html(name).strip()
    if not canon:
        return {}
    inferred = _infer_flags(canon, synthetic_hint=flags.pop("synthetic", None))
    for k, v in flags.items():
        if k in inferred and v is not None:
            inferred[k] = v
    all_aliases = list(aliases)
    if cas and cas not in all_aliases:
        all_aliases.append(cas)
    if source_detail:
        all_aliases.append(source_detail)
    canon_norm = normalize_ingredient_key(canon)
    deduped: list[str] = []
    seen: set[str] = set()
    for a in all_aliases:
        an = normalize_ingredient_key(a)
        if not an or an == canon_norm or an in seen:
            continue
        if a.upper().startswith("E") and is_plausible_e_number_code(a.upper().replace(" ", "")):
            deduped.insert(0, a.upper().replace(" ", ""))
        else:
            deduped.append(a)
        seen.add(an)
    return {
        "canonical_name": canon,
        "aliases": deduped[:30],
        "source": "fda_gras",
        "region": "US",
        "regions": ["US"],
        **inferred,
    }


def _find_csv_header(lines: list[str], marker: str) -> int:
    for i, line in enumerate(lines):
        if line.startswith(marker):
            return i
    raise ValueError(f"CSV header not found (expected line starting with {marker!r})")


def _parse_scogs(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    hdr = _find_csv_header(lines, "GRAS Substance,")
    rows: list[dict[str, Any]] = []
    for row in csv.DictReader(lines[hdr:]):
        name = _clean_cell(row.get("GRAS Substance"))
        if not name:
            continue
        other = _clean_cell(row.get("Other Names"))
        cas = _clean_cell(row.get("CAS Reg. No. or other ID CODE"))
        conclusion = _clean_cell(row.get("SCOGS Type of Conclusion"))
        aliases = _split_aliases(other)
        detail = f"SCOGS conclusion type {conclusion}" if conclusion else None
        item = _row_from_substance(name, aliases, cas=cas or None, source_detail=detail)
        if item:
            rows.append(item)
    return rows


def _parse_gras_notices(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    hdr = _find_csv_header(lines, "GRAS Notice (GRN) No.,")
    rows: list[dict[str, Any]] = []
    for row in csv.DictReader(lines[hdr:]):
        name = _strip_html(_clean_cell(row.get("Substance")))
        if not name:
            continue
        grn = _clean_cell(row.get("GRAS Notice (GRN) No."))
        basis = _clean_cell(row.get("Basis"))
        detail = f"GRN {grn}" if grn else None
        if basis:
            detail = f"{detail}; {basis}" if detail else basis
        item = _row_from_substance(name, [], source_detail=detail)
        if item:
            rows.append(item)
    return rows


def _parse_manual(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        canon = (entry.get("canonical_name") or "").strip()
        if not canon:
            continue
        aliases = list(entry.get("aliases") or [])
        flags = {
            k: entry[k]
            for k in ("plant_origin", "animal_origin", "synthetic")
            if k in entry
        }
        item = _row_from_substance(
            canon,
            aliases,
            source_detail=entry.get("notes"),
            **flags,
        )
        if item:
            item["uncertainty_flags"] = ["fda_gras_manual"]
            rows.append(item)
    return rows


def transform_fda_gras_bulk(
    scogs_path: Path,
    gras_path: Path,
    manual_path: Path,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for batch in (
        _parse_scogs(scogs_path),
        _parse_gras_notices(gras_path),
        _parse_manual(manual_path),
    ):
        for row in batch:
            key = normalize_ingredient_key(row["canonical_name"])
            if not key:
                continue
            if key in merged:
                existing = merged[key]
                seen = {normalize_ingredient_key(a) for a in existing.get("aliases") or []}
                for a in row.get("aliases") or []:
                    an = normalize_ingredient_key(a)
                    if an and an not in seen:
                        existing.setdefault("aliases", []).append(a)
                        seen.add(an)
            else:
                merged[key] = row
    return sorted(merged.values(), key=lambda r: r["canonical_name"].lower())


def main() -> int:
    parser = argparse.ArgumentParser(description="Transform FDA GRAS bulk data to Layer 1")
    parser.add_argument("--scogs-input", type=Path, default=_SCOGS_IN)
    parser.add_argument("--gras-input", type=Path, default=_GRAS_IN)
    parser.add_argument("--manual-input", type=Path, default=_MANUAL_IN)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.scogs_input.exists() and not args.gras_input.exists():
        print("No FDA input files found.", file=sys.stderr)
        print("Run: ./scripts/download_sources_5_6.sh", file=sys.stderr)
        return 1

    rows = transform_fda_gras_bulk(args.scogs_input, args.gras_input, args.manual_input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(rows)} groups to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
