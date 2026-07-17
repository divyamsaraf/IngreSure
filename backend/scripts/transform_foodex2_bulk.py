#!/usr/bin/env python3
"""
Transform FoodEx2 bulk CSV (Exposure hierarchy) → Layer 1 ingest JSON.

Input (after ./scripts/download_sources_5_6.sh):
  data/raw/foodex2/foodex2.csv   (AgroPortal export of UK FSA FoodEx2 register)

Output: data/layer1_foodex2.json

Filters RPC derivatives/ingredients and additive/flavour/processing-aid terms.
Excludes feed-only and hierarchy-only rows.

Run from repo root:
  python backend/scripts/transform_foodex2_bulk.py
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
sys.path.insert(0, str(_backend))

from core.normalization.normalizer import normalize_ingredient_key

_FOODEX_IN = _repo / "data" / "raw" / "foodex2" / "foodex2.csv"
_DEFAULT_OUTPUT = _repo / "data" / "layer1_foodex2.json"

STATE_DERIVATIVE = "http://data.food.gov.uk/codes/foodtype/def/state/d"
TERM_HIERARCHY = "http://data.food.gov.uk/codes/foodtype/def/corex/H"

_INGREDIENT_KW = re.compile(
    r"additive|flavour|flavor|flavoring|flavouring|processing aid|sweetener|"
    r"preservative|emulsifier|thickener|antioxidant|stabiliz|humectant|"
    r"acidity regulator|raising agent|glazing|anticaking|bulking|colour|"
    r"coloring|foaming|gelling|sequestrant|firming|flavour enhancer",
    re.I,
)
_PLANT_HINTS = re.compile(
    r"plant|herb|spice|fruit|vegetable|grain|seed|bean|algae|gum|starch|"
    r"inulin|pectin|cellulose|oil|extract|fibre|fiber|flour|sugar|honey",
    re.I,
)
_ANIMAL_HINTS = re.compile(r"milk|cheese|whey|casein|egg|fish|meat|gelatin|collagen|honey", re.I)


def _parse_label(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith("["):
        try:
            vals = json.loads(raw)
            if vals:
                return str(vals[0]).strip()
        except json.JSONDecodeError:
            pass
    return raw.strip('"')


def _parse_synonyms(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            vals = json.loads(raw)
            return [str(v).strip() for v in vals if str(v).strip()]
        except json.JSONDecodeError:
            pass
    return [raw]


def _code_from_uri(uri: str) -> str:
    if "/id/" in uri:
        return uri.rsplit("/id/", 1)[-1]
    return uri


def _include_row(label: str, state: str, term_type: str) -> bool:
    if term_type == TERM_HIERARCHY:
        return False
    if "(feed)" in label.lower():
        return False
    if state == STATE_DERIVATIVE:
        return True
    return bool(_INGREDIENT_KW.search(label))


def _infer_flags(label: str, definition: str = "") -> dict[str, Any]:
    text = f"{label} {definition}".lower()
    plant = bool(_PLANT_HINTS.search(text))
    animal = bool(_ANIMAL_HINTS.search(text))
    synth = bool(re.search(r"acid|phosphate|benzoate|sorbate|nitrite|enzyme|culture|E\d{3}", text))
    return {
        "plant_origin": plant and not synth,
        "animal_origin": animal,
        "synthetic": synth and not plant,
        "uncertainty_flags": ["foodex2_inferred"],
    }


def transform_foodex2_bulk(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    merged: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            label = _parse_label(row.get("Preferred Label") or "")
            if not label:
                continue
            state = row.get("state") or ""
            term_type = row.get("termType") or ""
            if not _include_row(label, state, term_type):
                continue
            code = _code_from_uri(row.get("Class ID") or "")
            definition = (row.get("Definitions") or row.get("http://www.w3.org/2004/02/skos/core#definition") or "").strip()
            flags = _infer_flags(label, definition)
            aliases = _parse_synonyms(row.get("Synonyms") or "")
            if code:
                aliases.append(f"FoodEx2:{code}")
            expo_code = (row.get("hierarchyCode_expo") or "").strip()
            if expo_code:
                aliases.append(f"FoodEx2.expo:{expo_code}")
            canon_norm = normalize_ingredient_key(label)
            deduped: list[str] = []
            seen: set[str] = set()
            for a in aliases:
                an = normalize_ingredient_key(a)
                if not an or an == canon_norm or an in seen:
                    continue
                deduped.append(a)
                seen.add(an)
            key = canon_norm
            if key in merged:
                existing = merged[key]
                eseen = {normalize_ingredient_key(a) for a in existing.get("aliases") or []}
                for a in deduped:
                    an = normalize_ingredient_key(a)
                    if an and an not in eseen:
                        existing.setdefault("aliases", []).append(a)
                        eseen.add(an)
            else:
                merged[key] = {
                    "canonical_name": label,
                    "aliases": deduped[:30],
                    "source": "foodex2",
                    "region": "EU",
                    "regions": ["EU"],
                    **flags,
                }
    return sorted(merged.values(), key=lambda r: r["canonical_name"].lower())


def main() -> int:
    parser = argparse.ArgumentParser(description="Transform FoodEx2 CSV to Layer 1")
    parser.add_argument("--input", type=Path, default=_FOODEX_IN)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input not found: {args.input}", file=sys.stderr)
        print("Run: ./scripts/download_sources_5_6.sh", file=sys.stderr)
        return 1

    rows = transform_foodex2_bulk(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(rows)} groups to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
