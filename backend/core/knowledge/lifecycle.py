"""
Knowledge lifecycle primitives.

This module defines the internal states an ingredient/group can move through
as the system learns more about it. In Phase 1 this is scaffolding only and
does not change existing resolution or compliance behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class KnowledgeState(str, Enum):
    """
    Lifecycle for ingredient knowledge quality.

    UNKNOWN        - no structured knowledge yet (only logged as unknown)
    DISCOVERED     - fetched from an external source, unreviewed
    AUTO_CLASSIFIED- multiple sources / strong heuristics, still unverified
    VERIFIED       - human or high-trust source has confirmed correctness
    LOCKED         - canonically trusted; changes require versioning

    NOTE: For now this is not wired into the confidence engine; that will
    happen once the PostgreSQL-backed knowledge DB is introduced.
    """

    UNKNOWN = "UNKNOWN"
    DISCOVERED = "DISCOVERED"
    AUTO_CLASSIFIED = "AUTO_CLASSIFIED"
    VERIFIED = "VERIFIED"
    LOCKED = "LOCKED"


ResolutionLevel = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class KnowledgeMetadata:
    """
    Minimal metadata describing the trust level of a resolved ingredient/group.

    This abstraction allows the resolution pipeline to be explicit about
    where knowledge came from, without leaking storage details (JSON vs DB).
    """

    state: KnowledgeState
    source: str  # e.g. "static_ontology", "dynamic_ontology", "usda_fdc", "open_food_facts", "database"

    def to_resolution_level(self) -> ResolutionLevel:
        """
        Map lifecycle state to the coarse resolution bands used by the
        existing confidence engine (high/medium/low).

        This keeps the new lifecycle compatible with the current scoring
        model, while allowing more nuance later if needed.
        """
        if self.state in (KnowledgeState.LOCKED, KnowledgeState.VERIFIED, KnowledgeState.AUTO_CLASSIFIED):
            return "high"
        if self.state is KnowledgeState.DISCOVERED:
            return "medium"
        return "low"

