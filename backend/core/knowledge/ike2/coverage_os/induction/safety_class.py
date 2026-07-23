from __future__ import annotations

from typing import Any, Mapping

from core.knowledge.ike2.coverage_os.deny_lists import (
    is_allergen_adjacent,
    is_animalish,
)
from core.knowledge.ike2.coverage_os.hybrid_gate import (
    has_dual_origin_collision,
    is_umbrella_term,
)
from core.knowledge.ike2.coverage_os.induction.types import SafetyClass


def assign_safety_class(
    *,
    candidate_name: str,
    flags: Mapping[str, Any] | None,
    ontology: Mapping[str, Any],
) -> SafetyClass:
    """Label for precision A1 — same predicates/order as decide_promote."""
    f = dict(flags or {})
    if is_allergen_adjacent(f):
        return "allergen_adjacent"
    if is_animalish(f):
        return "animalish"
    if has_dual_origin_collision(candidate_name, ontology):
        return "dual_origin"
    if is_umbrella_term(candidate_name, f):
        return "umbrella"
    if f.get("plant_origin") and not f.get("animal_origin"):
        return "plant_closed"
    return "role_only"
