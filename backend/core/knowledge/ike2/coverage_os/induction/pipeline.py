from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from core.knowledge.ike2.coverage_os.induction.cluster import load_clusters
from core.knowledge.ike2.coverage_os.induction.propose_alias import propose_alias
from core.knowledge.ike2.coverage_os.induction.propose_role import (
    propose_role_backfill,
    propose_role_pattern_fill,
)
from core.knowledge.ike2.coverage_os.induction.types import InductionCandidate
from core.knowledge.ike2.coverage_os.neutralize import build_role_index
from core.knowledge.ike2.coverage_os.promote_ledger import candidate_key


def build_candidates(
    *,
    ontology: Mapping[str, Any],
    alias_table: Mapping[str, str],
    tear_evidence: Mapping[str, str] | None = None,
    log_path: Path | None = None,
    entries: Mapping[str, Any] | None = None,
    min_frequency: int = 1,
) -> list[InductionCandidate]:
    clusters = load_clusters(log_path, entries=entries, min_frequency=min_frequency)
    role_index = build_role_index(list(ontology.get("ingredients") or []))
    out: list[InductionCandidate] = []
    seen: set[str] = set()

    def _add(cand: InductionCandidate | None) -> None:
        if cand is None:
            return
        if cand.proposal_kind == "variant_alias":
            key = candidate_key(cand.raw, cand.canonical)
        else:
            key = candidate_key(cand.canonical or cand.raw, cand.canonical or cand.raw)
        if key in seen:
            return
        seen.add(key)
        out.append(cand)

    for item in clusters:
        _add(propose_alias(item, ontology=ontology, alias_table=alias_table))
        _add(propose_role_pattern_fill(item, ontology=ontology, role_index=role_index))
    for cand in propose_role_backfill(ontology=ontology, tear_evidence=tear_evidence or {}):
        _add(cand)
    out.sort(key=lambda c: (-c.frequency, c.raw))
    return out
