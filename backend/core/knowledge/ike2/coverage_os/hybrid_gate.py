from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Optional

from core.knowledge.ike2.coverage_os.deny_lists import is_allergen_adjacent, is_animalish
from core.knowledge.ike2.coverage_os.promote_ledger import PromoteLedger
from core.knowledge.ike2.truth_anchor import is_compound_umbrella
from core.normalization.normalizer import is_e_number_code, normalize_ingredient_key

_ROW_FLAG_KEYS = (
    "plant_origin", "animal_origin", "animal_species",
    "egg_source", "fish_source", "shellfish_source", "insect_derived",
    "bee_product", "dairy_source", "peanut_source", "tree_nut_source",
    "sesame_source", "soy_source", "gluten_source", "mustard_source",
    "celery_source", "lupin_source", "sulphite_source", "verdict_cap",
)


def _row_flags(row: Mapping[str, Any]) -> dict[str, Any]:
    nested = row.get("flags")
    if isinstance(nested, dict) and nested:
        return dict(nested)
    return {k: row[k] for k in _ROW_FLAG_KEYS if k in row}


def _norm_key(s: str) -> str:
    return normalize_ingredient_key(str(s).strip()) if s else ""


def has_dual_origin_collision(candidate_name: str, ontology: Mapping[str, Any]) -> bool:
    """True if candidate_name keys an animalish/allergen ontology row (canonical or alias)."""
    needle = _norm_key(candidate_name)
    if not needle:
        return False
    for row in ontology.get("ingredients") or []:
        if not isinstance(row, Mapping):
            continue
        names = {_norm_key(row.get("canonical_name") or row.get("name") or "")}
        for a in row.get("aliases") or []:
            names.add(_norm_key(a))
        names.discard("")
        if needle not in names:
            continue
        flags = _row_flags(row)
        if is_animalish(flags) or is_allergen_adjacent(flags):
            return True
    return False


def is_umbrella_term(candidate_name: str, flags: dict | None = None) -> bool:
    """Compound/process umbrella via shared Tier-1 logic + verdict_cap + E-number."""
    f = flags or {}
    if f.get("verdict_cap") == "WARN":
        return True
    if is_compound_umbrella(candidate_name or ""):
        return True
    if is_e_number_code(candidate_name or ""):
        return True
    return False


@dataclass(frozen=True)
class GateDecision:
    action: Literal["auto_promote", "human_approval", "rejected"]
    rule_id: str
    reason: str


def decide_promote(
    *,
    candidate_key: str,
    candidate_name: str,
    flags: Optional[dict[str, Any]],
    ledger: PromoteLedger,
    ontology: Mapping[str, Any],
) -> GateDecision:
    """Hybrid gate. Non-promotable short-circuit runs before any other predicate."""
    flags = dict(flags or {})

    blocked = ledger.find_non_promotable(candidate_key)
    if blocked is not None:
        return GateDecision(
            action="rejected",
            rule_id=str(blocked.get("rule_id") or "confirmed_non_promotable"),
            reason="confirmed_non_promotable",
        )

    collision = has_dual_origin_collision(candidate_name, ontology)
    umbrella = is_umbrella_term(candidate_name, flags)

    if is_allergen_adjacent(flags):
        return GateDecision(
            action="human_approval",
            rule_id="human_allergen_adjacent",
            reason="allergen-adjacent flags require human approval",
        )
    if is_animalish(flags):
        return GateDecision(
            action="human_approval",
            rule_id="human_animal_derived",
            reason="animal-derived flags require human approval",
        )
    if collision:
        return GateDecision(
            action="human_approval",
            rule_id="human_dual_origin_collision",
            reason="dual-origin name collision with animal/allergen ontology row",
        )
    if umbrella:
        return GateDecision(
            action="human_approval",
            rule_id="human_umbrella",
            reason="compound/process umbrella requires human approval",
        )

    if flags.get("plant_origin") and not flags.get("animal_origin"):
        return GateDecision(
            action="auto_promote",
            rule_id="closed_form_plant_v1",
            reason="closed_form_plant",
        )

    return GateDecision(
        action="human_approval",
        rule_id="human_fail_closed",
        reason="insufficient closed-form plant evidence",
    )
