#!/usr/bin/env python3
"""
Transform Wikidata SPARQL batch JSON → Layer 1 ingest JSON.

Inputs (from fetch_wikidata_batch.py):
  data/raw/wikidata_e_number_additives.json
  data/raw/wikidata_food_ingredients.json

Output: data/layer1_wikidata.json

Run from repo root:
  python backend/scripts/transform_wikidata_batch.py
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
from core.external_apis.wikidata_api import _infer_origin_from_description

_E_IN = _repo / "data" / "raw" / "wikidata_e_number_additives.json"
_FOOD_IN = _repo / "data" / "raw" / "wikidata_food_ingredients.json"
_DEFAULT_OUTPUT = _repo / "data" / "layer1_wikidata.json"

_E_RE = re.compile(r"^E\s*(\d{3,4}[A-Za-z]?)$", re.I)


def _val(binding: dict, key: str) -> str | None:
    node = binding.get(key)
    if not isinstance(node, dict):
        return None
    v = node.get("value")
    return str(v).strip() if v else None


def _qid_from_uri(uri: str) -> str:
    if "/entity/" in uri:
        return uri.rsplit("/", 1)[-1]
    return uri


def _normalize_e_number(raw: str) -> str | None:
    if not raw:
        return None
    s = raw.strip().upper().replace(" ", "")
    if not s.startswith("E"):
        s = f"E{s}"
    m = _E_RE.match(s)
    if not m:
        return None
    code = m.group(1).upper()
    if not is_plausible_e_number_code(f"E{code}"):
        return None
    return f"E{code}"


def _origin_flags(origin_label: str | None, label: str, description: str = "") -> dict[str, Any]:
    text = " ".join(filter(None, [origin_label, label, description])).lower()
    flags = _infer_origin_from_description(text, label)
    uncertainty: list[str] = ["wikidata_inferred"]
    return {
        "plant_origin": flags.get("plant_origin", False),
        "animal_origin": flags.get("animal_origin", False),
        "synthetic": flags.get("synthetic", False),
        "uncertainty_flags": uncertainty,
    }


def _aliases_from_binding(b: dict) -> list[str]:
    """Parse GROUP_CONCAT aliases or legacy per-row ?alias."""
    raw = _val(b, "aliases")
    if raw:
        return [a.strip() for a in raw.split("||") if a.strip()]
    alias = _val(b, "alias")
    return [alias] if alias else []


def _ingest_rows_from_bindings(bindings: list[dict]) -> dict[str, dict[str, Any]]:
    """Group SPARQL rows by item URI → Layer 1 row."""
    by_item: dict[str, dict[str, Any]] = {}

    for b in bindings:
        item_uri = _val(b, "item")
        label = _val(b, "itemLabel")
        if not item_uri or not label:
            continue

        if item_uri not in by_item:
            e_raw = _val(b, "eNumber")
            e_norm = _normalize_e_number(e_raw) if e_raw else None
            origin = _val(b, "originLabel")
            flags = _origin_flags(origin, label)
            if e_norm:
                flags["synthetic"] = True
            by_item[item_uri] = {
                "canonical_name": label,
                "aliases": [],
                "source": "wikidata",
                "wikidata_id": _qid_from_uri(item_uri),
                "e_number": e_norm,
                "cas_number": _val(b, "casNumber"),
                **flags,
            }

        row = by_item[item_uri]
        for alias in _aliases_from_binding(b):
            if alias and alias != row["canonical_name"]:
                existing = {normalize_ingredient_key(a) for a in row["aliases"]}
                an = normalize_ingredient_key(alias)
                if an and an not in existing and an != normalize_ingredient_key(row["canonical_name"]):
                    row["aliases"].append(alias)
                    existing.add(an)

        e_raw = _val(b, "eNumber")
        if e_raw and not row.get("e_number"):
            row["e_number"] = _normalize_e_number(e_raw)
        cas = _val(b, "casNumber")
        if cas and not row.get("cas_number"):
            row["cas_number"] = cas

    return by_item


def transform_wikidata_batch(
    e_number_path: Path | None,
    food_path: Path | None,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    for path in (e_number_path, food_path):
        if not path or not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        bindings = (data.get("results") or {}).get("bindings") or []
        rows = _ingest_rows_from_bindings(bindings)
        for item_uri, row in rows.items():
            if item_uri in merged:
                existing = merged[item_uri]
                seen = {normalize_ingredient_key(a) for a in existing.get("aliases") or []}
                for a in row.get("aliases") or []:
                    an = normalize_ingredient_key(a)
                    if an and an not in seen:
                        existing.setdefault("aliases", []).append(a)
                        seen.add(an)
                if row.get("e_number") and not existing.get("e_number"):
                    existing["e_number"] = row["e_number"]
            else:
                merged[item_uri] = row

    out: list[dict[str, Any]] = []
    for row in merged.values():
        aliases = list(row.get("aliases") or [])
        e_num = row.pop("e_number", None)
        cas = row.pop("cas_number", None)
        row.pop("wikidata_id", None)
        if e_num:
            aliases.insert(0, e_num)
        if cas and cas not in aliases:
            aliases.append(cas)
        canon_norm = normalize_ingredient_key(row["canonical_name"])
        row["aliases"] = [
            a for a in aliases
            if normalize_ingredient_key(a) != canon_norm
        ][:30]
        if e_num:
            row["alias_type"] = "e_number"
        out.append(row)

    return sorted(out, key=lambda r: r["canonical_name"].lower())


def main() -> int:
    parser = argparse.ArgumentParser(description="Transform Wikidata SPARQL JSON to Layer 1")
    parser.add_argument("--e-input", type=Path, default=_E_IN)
    parser.add_argument("--food-input", type=Path, default=_FOOD_IN)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.e_input.exists() and not args.food_input.exists():
        print("No Wikidata input files found.", file=sys.stderr)
        print("Run: python backend/scripts/fetch_wikidata_batch.py", file=sys.stderr)
        return 1

    rows = transform_wikidata_batch(args.e_input, args.food_input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(rows)} groups to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
