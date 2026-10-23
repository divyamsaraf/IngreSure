"""
Structured compliance verdict. Single format for scan and chat.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VerdictStatus(str, Enum):
    SAFE = "SAFE"
    NOT_SAFE = "NOT_SAFE"
    UNCERTAIN = "UNCERTAIN"


_NOT_SAFE_ALIASES = frozenset({"NOT_SAFE", "AVOID", "FAIL"})
_SAFE_ALIASES = frozenset({"SAFE"})
_STATUS_RANK = {"NOT_SAFE": 3, "UNCERTAIN": 2, "SAFE": 1}


def normalize_external_status(status: Any) -> str:
    """Map an audit/group/engine status string to SAFE / NOT_SAFE / UNCERTAIN.

    Unrecognized, empty, DEPENDS, CHECK, WARN, and UNKNOWN fail closed to
    UNCERTAIN — never SAFE.
    """
    st = str(status or "").strip().upper()
    if st in _NOT_SAFE_ALIASES:
        return VerdictStatus.NOT_SAFE.value
    if st in _SAFE_ALIASES:
        return VerdictStatus.SAFE.value
    return VerdictStatus.UNCERTAIN.value


def worst_external_status(statuses: Any) -> str:
    """Worst-of fold over group statuses. Empty input is UNCERTAIN, not SAFE."""
    if isinstance(statuses, (str, bytes)):
        statuses = [statuses]
    worst: str | None = None
    for raw in statuses or []:
        mapped = normalize_external_status(raw)
        if worst is None or _STATUS_RANK[mapped] > _STATUS_RANK[worst]:
            worst = mapped
    return worst if worst is not None else VerdictStatus.UNCERTAIN.value


@dataclass
class ComplianceVerdict:
    status: VerdictStatus
    triggered_restrictions: list[str] = field(default_factory=list)
    triggered_ingredients: list[str] = field(default_factory=list)
    triggered_ingredient_to_input: dict[str, str] | None = None  # canonical -> raw user input (for display)
    # Per-ingredient FAIL restrictions (canonical -> restriction ids). Audit
    # cards must use this so Egg is not tagged with peanut_allergy when only
    # hindu_vegetarian FAILed for egg (and vice versa for peanut).
    triggered_restrictions_by_ingredient: dict[str, list[str]] = field(default_factory=dict)
    uncertain_ingredients: list[str] = field(default_factory=list)
    informational_ingredients: list[str] = field(default_factory=list)  # minor <2%, do not reduce confidence
    confidence_score: float = 0.0
    ontology_version: str = ""
    # Display-only evidence tier for the audit UI (never gates the verdict
    # itself): "verified" when every resolved ingredient rests on
    # LOCKED/VERIFIED knowledge, "limited" when any ingredient is untrusted
    # or from a low-trust/unclassified source, else "standard".
    evidence_tier: str = "standard"
    # True when the engine swallowed an exception and fail-closed to UNCERTAIN.
    degraded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "triggered_restrictions": list(self.triggered_restrictions),
            "triggered_ingredients": list(self.triggered_ingredients),
            "triggered_ingredient_to_input": dict(self.triggered_ingredient_to_input or {}),
            "triggered_restrictions_by_ingredient": {
                k: list(v) for k, v in (self.triggered_restrictions_by_ingredient or {}).items()
            },
            "uncertain_ingredients": list(self.uncertain_ingredients),
            "informational_ingredients": list(self.informational_ingredients),
            "confidence_score": self.confidence_score,
            "ontology_version": self.ontology_version,
            "evidence_tier": self.evidence_tier,
            "degraded": bool(self.degraded),
        }
