from __future__ import annotations

from typing import Any, Mapping

from core.knowledge.ike2.coverage_os.hybrid_gate import row_flags
from core.knowledge.ike2.coverage_os.induction.cluster import ClusterItem
from core.knowledge.ike2.coverage_os.induction.safety_class import assign_safety_class
from core.knowledge.ike2.coverage_os.induction.types import ROLE_ENUM, InductionCandidate
from core.normalization.normalizer import normalize_ingredient_key


def _rows_by_canon(ontology: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in ontology.get("ingredients") or []:
        if not isinstance(row, Mapping):
            continue
        canon = normalize_ingredient_key(str(row.get("canonical_name") or ""))
        if canon:
            out[canon] = dict(row)
    return out


def _empty_role(row: Mapping[str, Any]) -> bool:
    return not str(row.get("role") or "").strip()


def _candidate_for_row(
    row: Mapping[str, Any],
    *,
    role: str,
    frequency: int,
    miss_class: str | None,
    provenance: dict[str, Any],
    ontology: Mapping[str, Any],
) -> InductionCandidate | None:
    if role not in ROLE_ENUM:
        return None
    canon = normalize_ingredient_key(str(row.get("canonical_name") or ""))
    if not canon:
        return None
    flags = row_flags(row)
    safety = assign_safety_class(
        candidate_name=str(row.get("canonical_name") or canon),
        flags=flags,
        ontology=ontology,
    )
    return InductionCandidate(
        proposal_kind="ontology_role",
        raw=canon,
        canonical=canon,
        role=role,
        frequency=frequency,
        miss_class=miss_class,
        safety_class=safety,
        provenance=provenance,
        flags=flags,
    )


def propose_role_pattern_fill(
    item: ClusterItem,
    *,
    ontology: Mapping[str, Any],
    role_index: Mapping[str, str],
) -> InductionCandidate | None:
    parts = normalize_ingredient_key(item.raw).split()
    if len(parts) != 2:
        return None
    a, b = parts[0], parts[1]
    rows = _rows_by_canon(ontology)

    def _try(known: str, other: str, proposed_role: str) -> InductionCandidate | None:
        if role_index.get(known) not in {"dairy_head", "plant_mod"}:
            return None
        row = rows.get(other)
        if row is None or not _empty_role(row):
            return None
        known_role = role_index.get(known)
        if known_role == "dairy_head" and proposed_role != "plant_mod":
            return None
        if known_role == "plant_mod" and proposed_role != "dairy_head":
            return None
        return _candidate_for_row(
            row,
            role=proposed_role,
            frequency=item.frequency,
            miss_class=item.miss_class,
            provenance={
                "rule": "pattern_fill",
                "neighbor": known,
                "cluster_key": item.normalized_key,
            },
            ontology=ontology,
        )

    return (
        _try(a, b, "plant_mod")
        or _try(b, a, "plant_mod")
        or _try(a, b, "dairy_head")
        or _try(b, a, "dairy_head")
    )


def propose_role_backfill(
    *,
    ontology: Mapping[str, Any],
    tear_evidence: Mapping[str, str],
) -> list[InductionCandidate]:
    out: list[InductionCandidate] = []
    for canon, row in _rows_by_canon(ontology).items():
        if not _empty_role(row):
            continue
        role = str(tear_evidence.get(canon) or "").strip()
        cand = _candidate_for_row(
            row,
            role=role,
            frequency=0,
            miss_class=None,
            provenance={"rule": "tear_backfill"},
            ontology=ontology,
        )
        if cand is not None:
            out.append(cand)
    return out
