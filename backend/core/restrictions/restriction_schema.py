"""
Rule DSL for restrictions. All restrictions are data-driven; no hardcoded if/else.
"""
from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum


class RuleAction(str, Enum):
    FAIL = "FAIL"
    WARN = "WARN"


class RestrictionCategory(str, Enum):
    ALLERGY = "allergy"
    RELIGIOUS = "religious"
    MEDICAL = "medical"
    LIFESTYLE = "lifestyle"


class Severity(str, Enum):
    STRICT = "STRICT"
    MODERATE = "MODERATE"
    CONDITIONAL = "CONDITIONAL"


@dataclass
class Rule:
    """Single predicate: if (field op value) then action."""
    field: str
    operator: str  # equals, not_equals, contains, greater_than, in_list
    value: Any
    action: RuleAction = RuleAction.FAIL

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
            "action": self.action.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Rule":
        action = d.get("action", "FAIL")
        if isinstance(action, str):
            action = RuleAction(action)
        return cls(
            field=d["field"],
            operator=d["operator"],
            value=d["value"],
            action=action,
        )


@dataclass
class Restriction:
    id: str
    category: RestrictionCategory
    region_scope: list[str]  # GLOBAL, US, EU, IN, etc.
    severity: Severity
    rules: list[Rule]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category.value,
            "region_scope": list(self.region_scope),
            "severity": self.severity.value,
            "rules": [r.to_dict() for r in self.rules],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Restriction":
        cat = d.get("category", "lifestyle")
        if isinstance(cat, str):
            cat = RestrictionCategory(cat)
        sev = d.get("severity", "STRICT")
        if isinstance(sev, str):
            sev = Severity(sev)
        return cls(
            id=d["id"],
            category=cat,
            region_scope=d.get("region_scope", ["GLOBAL"]) or ["GLOBAL"],
            severity=sev,
            rules=[Rule.from_dict(r) for r in d.get("rules", [])],
        )
