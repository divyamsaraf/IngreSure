#!/usr/bin/env python3
"""Operator CLI for Coverage OS Phase 2b induction.

Dry-run by default. Accept path always goes through submit_induced (force-human).

Usage:
  cd backend && python scripts/run_induction.py \\
    --ontology /path/to/ontology.json \\
    --aliases /path/to/variant_aliases.json \\
    --ledger /path/to/ledger.jsonl \\
    --unknown-log /path/to/unknown_ingredients_log.json \\
    [--tear-evidence /path/to/tear.json] \\
    [--reviewer-id id] \\
    [--no-dry-run]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.knowledge.ike2.coverage_os.induction.pipeline import build_candidates
from core.knowledge.ike2.coverage_os.induction.submit import submit_induced
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger


def main() -> int:
    p = argparse.ArgumentParser(description="Coverage OS Phase 2b induction")
    p.add_argument("--ontology", type=Path, required=True)
    p.add_argument("--aliases", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--unknown-log", type=Path, required=True)
    p.add_argument("--tear-evidence", type=Path, default=None)
    p.add_argument("--reviewer-id", default="induction-operator")
    p.add_argument("--min-frequency", type=int, default=1)
    p.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Print candidates only (default). Use --no-dry-run to submit interactively.",
    )
    args = p.parse_args()

    ontology = json.loads(args.ontology.read_text(encoding="utf-8"))
    aliases_data = json.loads(args.aliases.read_text(encoding="utf-8"))
    alias_table = {
        str(k): str(v)
        for k, v in (aliases_data.get("aliases") or {}).items()
        if not str(k).startswith("_")
    }
    tear = {}
    if args.tear_evidence and args.tear_evidence.exists():
        tear = json.loads(args.tear_evidence.read_text(encoding="utf-8"))

    cands = build_candidates(
        log_path=args.unknown_log,
        ontology=ontology,
        alias_table=alias_table,
        tear_evidence=tear,
        min_frequency=args.min_frequency,
    )
    print(f"{len(cands)} candidates")
    for i, c in enumerate(cands, 1):
        print(
            f"{i}. [{c.proposal_kind}] {c.raw} -> {c.canonical}"
            f" role={c.role} safety={c.safety_class} freq={c.frequency}"
        )

    if args.dry_run:
        print("dry-run: no submit")
        return 0

    ledger = PromoteLedger(args.ledger)
    for c in cands:
        ans = input(f"Accept {c.raw}? [y/N/q] ").strip().lower()
        if ans == "q":
            break
        if ans != "y":
            submit_induced(
                c,
                ledger=ledger,
                ontology_path=args.ontology,
                aliases_path=args.aliases,
                ontology=ontology,
                reviewer_id=args.reviewer_id,
                approval_rationale="reviewer_reject",
                decision="reject",
            )
            continue
        submit_induced(
            c,
            ledger=ledger,
            ontology_path=args.ontology,
            aliases_path=args.aliases,
            ontology=ontology,
            reviewer_id=args.reviewer_id,
            approval_rationale="induction accept",
            decision="accept",
        )
        ontology = json.loads(args.ontology.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
