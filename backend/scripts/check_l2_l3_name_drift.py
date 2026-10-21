#!/usr/bin/env python3
"""Item 41 CI guard: name-keyed L3-true && L2-false drift (no aggregate counts).

Write-through policy: ontology-named rows must already store every verdict-relevant
true that a live/replayed L3 row holds. Read-time OR of L3 onto L2 is forbidden.

Usage (from backend/):
    python scripts/check_l2_l3_name_drift.py
    python scripts/check_l2_l3_name_drift.py --l3-json /tmp/l3_rows.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Mapping

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from core.knowledge.ike2.stores import local_ontology as lo
from core.normalization.normalizer import normalize_ingredient_key

VERDICT_FLAGS = (
    "animal_origin",
    "fish_source",
    "shellfish_source",
    "dairy_source",
    "egg_source",
    "gluten_source",
    "soy_source",
    "sesame_source",
    "peanut_source",
    "tree_nut_source",
    "mustard_source",
    "celery_source",
    "lupin_source",
    "sulphite_source",
)


def name_keyed_l3_l2_drift(
    l3_rows: Iterable[Mapping],
    l2_by_name: Mapping[str, Mapping],
    *,
    flags: Iterable[str] = VERDICT_FLAGS,
) -> list[tuple[str, str, str]]:
    """Return (name, flag, source) where L3 is true and L2 is not, keyed by name."""
    flag_list = tuple(flags)
    drifted: list[tuple[str, str, str]] = []
    for row in l3_rows:
        name = normalize_ingredient_key(str(row.get("canonical_name") or ""))
        if not name:
            continue
        l2 = l2_by_name.get(name)
        if l2 is None:
            continue
        source = str(row.get("source") or "")
        for flag in flag_list:
            if row.get(flag) and not l2.get(flag):
                drifted.append((name, flag, source))
    return drifted


def l2_flags_by_name() -> dict[str, dict]:
    lo.reset_cache()
    idx: dict[str, dict] = {}
    # local_ontology builds an index; walk via lookup of ontology records.
    from core.knowledge.ike2.etl.load_ontology import load_ontology_records

    for raw in load_ontology_records():
        name = normalize_ingredient_key(raw.get("canonical_name") or "")
        if not name:
            continue
        fact = lo.lookup(name)
        if fact is None:
            continue
        idx[name] = dict(fact.flags or {})
        for alias in raw.get("aliases") or []:
            alias_n = normalize_ingredient_key(alias)
            if alias_n:
                idx.setdefault(alias_n, dict(fact.flags or {}))
    return idx


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--l3-json",
        type=Path,
        help="Optional JSON list of L3-like rows. Without it, L2 is compared to itself (must be empty).",
    )
    args = p.parse_args(argv)
    l2 = l2_flags_by_name()
    if args.l3_json:
        l3 = json.loads(args.l3_json.read_text(encoding="utf-8"))
        if isinstance(l3, dict):
            l3 = l3.get("rows") or l3.get("groups") or []
    else:
        # Self-compare: L2 as both sides must produce zero drift.
        l3 = [
            {"canonical_name": name, "source": "l2_self", **flags}
            for name, flags in l2.items()
        ]
    drifted = name_keyed_l3_l2_drift(l3, l2)
    print(json.dumps({"n_l2": len(l2), "n_drift": len(drifted), "sample": drifted[:20]}, indent=2))
    return 1 if drifted else 0


if __name__ == "__main__":
    raise SystemExit(main())
