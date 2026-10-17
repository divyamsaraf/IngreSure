from __future__ import annotations

from typing import Any, Mapping

from core.knowledge.ike2.commodity_head import simple_commodity_head
from core.knowledge.ike2.coverage_os.hybrid_gate import row_flags
from core.knowledge.ike2.coverage_os.induction.cluster import ClusterItem
from core.knowledge.ike2.coverage_os.induction.safety_class import assign_safety_class
from core.knowledge.ike2.coverage_os.induction.types import InductionCandidate
from core.normalization.normalizer import normalize_ingredient_key


def _ontology_index(ontology: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for row in ontology.get("ingredients") or []:
        if not isinstance(row, Mapping):
            continue
        canon = normalize_ingredient_key(str(row.get("canonical_name") or row.get("name") or ""))
        if not canon:
            continue
        idx[canon] = dict(row)
        for a in row.get("aliases") or []:
            ak = normalize_ingredient_key(str(a))
            if ak:
                idx[ak] = dict(row)
    return idx


def _candidate_targets(raw: str, ontology_index: Mapping[str, dict[str, Any]]) -> set[str]:
    """Deterministic folds only — head + single token drop. No fuzzy."""
    targets: set[str] = set()
    nk = normalize_ingredient_key(raw)
    if not nk:
        return targets

    def _add_if_row(key: str) -> None:
        row = ontology_index.get(key)
        if row is None:
            return
        canon = normalize_ingredient_key(str(row.get("canonical_name") or ""))
        if canon:
            targets.add(canon)

    _add_if_row(nk)

    head = simple_commodity_head(raw)
    if head:
        _add_if_row(normalize_ingredient_key(head))

    parts = nk.split()
    if len(parts) >= 2:
        _add_if_row(normalize_ingredient_key(" ".join(parts[:-1])))
        _add_if_row(normalize_ingredient_key(" ".join(parts[1:])))
    return targets


def propose_alias(
    item: ClusterItem,
    *,
    ontology: Mapping[str, Any],
    alias_table: Mapping[str, str],
) -> InductionCandidate | None:
    nk = normalize_ingredient_key(item.normalized_key or item.raw)
    if not nk:
        return None
    if nk in alias_table:
        return None

    idx = _ontology_index(ontology)
    if nk in idx:
        return None

    targets = _candidate_targets(item.raw, idx)
    targets.discard(nk)
    if len(targets) != 1:
        return None

    canonical = next(iter(targets))
    row = idx[canonical]
    flags = row_flags(row)
    safety = assign_safety_class(
        candidate_name=str(row.get("canonical_name") or canonical),
        flags=flags,
        ontology=ontology,
    )
    return InductionCandidate(
        proposal_kind="variant_alias",
        raw=nk,
        canonical=canonical,
        role=None,
        frequency=item.frequency,
        miss_class=item.miss_class,
        safety_class=safety,
        provenance={
            "rule": "unique_closed_form",
            "cluster_key": item.normalized_key,
        },
        flags=flags,
    )
