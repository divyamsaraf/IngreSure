#!/usr/bin/env python3
"""
Transform ChEBI flat-file TSV bulk download → Layer 1 ingest JSON.

Inputs (after ./scripts/download_sources_3_4.sh):
  data/raw/chebi/compounds.tsv
  data/raw/chebi/names.tsv
  data/raw/chebi/database_accession.tsv

Output: data/layer1_chebi.json

License: ChEBI CC BY 4.0 — attribution required in product/docs.

Run from repo root:
  python backend/scripts/transform_chebi_bulk.py
  python backend/scripts/transform_chebi_bulk.py --require-cas   # default
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

from core.normalization.normalizer import normalize_ingredient_key, is_plausible_e_number_code
from core.external_apis.chebi import _infer_origin_from_entity

_CHEBI_DIR = _repo / "data" / "raw" / "chebi"
_DEFAULT_OUTPUT = _repo / "data" / "layer1_chebi.json"

_E_RE = re.compile(r"^e\s*(\d{3,4}[a-z]?)$", re.I)
_FOOD_ROLE_RE = re.compile(
    r"food additive|food component|food ingredient|flavour|flavor|"
    r"preservative|sweetener|colour|coloring|emulsifier|stabiliser|stabilizer|"
    r"thickener|antioxidant",
    re.I,
)


def _load_cas_by_compound(path: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row.get("type") != "CAS":
                continue
            cid = row.get("compound_id") or ""
            acc = (row.get("accession_number") or "").strip()
            if cid and acc and acc not in out.get(cid, []):
                out.setdefault(cid, []).append(acc)
    return out


def _load_names_by_compound(path: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            cid = row.get("compound_id") or ""
            name = (row.get("ascii_name") or row.get("name") or "").strip()
            if not cid or not name:
                continue
            names = out.setdefault(cid, [])
            if name not in names:
                names.append(name)
    return out


def _is_e_number_name(name: str) -> bool:
    s = name.strip().upper().replace(" ", "")
    if not s.startswith("E"):
        s = f"E{s}"
    return bool(_E_RE.match(s)) and is_plausible_e_number_code(s)


def _compound_to_row(
    compound: dict[str, str],
    names: list[str],
    cas_list: list[str],
) -> dict[str, Any] | None:
    canonical = (compound.get("ascii_name") or compound.get("name") or "").strip()
    if not canonical:
        return None
    if len(canonical) > 100 or len(canonical.split()) > 8:
        return None

    definition = (compound.get("definition") or "").strip()
    combined = f"{canonical} {definition} " + " ".join(names[:15])
    infer = _infer_origin_from_entity({"definition": definition, "ascii_name": canonical})

    aliases: list[str] = []
    seen: set[str] = set()
    canon_norm = normalize_ingredient_key(canonical)

    def add_alias(raw: str, *, alias_type: str = "synonym") -> None:
        norm = normalize_ingredient_key(raw)
        if not norm or norm == canon_norm or norm in seen:
            return
        seen.add(norm)
        aliases.append(raw)

    for n in names:
        if n != canonical:
            add_alias(n, alias_type="e_number" if _is_e_number_name(n) else "synonym")
    for cas in cas_list:
        add_alias(cas, alias_type="scientific")

    access = (compound.get("chebi_accession") or "").strip()
    if access:
        add_alias(access)

    return {
        "canonical_name": canonical,
        "aliases": aliases[:30],
        "source": "chebi",
        "animal_origin": infer.get("animal_origin", False),
        "plant_origin": infer.get("plant_origin", False),
        "synthetic": infer.get("synthetic", True),
        "insect_derived": infer.get("insect_derived", False),
        "uncertainty_flags": ["chebi_bulk_inferred"],
        "derived_from": [],
    }


def transform_chebi_bulk(
    chebi_dir: Path,
    *,
    min_stars: int = 3,
    require_cas: bool = True,
    food_keywords_only: bool = False,
) -> list[dict[str, Any]]:
    compounds_path = chebi_dir / "compounds.tsv"
    names_path = chebi_dir / "names.tsv"
    acc_path = chebi_dir / "database_accession.tsv"

    if not compounds_path.exists():
        raise FileNotFoundError(f"Missing {compounds_path}")

    cas_by = _load_cas_by_compound(acc_path)
    names_by = _load_names_by_compound(names_path)

    by_norm: dict[str, dict[str, Any]] = {}

    with compounds_path.open(encoding="utf-8") as f:
        for compound in csv.DictReader(f, delimiter="\t"):
            try:
                stars = int(compound.get("stars") or 0)
            except ValueError:
                stars = 0
            if stars < min_stars:
                continue

            cid = compound.get("id") or ""
            cas_list = cas_by.get(cid, [])
            if require_cas and not cas_list:
                continue

            names = names_by.get(cid, [])
            text_blob = " ".join([
                compound.get("definition") or "",
                compound.get("ascii_name") or "",
                " ".join(names[:5]),
            ])
            if food_keywords_only and not _FOOD_ROLE_RE.search(text_blob):
                if not any(_is_e_number_name(n) for n in names):
                    continue

            row = _compound_to_row(compound, names, cas_list)
            if not row:
                continue

            norm = normalize_ingredient_key(row["canonical_name"])
            if not norm:
                continue
            if norm not in by_norm:
                by_norm[norm] = row
            else:
                existing = by_norm[norm]
                seen = {normalize_ingredient_key(a) for a in existing.get("aliases") or []}
                for a in row.get("aliases") or []:
                    an = normalize_ingredient_key(a)
                    if an and an not in seen:
                        existing.setdefault("aliases", []).append(a)
                        seen.add(an)

    return sorted(by_norm.values(), key=lambda r: r["canonical_name"].lower())


def main() -> int:
    parser = argparse.ArgumentParser(description="Transform ChEBI TSV bulk files to Layer 1 JSON")
    parser.add_argument("--chebi-dir", type=Path, default=_CHEBI_DIR)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--min-stars", type=int, default=3, help="ChEBI star rating minimum (1-3)")
    parser.add_argument(
        "--require-cas",
        action="store_true",
        default=True,
        help="Only include compounds with a CAS number (default: on)",
    )
    parser.add_argument(
        "--no-require-cas",
        action="store_false",
        dest="require_cas",
        help="Include compounds without CAS",
    )
    parser.add_argument(
        "--food-keywords-only",
        action="store_true",
        help="Restrict to food/additive keyword or E-number names (~hundreds of rows)",
    )
    args = parser.parse_args()

    try:
        rows = transform_chebi_bulk(
            args.chebi_dir,
            min_stars=args.min_stars,
            require_cas=args.require_cas,
            food_keywords_only=args.food_keywords_only,
        )
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        print("Run: ./scripts/download_sources_3_4.sh", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(rows)} groups to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
