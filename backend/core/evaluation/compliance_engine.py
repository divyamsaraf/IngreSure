"""
Deterministic compliance engine. Single pipeline for scan and chat.
Resolve: 1) static ontology 2) dynamic ontology 3) external API if enabled.
Unknown ingredient -> UNCERTAIN; trace/minor ingredients optionally informational only.
"""
from typing import List, Optional, Set
import logging

from core.ontology.ingredient_registry import IngredientRegistry
from core.ontology.ingredient_schema import Ingredient
from core.restrictions.restriction_registry import RestrictionRegistry
from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.evaluation.confidence import compute_confidence

logger = logging.getLogger(__name__)


class ComplianceEngine:
    """
    Pipeline: resolve (static -> dynamic -> API) -> evaluate restrictions -> aggregate verdict.
    User profile (restriction_ids, profile_context) influences which restrictions run and logging.
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
        trace_ingredient_keys: Optional[Set[str]] = None,
        use_api_fallback: bool = True,
        profile_context: Optional[dict] = None,
    ) -> ComplianceVerdict:
        """
        Evaluate ingredient strings against restrictions.
        - restriction_ids: from user profile (allergens, dietary, religious, lifestyle).
        - trace_ingredient_keys: <2% minor ingredients; unknown in this set are informational only.
        - use_api_fallback: if True, unknown ingredients are fetched from USDA FDC / Open Food Facts.
        - profile_context: optional dict for unknown-ingredient log and enrichment.
        Returns verdict with triggered_restrictions, uncertain_ingredients, confidence_score.
        """
        if not ingredient_strings:
            return ComplianceVerdict(
                status=VerdictStatus.UNCERTAIN,
                uncertain_ingredients=[],
                informational_ingredients=[],
                confidence_score=0.0,
                ontology_version=self._ingredients.get_version(),
            )

        trace_set = trace_ingredient_keys or set()
        resolved: List[Ingredient] = []
        resolved_is_trace: List[bool] = []  # parallel to resolved: True if ingredient was <2% minor
        uncertain_raw: List[str] = []
        informational_raw: List[str] = []  # minor <2%; display "informational only" when confidence < 1.0
        resolution_levels: List[str] = []

        for raw in ingredient_strings:
            key = (raw or "").lower().strip()
            if not key:
                continue
            is_trace = key in trace_set

            if hasattr(self._ingredients, "resolve_with_fallback") and use_api_fallback:
                ing, source, level = self._ingredients.resolve_with_fallback(
                    raw,
                    try_api=True,
                    log_unknown=not is_trace,
                    restriction_ids=restriction_ids,
                    profile_context=profile_context,
                )
                if ing is not None:
                    resolved.append(ing)
                    resolved_is_trace.append(is_trace)
                    resolution_levels.append(level)
                    if is_trace:
                        informational_raw.append(raw)
                else:
                    if is_trace:
                        logger.info(
                            "COMPLIANCE_ENGINE trace_ingredient informational (not in ontology) raw=%s key=%s",
                            raw, key,
                        )
                        informational_raw.append(raw)
                        resolution_levels.append("high")  # do not reduce confidence
                    elif source == "api":
                        # All external APIs failed: do NOT mark SAFE; mark UNCERTAIN, confidence 0.0-0.4
                        logger.info(
                            "COMPLIANCE_ENGINE api_failed uncertain raw=%s key=%s (all external lookups failed)",
                            raw, key,
                        )
                        uncertain_raw.append(raw)
                        resolution_levels.append("api_failed")
                    else:
                        uncertain_raw.append(raw)
                        resolution_levels.append("low")
                        logger.info(
                            "UNKNOWN_INGREDIENT raw=%s normalized_key=%s restriction_ids=%s",
                            raw, key, (restriction_ids or [])[:10],
                        )
            else:
                ing = self._ingredients.resolve(raw)
                if ing is None:
                    if is_trace:
                        logger.info(
                            "COMPLIANCE_ENGINE trace_ingredient informational (not in ontology) raw=%s key=%s",
                            raw, key,
                        )
                        informational_raw.append(raw)
                        resolution_levels.append("high")
                    else:
                        uncertain_raw.append(raw)
                        resolution_levels.append("low")
                        logger.info(
                            "UNKNOWN_INGREDIENT raw=%s normalized_key=%s restriction_ids=%s",
                            raw, key, (restriction_ids or [])[:10],
                        )
                else:
                    resolved.append(ing)
                    resolved_is_trace.append(is_trace)
                    resolution_levels.append("high")
                    if is_trace:
                        informational_raw.append(raw)

        if informational_raw:
            logger.info(
                "COMPLIANCE_ENGINE minor_ingredients informational_only count=%d items=%s",
                len(informational_raw), informational_raw,
            )
        if uncertain_raw:
            logger.info(
                "COMPLIANCE_ENGINE unknown_ingredients count=%d items=%s restriction_ids=%s",
                len(uncertain_raw),
                uncertain_raw,
                (restriction_ids or [])[:10],
            )

        rest_ids = self._restrictions.list_ids()
        if restriction_ids is not None:
            rest_ids = [rid for rid in restriction_ids if self._restrictions.get(rid) is not None]
        if region_scope:
            rest_ids = [
                rid for rid in rest_ids
                if self._restrictions.get(rid) and region_scope in (self._restrictions.get(rid).region_scope or [])
            ]

        triggered_restrictions: List[str] = []
        triggered_ingredients: List[str] = []
        triggered_restrictions_from_minor: set = set()
        triggered_ingredients_from_minor: set = set()
        warning_count = 0

        for restriction_id in rest_ids:
            rest = self._restrictions.get(restriction_id)
            if not rest:
                continue
            for idx, ing in enumerate(resolved):
                result, reason = self._restrictions.evaluate(ing, rest)
                if result == "FAIL":
                    triggered_restrictions.append(restriction_id)
                    triggered_ingredients.append(ing.canonical_name)
                    if idx < len(resolved_is_trace) and resolved_is_trace[idx]:
                        triggered_restrictions_from_minor.add(restriction_id)
                        triggered_ingredients_from_minor.add(ing.canonical_name)
                elif result == "WARN":
                    warning_count += 1

        triggered_restrictions = list(dict.fromkeys(triggered_restrictions))
        triggered_ingredients = list(dict.fromkeys(triggered_ingredients))

        if triggered_restrictions:
            status = VerdictStatus.NOT_SAFE
        elif uncertain_raw:
            status = VerdictStatus.UNCERTAIN
        else:
            status = VerdictStatus.SAFE

        # Minor-only trigger: all triggered restrictions came from <2% ingredients -> confidence 0.2-0.5
        triggered_only_by_minor = (
            bool(triggered_restrictions)
            and set(triggered_restrictions) <= triggered_restrictions_from_minor
        )
        has_minor = bool(informational_raw)

        confidence = compute_confidence(
            total_ingredients=len(ingredient_strings),
            resolved_count=len(resolved),
            uncertain_ingredients=uncertain_raw,
            warning_count=warning_count,
            resolution_levels=resolution_levels if len(resolution_levels) == len(ingredient_strings) else None,
            triggered_only_by_minor=triggered_only_by_minor,
            has_minor_ingredients=has_minor,
            status=status,
        )

        return ComplianceVerdict(
            status=status,
            triggered_restrictions=triggered_restrictions,
            triggered_ingredients=triggered_ingredients,
            uncertain_ingredients=uncertain_raw,
            informational_ingredients=informational_raw,
            confidence_score=round(confidence, 4),
            ontology_version=self._ingredients.get_version(),
        )
