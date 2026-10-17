from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SafetyClass = Literal[
    "plant_closed",
    "animalish",
    "allergen_adjacent",
    "dual_origin",
    "umbrella",
    "role_only",
]
ProposalKind = Literal["variant_alias", "ontology_role"]

A1_DANGEROUS: frozenset[str] = frozenset(
    {"animalish", "allergen_adjacent", "dual_origin", "umbrella"}
)

ROLE_ENUM: frozenset[str] = frozenset(
    {"plant_mod", "dairy_head", "process_keep", "culinary_keep"}
)


@dataclass
class InductionCandidate:
    proposal_kind: ProposalKind
    raw: str
    canonical: str | None
    role: str | None
    frequency: int
    miss_class: str | None
    safety_class: SafetyClass
    provenance: dict[str, Any] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
