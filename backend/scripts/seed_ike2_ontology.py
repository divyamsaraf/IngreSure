#!/usr/bin/env python3
"""Seed IKE-2 L3 tables from runtime ``data/ontology.json``.

Usage (from backend/):
    python scripts/seed_ike2_ontology.py
    python scripts/seed_ike2_ontology.py --dry-run
    python scripts/seed_ike2_ontology.py --limit 50

Requires local Supabase with IKE-2 migrations applied and service role key in .env.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
os.chdir(_backend)

from dotenv import load_dotenv

load_dotenv(_backend / ".env")
load_dotenv(_backend.parent / ".env")

from core.knowledge.ike2.etl.bulk_inject import inject, _build_writer
from core.knowledge.ike2.etl.load_ontology import default_ontology_path, load_ontology_records


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Seed IKE-2 from data/ontology.json")
    parser.add_argument(
        "--ontology",
        type=Path,
        default=None,
        help=f"path to ontology.json (default: {default_ontology_path()})",
    )
    parser.add_argument("--limit", type=int, default=None, help="process only first N records")
    parser.add_argument("--dry-run", action="store_true", help="validate in memory only")
    parser.add_argument(
        "--reject-report",
        default="ike2_ontology_rejects.json",
        help="reject report path when writing to DB",
    )
    args = parser.parse_args(argv)

    path = args.ontology or default_ontology_path()
    records = load_ontology_records(path)
    if args.limit is not None:
        records = records[: args.limit]

    writer = _build_writer(args.dry_run, args.reject_report)
    stats = inject(records, "ontology", writer)
    writer.flush()

    print(
        json.dumps(
            {
                "ontology_path": str(path),
                "dry_run": args.dry_run,
                **stats.as_dict(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
