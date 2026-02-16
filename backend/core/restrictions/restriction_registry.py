"""
Loads restrictions from data/restrictions.json. Evaluates ingredient against rules only.
"""
from pathlib import Path
from typing import Any, Optional
import json
import logging

from .restriction_schema import Restriction, Rule, RuleAction
from core.ontology.ingredient_schema import Ingredient
from core.config import get_restrictions_path

logger = logging.getLogger(__name__)

_DEFAULT_RESTRICTIONS_PATH = get_restrictions_path()


def _get_ingredient_value(ing: Ingredient, field: str) -> Any:
    """Get field value from Ingredient for rule evaluation (including properties)."""
    if hasattr(Ingredient, field) and isinstance(getattr(Ingredient, field), property):
        return getattr(ing, field)
    if hasattr(ing, field):
        return getattr(ing, field)
    return None


def _evaluate_rule(ing: Ingredient, rule: Rule) -> bool:
    """
    Returns True if the rule condition is satisfied (so action should fire).
    E.g. field=animal_origin, operator=equals, value=true -> True when ing.animal_origin is True.
    """
    val = _get_ingredient_value(ing, rule.field)
    op = rule.operator
    target = rule.value

    if op == "equals":
        return val == target
    if op == "not_equals":
        return val != target
    if op == "contains":
        if val is None:
            return False
        if isinstance(val, list):
            return target in val
        return target in str(val)
    if op == "greater_than":
        if val is None:
            return False
        try:
            return float(val) > float(target)
        except (TypeError, ValueError):
            return False
    if op == "in_list":
        if val is None:
            return False
        return val in (target if isinstance(target, list) else [target])
    return False


class RestrictionRegistry:
    def __init__(self, restrictions_path: Optional[Path] = None):
        self._path = restrictions_path or _DEFAULT_RESTRICTIONS_PATH
        self._by_id: dict[str, Restriction] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            logger.warning("Restrictions file not found at %s; registry empty.", self._path)
            return
        with open(self._path, encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("restrictions", []):
            r = Restriction.from_dict(item)
            self._by_id[r.id] = r
        logger.info("Loaded %d restrictions from %s", len(self._by_id), self._path)

    def get(self, restriction_id: str) -> Optional[Restriction]:
        return self._by_id.get(restriction_id)

    def list_ids(self) -> list[str]:
        return list(self._by_id.keys())

    def evaluate(self, ingredient: Ingredient, restriction: Restriction) -> tuple[str, Optional[str]]:
        """
        Evaluate one ingredient against one restriction.
        Returns ("FAIL", reason) or ("WARN", reason) or ("PASS", None).
        """
        for rule in restriction.rules:
            if _evaluate_rule(ingredient, rule):
                return (rule.action.value, f"{restriction.id}: {rule.field} {rule.operator} {rule.value}")
        return ("PASS", None)
