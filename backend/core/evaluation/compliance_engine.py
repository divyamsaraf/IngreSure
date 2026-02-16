"""
Deterministic compliance engine. Single pipeline for scan and chat.
No LLM; no substring fallback. Unknown ingredient -> UNCERTAIN.
"""
from typing import List, Optional
import logging

from core.ontology.ingredient_registry import IngredientRegistry
from core.ontology.ingredient_schema import Ingredient
from core.restrictions.restriction_registry import RestrictionRegistry
from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.evaluation.confidence import compute_confidence

logger = logging.getLogger(__name__)


class ComplianceEngine:
    """
    Pipeline: normalize -> resolve -> evaluate each restriction -> aggregate verdict.
    """

    def __init__(
        self,
        ingredient_registry: Optional[IngredientRegistry] = None,
        restriction_registry: Optional[RestrictionRegistry] = None,
    ):
        self._ingredients = ingredient_registry or IngredientRegistry()
        self._restrictions = restriction_registry or RestrictionRegistry()

    def evaluate(
        self,
        ingredient_strings: List[str],
        restriction_ids: Optional[List[str]] = None,
        region_scope: Optional[str] = None,
    ) -> ComplianceVerdict:
        """
        Evaluate a list of ingredient strings against selected restrictions.
        - restriction_ids: if None, evaluate against all loaded restrictions (or pass explicit list for user profile).
        - region_scope: optional filter (e.g. "GLOBAL"); restrictions with matching region_scope are applied.
        Returns structured ComplianceVerdict. Unknown ingredients go to uncertain_ingredients and contribute to UNCERTAIN.
        """
        if not ingredient_strings:
            return ComplianceVerdict(
                status=VerdictStatus.UNCERTAIN,
                uncertain_ingredients=[],
                confidence_score=0.0,
                ontology_version=self._ingredients.get_version(),
            )

        # Normalize and resolve (unknowns logged in registry for ontology updates)
        resolved: List[Ingredient] = []
        uncertain_raw: List[str] = []
        for raw in ingredient_strings:
            key = raw.lower().strip()
            if not key:
                continue
            ing = self._ingredients.resolve(raw)
            if ing is None:
                uncertain_raw.append(raw)
            else:
                resolved.append(ing)
        if uncertain_raw:
            logger.info(
                "COMPLIANCE_ENGINE unknown_ingredients count=%d items=%s restriction_ids=%s",
                len(uncertain_raw),
                uncertain_raw,
                (restriction_ids or [])[:10],
            )

        # Select restrictions
        if restriction_ids is not None:
            rest_ids = [rid for rid in restriction_ids if self._restrictions.get(rid) is not None]
        else:
            rest_ids = self._restrictions.list_ids()
        if region_scope:
            rest_ids = [
                rid for rid in rest_ids
                if self._restrictions.get(rid) and region_scope in (self._restrictions.get(rid).region_scope or [])
            ]

        triggered_restrictions: List[str] = []
        triggered_ingredients: List[str] = []
        warning_count = 0

        for restriction_id in rest_ids:
            rest = self._restrictions.get(restriction_id)
            if not rest:
                continue
            for ing in resolved:
                result, reason = self._restrictions.evaluate(ing, rest)
                if result == "FAIL":
                    triggered_restrictions.append(restriction_id)
                    triggered_ingredients.append(ing.canonical_name)
                elif result == "WARN":
                    warning_count += 1

        # Deduplicate
        triggered_restrictions = list(dict.fromkeys(triggered_restrictions))
        triggered_ingredients = list(dict.fromkeys(triggered_ingredients))

        # Status: any FAIL -> NOT_SAFE; else any uncertain -> UNCERTAIN; else SAFE
        if triggered_restrictions:
            status = VerdictStatus.NOT_SAFE
        elif uncertain_raw:
            status = VerdictStatus.UNCERTAIN
        else:
            status = VerdictStatus.SAFE

        confidence = compute_confidence(
            total_ingredients=len(ingredient_strings),
            resolved_count=len(resolved),
            uncertain_ingredients=uncertain_raw,
            warning_count=warning_count,
        )

        return ComplianceVerdict(
            status=status,
            triggered_restrictions=triggered_restrictions,
            triggered_ingredients=triggered_ingredients,
            uncertain_ingredients=uncertain_raw,
            confidence_score=round(confidence, 4),
            ontology_version=self._ingredients.get_version(),
        )
