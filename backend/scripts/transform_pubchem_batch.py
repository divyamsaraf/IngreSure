#!/usr/bin/env python3
"""
Transform PubChem batch JSON → Layer 1 ingest JSON.

Inputs (from fetch_pubchem_batch.py):
  data/raw/pubchem/food_additive_cids.json
  data/raw/pubchem/compound_properties.json
  data/raw/pubchem/compound_synonyms.json

Output: data/layer1_pubchem.json

Run from repo root:
  python backend/scripts/transform_pubchem_batch.py
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

from core.normalization.normalizer import normalize_ingredient_key, is_plausible_e_number_code
from core.external_apis.pubchem import _infer_origin_from_synonyms_and_title

_CIDS_IN = _repo / "data" / "raw" / "pubchem" / "food_additive_cids.json"
_PROPS_IN = _repo / "data" / "raw" / "pubchem" / "compound_properties.json"
_SYNS_IN = _repo / "data" / "raw" / "pubchem" / "compound_synonyms.json"
_DEFAULT_OUTPUT = _repo / "data" / "layer1_pubchem.json"

_E_RE = re.compile(r"^E\s*(\d{3,4}[A-Za-z]?)$", re.I)
_CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


def _pick_canonical_name(synonyms: list[str], iupac: str | None, cid: int) -> str:
    candidates: list[str] = []
    if iupac and iupac.strip() and len(iupac) <= 80:
        candidates.append(iupac.strip())
    for s in synonyms:
        if not s:
            continue
        sl = s.lower()
        if "pubchem" in sl or len(s) > 80:
            continue
        if _CAS_RE.match(s.strip()) or _E_RE.match(s.strip().upper()):
            continue
        candidates.append(s.strip())
    if candidates:
        return min(candidates, key=lambda x: (len(x), x.lower()))
    if iupac and iupac.strip():
        return iupac.strip()
    return f"PubChem_{cid}"


def _alias_priority(name: str) -> int:
    s = name.strip().upper().replace(" ", "")
    if s.startswith("E") and is_plausible_e_number_code(s):
        return 0
    if _CAS_RE.match(name.strip()):
        return 1
    if name.startswith("PubChem:"):
        return 9
    return 5


def transform_pubchem_batch(
    cids_path: Path,
    props_path: Path,
    syns_path: Path,
) -> list[dict[str, Any]]:
    if not cids_path.exists():
        return []
    cids_data = json.loads(cids_path.read_text(encoding="utf-8"))
    cids = [int(c) for c in (cids_data.get("cids") or [])]

    props_by_cid: dict[int, dict[str, Any]] = {}
    if props_path.exists():
        props_data = json.loads(props_path.read_text(encoding="utf-8"))
        for row in props_data.get("properties") or []:
            cid = row.get("CID")
            if cid is not None:
                props_by_cid[int(cid)] = row

    syns_by_cid: dict[int, list[str]] = {}
    if syns_path.exists():
        syns_data = json.loads(syns_path.read_text(encoding="utf-8"))
        for k, v in (syns_data.get("synonyms") or {}).items():
            syns_by_cid[int(k)] = list(v or [])

    rows: list[dict[str, Any]] = []
    for cid in cids:
        props = props_by_cid.get(cid, {})
        syns = syns_by_cid.get(cid, [])
        iupac = (props.get("IUPACName") or "").strip() or None
        canon = _pick_canonical_name(syns, iupac, cid)
        infer = _infer_origin_from_synonyms_and_title(syns, canon)

        aliases: list[str] = [f"PubChem:{cid}"]
        if props.get("MolecularFormula"):
            aliases.append(str(props["MolecularFormula"]))
        for s in syns[:25]:
            if s and s != canon:
                aliases.append(s)
        aliases = sorted(
            dict.fromkeys(aliases),
            key=lambda a: (_alias_priority(a), a.lower()),
        )
        canon_norm = normalize_ingredient_key(canon)
        aliases = [
            a for a in aliases
            if normalize_ingredient_key(a) != canon_norm
        ][:30]

        rows.append({
            "canonical_name": canon,
            "aliases": aliases,
            "source": "pubchem",
            "plant_origin": infer.get("plant_origin", False),
            "animal_origin": infer.get("animal_origin", False),
            "synthetic": infer.get("synthetic", True),
            "insect_derived": infer.get("insect_derived", False),
            "uncertainty_flags": ["pubchem_bulk_inferred"],
        })

    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
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
    parser = argparse.ArgumentParser(description="Transform PubChem batch JSON to Layer 1")
    parser.add_argument("--cids-input", type=Path, default=_CIDS_IN)
    parser.add_argument("--props-input", type=Path, default=_PROPS_IN)
    parser.add_argument("--syns-input", type=Path, default=_SYNS_IN)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.cids_input.exists():
        print("No PubChem input found.", file=sys.stderr)
        print("Run: python backend/scripts/fetch_pubchem_batch.py", file=sys.stderr)
        return 1

    rows = transform_pubchem_batch(args.cids_input, args.props_input, args.syns_input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(rows)} groups to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
