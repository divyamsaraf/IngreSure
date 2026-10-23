#!/usr/bin/env python3
"""Idempotent production seed: ontology + allowlisted L1 only.

Never writes ike2_unknown_queue or shadow diffs. Dry-run by default.

    python scripts/seed_prod.py
    python scripts/seed_prod.py --apply --limit 50
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))
os.chdir(_BACKEND)

from dotenv import load_dotenv

load_dotenv(_BACKEND / ".env")
load_dotenv(_REPO / ".env")

from core.knowledge.ike2.etl.bulk_inject import _build_writer, inject, load_dump
from core.knowledge.ike2.etl.load_ontology import default_ontology_path, load_ontology_records

ALLOWED_L1 = frozenset({"produce_catalog", "animal_catalog", "infoods"})
FORBIDDEN = frozenset(
    {
        "unknown_queue",
        "ike2_unknown_queue",
        "shadow",
        "shadow_diff",
        "usda",
        "usda_fdc",
        "fssai",
        "wikidata",
        "off",
        "openfoodfacts",
        "staples",
        "staples_wave1",
    }
)
_STAPLES_DIR = _REPO / "data" / "staples_wave1"
_LAYER1 = {
    "produce_catalog": _REPO / "data" / "layer1_produce_catalog.json",
    "animal_catalog": _REPO / "data" / "layer1_animal_catalog.json",
    "infoods": _REPO / "data" / "layer1_infoods_anfood.json",
}


def plan_sources(requested: list[str]) -> list[dict]:
    names = list(requested) if requested else ["ontology", *sorted(ALLOWED_L1)]
    if names[0] != "ontology" and "ontology" not in names:
        names = ["ontology", *names]
    elif "ontology" in names:
        names = ["ontology"] + [n for n in names if n != "ontology"]
    out: list[dict] = []
    for name in names:
        key = name.strip()
        if key in FORBIDDEN:
            raise ValueError(f"refusing source {key!r} (unknown_queue/shadow/bulk L3)")
        if key == "ontology":
            path = default_ontology_path()
        elif key in ALLOWED_L1:
            path = _LAYER1[key]
        else:
            raise ValueError(f"source {key!r} is not allowlisted L1")
        resolved = Path(path).resolve()
        staples = _STAPLES_DIR.resolve()
        if resolved == staples or staples in resolved.parents:
            raise ValueError("refusing staples_wave1 (review CSVs, not ingest)")
        out.append({"source": key, "path": path})
    return out


def _records_for(item: dict) -> list[dict]:
    if item["source"] == "ontology":
        return load_ontology_records(item["path"])
    _src, records = load_dump(str(item["path"]))
    return list(records or [])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write to DB (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="explicit dry-run (default)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        default=[],
        help="repeatable; default ontology + produce/animal/infoods",
    )
    args = parser.parse_args(argv)
    dry = not args.apply
    if args.dry_run:
        dry = True

    try:
        plan = plan_sources(args.sources)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1

    writer = _build_writer(dry, "ike2_prod_seed_rejects.json")
    report = {"dry_run": dry, "sources": []}
    for item in plan:
        records = _records_for(item)
        if args.limit is not None:
            records = records[: args.limit]
        stats = inject(records, item["source"], writer)
        report["sources"].append(
            {
                "source": item["source"],
                "path": str(item["path"]),
                "planned": len(records),
                **stats.as_dict(),
            }
        )
    writer.flush()
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
