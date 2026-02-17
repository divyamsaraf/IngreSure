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
    uncertain_ingredients: list[str] = field(default_factory=list)
    informational_ingredients: list[str] = field(default_factory=list)  # minor <2%, do not reduce confidence
    confidence_score: float = 0.0
    ontology_version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "triggered_restrictions": list(self.triggered_restrictions),
            "triggered_ingredients": list(self.triggered_ingredients),
            "uncertain_ingredients": list(self.uncertain_ingredients),
            "informational_ingredients": list(self.informational_ingredients),
            "confidence_score": self.confidence_score,
            "ontology_version": self.ontology_version,
        }
