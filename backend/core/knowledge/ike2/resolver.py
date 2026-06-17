from dataclasses import dataclass
from typing import Literal, Optional

from core.evaluation.resolution_trust import is_trusted_for_compliance
from core.knowledge.ike2 import truth_anchor
from core.knowledge.ike2.stores import db


@dataclass
class ResolvedIngredient:
    group: object
    source: str
    confidence_band: str
    trusted: bool
    resolution_layer: str
    status: Literal["resolved", "uncertain"]


def _uncertain(layer: str, source: str) -> ResolvedIngredient:
    """Fail-closed: anything we cannot pin down is uncertain, never safe."""
    return ResolvedIngredient(
        group=None,
        source=source,
        confidence_band="none",
        trusted=False,
        resolution_layer=layer,
        status="uncertain",
    )


def resolve(atom: str, region: Optional[str]) -> ResolvedIngredient:
    # L1 — truth anchor (overrides everything, including the DB).
    fact = truth_anchor.lookup(atom)
    if fact is not None:
        return ResolvedIngredient(
            group=fact,
            source="truth_anchor",
            confidence_band="exact",
            trusted=is_trusted_for_compliance(fact, "static", "high"),
            resolution_layer="L1_truth_anchor",
            status="resolved",
        )

    # L3 — DB alias resolution (L2 cache omitted; correctness is unaffected).
    if db.disambiguate(atom, region) == "ambiguous":
        return _uncertain("L3_db_alias", "db")

    group = db.resolve_alias(atom, region)
    if group is not None:
        return ResolvedIngredient(
            group=group,
            source="db",
            confidence_band="high",
            trusted=is_trusted_for_compliance(group, "db", "high"),
            resolution_layer="L3_db_alias",
            status="resolved",
        )

    # L5 — unknown: enqueue for later enrichment and stay uncertain (fail-closed).
    return _uncertain("L5_unknown_queue", "unknown_queue")
