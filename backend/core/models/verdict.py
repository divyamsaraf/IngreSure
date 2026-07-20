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
        }
