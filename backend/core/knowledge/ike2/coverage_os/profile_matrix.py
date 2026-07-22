# backend/core/knowledge/ike2/coverage_os/profile_matrix.py
from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, Optional

from core.knowledge.ike2 import resolution_cache
from core.knowledge.ike2.compliance import evaluate
from core.knowledge.ike2.coverage_os.evidence_chain import build_chain_from_resolve
from core.knowledge.ike2.input_layer import parse_atoms
from core.knowledge.ike2.resolver import resolve
from core.knowledge.ike2.rules import SUPPORTED_RESTRICTIONS, seeded_rules
from core.knowledge.ike2.seam import to_compliance_input
from core.knowledge.ike2.stores import local_ontology
from core.knowledge.ike2.variant_aliases import reset_variant_alias_cache


def _reset_l2_caches() -> None:
    """Drop in-process L2 resolution state so a full matrix run sees current files.

    Called at the start of every ``run_matrix`` (default). Does not clear mid-run;
    within one paste, resolve write-through cache remains useful across atoms.
    """
    resolution_cache.clear()
    local_ontology.reset_cache()
    reset_variant_alias_cache()


def run_matrix(
    raw: str,
    restriction_ids: Optional[Iterable[str]] = None,
    *,
    region: Optional[str] = None,
    clear_caches: bool = True,
) -> list[dict[str, Any]]:
    if clear_caches:
        _reset_l2_caches()

    if restriction_ids is None:
        profiles = sorted(SUPPORTED_RESTRICTIONS)
    else:
        profiles = list(restriction_ids)

    atoms = parse_atoms(raw)
    rules = seeded_rules()
    rows: list[dict[str, Any]] = []

    for atom in atoms:
        resolved = resolve(atom.name, region)
        compliance_input = to_compliance_input(
            resolved,
            trace=atom.trace,
            may_contain=atom.may_contain,
            query_atom=atom.name,
        )
        for restriction_id in profiles:
            profile = SimpleNamespace(
                restrictions={restriction_id: "preference"},
            )
            # One restriction per evaluate so this cell's ComplianceResult is not
            # an aggregate across unrelated profiles (bucket still comes from chain).
            compliance_result = evaluate([compliance_input], profile, rules)
            chain = build_chain_from_resolve(
                atom=atom.name,
                resolved=resolved,
                compliance_result=compliance_result,
                restriction_id=restriction_id,
                compliance_input=compliance_input,
            )
            rows.append({
                "ingredient": atom.name,
                "profile": restriction_id,
                "bucket": chain.verdict,  # Safe | Avoid | Depends — already audit bucket
                "chain": chain.to_dict(),
            })
    return rows


def write_matrix_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["ingredient", "profile", "bucket", "evidence_class", "miss_class"],
        )
        w.writeheader()
        for r in rows:
            chain = r.get("chain") or {}
            w.writerow({
                "ingredient": r.get("ingredient"),
                "profile": r.get("profile"),
                "bucket": r.get("bucket"),
                "evidence_class": chain.get("evidence_class"),
                "miss_class": chain.get("miss_class"),
            })
