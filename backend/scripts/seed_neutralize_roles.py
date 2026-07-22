#!/usr/bin/env python3
"""Seed neutralize roles onto ontology via Coverage OS promote path.

Operator tool — run against explicit ontology/aliases/ledger paths.
Does not auto-commit production data. Role-only promotes go through
decide_promote (expect human_approval) then commit_promotion with reviewer fields.

Usage:
  cd backend && python scripts/seed_neutralize_roles.py \\
    --ontology /path/to/ontology.json \\
    --aliases /path/to/variant_aliases.json \\
    --ledger /path/to/ledger.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.knowledge.ike2.coverage_os.hybrid_gate import decide_promote
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger, candidate_key
from core.knowledge.ike2.coverage_os.promote_writer import commit_promotion

# Closed seed lists (formerly compound_expansion private Sets — owned here for seeding).
_PLANT_MOD = frozenset({
    "coconut", "almond", "soy", "oat", "oats", "rice", "cashew",
    "hemp", "pea", "cocoa", "shea", "sesame", "flax", "hazelnut",
    "peanut", "walnut", "pistachio", "macadamia", "pecan", "plant",
})
_DAIRY_HEADS = frozenset({
    "yogurt", "yoghurt", "milk", "cheese", "butter", "cream", "ghee",
    "paneer", "whey", "curd",
})
_CULINARY_KEEP = frozenset({
    "vinegar", "lecithin", "extract", "sauce", "juice", "syrup",
    "starch", "flour", "powder", "paste", "puree", "purée",
})
_PROCESS_KEEP = frozenset({
    "mechanically", "separated", "hydrolyzed", "textured", "rendered",
    "extracted", "concentrated", "isolated", "deboned", "ground", "minced",
    "base", "stock", "broth",
    "dried", "fresh", "frozen", "sliced", "diced", "chopped",
    "cooked", "roasted", "smoked", "cured", "raw",
})


def seed_role_list() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for name in sorted(_PLANT_MOD):
        out.append((name, "plant_mod"))
    for name in sorted(_DAIRY_HEADS):
        out.append((name, "dairy_head"))
    for name in sorted(_CULINARY_KEEP):
        out.append((name, "culinary_keep"))
    for name in sorted(_PROCESS_KEEP):
        out.append((name, "process_keep"))
    return out


def _flags_for(name: str, ontology: dict) -> dict:
    for row in ontology.get("ingredients") or []:
        if str(row.get("canonical_name") or "").strip().lower() == name.lower():
            flags = {}
            for k, v in row.items():
                if isinstance(v, bool):
                    flags[k] = v
            return flags
    return {}


def seed_roles(
    *,
    ontology_path: Path,
    aliases_path: Path,
    ledger_path: Path,
    reviewer_id: str = "phase2a-seed",
) -> int:
    ontology = json.loads(ontology_path.read_text(encoding="utf-8"))
    ledger = PromoteLedger(ledger_path)
    count = 0
    for name, role in seed_role_list():
        flags = _flags_for(name, ontology)
        key = candidate_key(name, name)
        decision = decide_promote(
            candidate_key=key,
            candidate_name=name,
            flags=flags,
            ledger=ledger,
            ontology=ontology,
        )
        if decision.action == "rejected":
            continue
        entry = {
            "candidate_key": key,
            "payload": {
                "write_kind": "ontology_row",
                "canonical_name": name,
                "role": role,
                "flags": flags if decision.action == "auto_promote" else {},
                "inverse": {
                    "write_kind": "ontology_row",
                    "canonical_name": name,
                    "prior_role": None,
                    "role_patch_only": True,
                },
            },
        }
        commit_promotion(
            entry,
            ledger,
            ontology_path=ontology_path,
            aliases_path=aliases_path,
            rule_id=decision.rule_id,
            source="phase2a_role_seed",
            auto=False,
            reviewer_id=reviewer_id,
            approval_rationale="phase2a role seed",
            candidate_key=key,
        )
        count += 1
        ontology = json.loads(ontology_path.read_text(encoding="utf-8"))
    return count


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ontology", type=Path, required=True)
    p.add_argument("--aliases", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--reviewer-id", default="phase2a-seed")
    args = p.parse_args()
    n = seed_roles(
        ontology_path=args.ontology,
        aliases_path=args.aliases,
        ledger_path=args.ledger,
        reviewer_id=args.reviewer_id,
    )
    print(f"seeded {n} role promotions")


if __name__ == "__main__":
    main()
