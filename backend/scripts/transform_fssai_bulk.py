#!/usr/bin/env python3
"""
Transform FSSAI extracted additives → Layer 1 ingest JSON.

Inputs:
  data/raw/fssai/permitted_additives.json
  data/raw/fssai/prohibited_substances.json

Output: data/layer1_fssai.json

Run from repo root:
  python backend/scripts/transform_fssai_bulk.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_backend = Path(__file__).resolve().parent.parent
_repo = _backend.parent
sys.path.insert(0, str(_backend))

from core.normalization.normalizer import normalize_ingredient_key

_PERMITTED_IN = _repo / "data" / "raw" / "fssai" / "permitted_additives.json"
_PROHIBITED_IN = _repo / "data" / "raw" / "fssai" / "prohibited_substances.json"
_DEFAULT_OUTPUT = _repo / "data" / "layer1_fssai.json"


def _row_from_permitted(entry: dict[str, Any]) -> dict[str, Any]:
    canon = entry.get("canonical_name") or ""
    aliases = list(entry.get("aliases") or [])
    e_num = entry.get("e_number")
    ins = entry.get("ins_number")
    if e_num and e_num not in aliases:
        aliases.insert(0, e_num)
    if ins and ins not in aliases:
        aliases.append(ins)
    if f"INS {ins}" not in aliases and ins:
        aliases.append(f"INS {ins}")
    canon_norm = normalize_ingredient_key(canon)
    return {
        "canonical_name": canon,
        "aliases": [a for a in aliases if normalize_ingredient_key(a) != canon_norm][:30],
        "source": "fssai",
        "region": "IN",
        "regions": ["IN"],
        "synthetic": True,
        "uncertainty_flags": ["fssai_permitted"],
        "alias_type": "e_number" if e_num else "synonym",
    }


def _row_from_prohibited(entry: dict[str, Any]) -> dict[str, Any]:
    canon = entry.get("canonical_name") or ""
    aliases = list(entry.get("aliases") or [])
    note = entry.get("notes")
    if note:
        aliases.append(note)
    canon_norm = normalize_ingredient_key(canon)
    flags = ["fssai_prohibited", "india_banned"]
    return {
        "canonical_name": canon,
        "aliases": [a for a in aliases if normalize_ingredient_key(a) != canon_norm][:30],
        "source": "fssai",
        "region": "IN",
        "regions": ["IN"],
        "synthetic": entry.get("synthetic", True),
        "plant_origin": entry.get("plant_origin", False),
        "animal_origin": entry.get("animal_origin", False),
        "uncertainty_flags": flags,
    }


def transform_fssai_bulk(permitted_path: Path, prohibited_path: Path) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    if permitted_path.exists():
        data = json.loads(permitted_path.read_text(encoding="utf-8"))
        for entry in data.get("additives") or []:
            row = _row_from_permitted(entry)
            key = normalize_ingredient_key(row["canonical_name"])
            if key:
                merged[key] = row
    if prohibited_path.exists():
        data = json.loads(prohibited_path.read_text(encoding="utf-8"))
        for entry in data.get("substances") or []:
            row = _row_from_prohibited(entry)
            key = normalize_ingredient_key(row["canonical_name"])
            if not key:
                continue
            if key in merged:
                existing = merged[key]
                existing["uncertainty_flags"] = list(set(
                    (existing.get("uncertainty_flags") or []) + row["uncertainty_flags"]
                ))
            else:
                merged[key] = row
    return sorted(merged.values(), key=lambda r: r["canonical_name"].lower())


def main() -> int:
    parser = argparse.ArgumentParser(description="Transform FSSAI data to Layer 1")
    parser.add_argument("--permitted-input", type=Path, default=_PERMITTED_IN)
    parser.add_argument("--prohibited-input", type=Path, default=_PROHIBITED_IN)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.permitted_input.exists() and not args.prohibited_input.exists():
        print("No FSSAI input found.", file=sys.stderr)
        print("Run: python backend/scripts/extract_fssai_additives.py --download", file=sys.stderr)
        return 1

    rows = transform_fssai_bulk(args.permitted_input, args.prohibited_input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(rows)} groups to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
