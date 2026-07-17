#!/usr/bin/env python3
"""
Transform NIN curated Indian ingredient list → Layer 1 ingest JSON.

Input: data/nin_indian_ingredients.json

Output: data/layer1_nin.json

Source: Curated from NIN Nutritive Value of Indian Foods + regional names.
Extend data/nin_indian_ingredients.json as more items are digitized.

Run from repo root:
  python backend/scripts/transform_nin_bulk.py
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

_INPUT = _repo / "data" / "nin_indian_ingredients.json"
_DEFAULT_OUTPUT = _repo / "data" / "layer1_nin.json"


def transform_nin_bulk(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    merged: dict[str, dict[str, Any]] = {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        canon = (entry.get("canonical_name") or "").strip()
        if not canon:
            continue
        aliases = list(entry.get("aliases") or [])
        note = entry.get("notes")
        if note:
            aliases.append(note)
        row = {
            "canonical_name": canon,
            "aliases": [],
            "source": "nin",
            "region": entry.get("region") or "IN",
            "regions": entry.get("regions") or ["IN"],
            "plant_origin": entry.get("plant_origin", False),
            "animal_origin": entry.get("animal_origin", False),
            "synthetic": entry.get("synthetic", False),
            "dairy_source": entry.get("dairy_source", False),
            "soy_source": entry.get("soy_source", False),
            "sesame_source": entry.get("sesame_source", False),
            "uncertainty_flags": ["nin_curated"],
        }
        canon_norm = normalize_ingredient_key(canon)
        seen: set[str] = set()
        for a in aliases:
            an = normalize_ingredient_key(a)
            if an and an != canon_norm and an not in seen:
                row["aliases"].append(a)
                seen.add(an)
        key = canon_norm
        if key in merged:
            existing = merged[key]
            eseen = {normalize_ingredient_key(a) for a in existing.get("aliases") or []}
            for a in row["aliases"]:
                an = normalize_ingredient_key(a)
                if an and an not in eseen:
                    existing.setdefault("aliases", []).append(a)
                    eseen.add(an)
        else:
            merged[key] = row
    return sorted(merged.values(), key=lambda r: r["canonical_name"].lower())


def main() -> int:
    parser = argparse.ArgumentParser(description="Transform NIN Indian ingredients to Layer 1")
    parser.add_argument("--input", type=Path, default=_INPUT)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 1

    rows = transform_nin_bulk(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(rows)} groups to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
