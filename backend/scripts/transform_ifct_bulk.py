#!/usr/bin/env python3
"""
Transform IFCT 2017 compositions CSV → Layer 1 ingest JSON.

Input (after ./scripts/download_sources_8_9_10.sh):
  data/raw/ifct2017/index.csv

Source: Indian Food Composition Tables 2017 (NIN/ICMR).
Open CSV mirror: https://github.com/ifct2017/compositions (index.csv)

Output: data/layer1_ifct.json

Run from repo root:
  python backend/scripts/transform_ifct_bulk.py
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

_IFCT_IN = _repo / "data" / "raw" / "ifct2017" / "index.csv"
_DEFAULT_OUTPUT = _repo / "data" / "layer1_ifct.json"

_ANIMAL_GROUPS = re.compile(r"egg|meat|poultry|fish|shellfish|mollusk|marine|milk", re.I)
_PLANT_GROUPS = re.compile(
    r"cereal|millet|legume|vegetable|fruit|nut|spice|condiment|sugar|mushroom|oil",
    re.I,
)


def _parse_lang_names(lang: str) -> list[str]:
    """Parse IFCT lang field: 'H. Ramdana; Kan. Danthu beeja; ...'"""
    if not lang:
        return []
    out: list[str] = []
    for part in re.split(r";", lang):
        p = part.strip()
        if not p:
            continue
        # Drop language prefix like 'H.' 'Kan.' 'Tam.'
        p = re.sub(r"^[A-Za-z]{1,4}\.\s*", "", p).strip()
        if p and len(p) > 1:
            out.append(p)
    return out


def _infer_flags(name: str, group: str, tags: str) -> dict[str, Any]:
    text = f"{name} {group} {tags}".lower()
    animal = bool(_ANIMAL_GROUPS.search(group))
    plant = bool(_PLANT_GROUPS.search(group)) and not animal
    if "vegetarian" in text and not animal:
        plant = True
    if "non-veg" in text or "non veg" in text:
        animal = True
    return {
        "plant_origin": plant,
        "animal_origin": animal,
        "dairy_source": "milk" in group.lower(),
        "egg_source": "egg" in group.lower(),
        "uncertainty_flags": ["ifct2017_inferred"],
    }


def transform_ifct_bulk(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    merged: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get("code") or "").strip().strip('"')
            name = (row.get("name") or "").strip().strip('"')
            scie = (row.get("scie") or "").strip().strip('"')
            group = (row.get("grup") or "").strip().strip('"')
            lang = (row.get("lang") or "").strip().strip('"')
            tags = (row.get("tags") or "").strip().strip('"')
            if not name:
                continue
            flags = _infer_flags(name, group, tags)
            aliases = _parse_lang_names(lang)
            if scie and scie.lower() != name.lower():
                aliases.append(scie)
            if code:
                aliases.append(f"IFCT:{code}")
            if group:
                aliases.append(group)
            canon_norm = normalize_ingredient_key(name)
            deduped: list[str] = []
            seen: set[str] = set()
            for a in aliases:
                an = normalize_ingredient_key(a)
                if an and an != canon_norm and an not in seen:
                    deduped.append(a)
                    seen.add(an)
            key = canon_norm
            entry = {
                "canonical_name": name,
                "aliases": deduped[:30],
                "source": "ifct",
                "region": "IN",
                "regions": ["IN"],
                **flags,
            }
            if key in merged:
                existing = merged[key]
                eseen = {normalize_ingredient_key(a) for a in existing.get("aliases") or []}
                for a in deduped:
                    an = normalize_ingredient_key(a)
                    if an and an not in eseen:
                        existing.setdefault("aliases", []).append(a)
                        eseen.add(an)
            else:
                merged[key] = entry
    return sorted(merged.values(), key=lambda r: r["canonical_name"].lower())


def main() -> int:
    parser = argparse.ArgumentParser(description="Transform IFCT 2017 CSV to Layer 1")
    parser.add_argument("--input", type=Path, default=_IFCT_IN)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input not found: {args.input}", file=sys.stderr)
        print("Run: ./scripts/download_sources_8_9_10.sh", file=sys.stderr)
        return 1

    rows = transform_ifct_bulk(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(rows)} groups to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
