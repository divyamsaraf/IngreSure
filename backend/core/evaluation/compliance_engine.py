"""
Deterministic compliance engine. Single pipeline for scan and chat.
Resolve: 1) static ontology 2) dynamic ontology 3) external API if enabled.
Unknown ingredient -> UNCERTAIN; trace/minor ingredients optionally informational only.
Ingredients are resolved in parallel when multiple are present.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Set, Tuple
import logging

from core.ontology.ingredient_registry import IngredientRegistry
from core.ontology.ingredient_schema import Ingredient
from core.restrictions.restriction_registry import RestrictionRegistry
from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.evaluation.confidence import compute_confidence
from core.knowledge.canonicalizer import CanonicalResolver

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
        self._resolver = CanonicalResolver(self._ingredients)
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
        # Build list of (index, raw, key, is_trace) for items we will resolve
        items: List[Tuple[int, str, str, bool]] = []
        for i, raw in enumerate(ingredient_strings):
            key = (raw or "").lower().strip()
            if not key:
                continue
            items.append((i, raw, key, key in trace_set))

        def resolve_one(item: Tuple[int, str, str, bool]) -> Tuple[int, str, str, bool, Optional[Ingredient], str, str]:
            idx, raw, key, is_trace = item
            if use_api_fallback:
                res = self._resolver.resolve_with_fallback(
                    raw,
                    try_api=True,
                    log_unknown=not is_trace,
                    restriction_ids=restriction_ids,
                    profile_context=profile_context,
                )
                ing = res.ingredient
                source = getattr(res, "source_layer", "unknown")
                level = (res.confidence_band or "low") if hasattr(res, "confidence_band") else "low"
                return (idx, raw, key, is_trace, ing, source, level)
            ing = self._ingredients.resolve(raw)
            return (idx, raw, key, is_trace, ing, "static" if ing else "unknown", "high" if ing else "low")

        resolved: List[Ingredient] = []
        resolved_raw: List[str] = []
        resolved_is_trace: List[bool] = []
        uncertain_raw: List[str] = []
        informational_raw: List[str] = []
        resolution_levels: List[str] = []

        max_workers = min(8, max(1, len(items)))
        if len(items) <= 1:
            results_ordered = [resolve_one(it) for it in items]
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(resolve_one, it): it for it in items}
                results_by_idx: Dict[int, Tuple[int, str, str, bool, Optional[object], str, str]] = {}
                for fut in as_completed(futures):
                    t = fut.result()
                    results_by_idx[t[0]] = t
                results_ordered = [results_by_idx[i] for i in sorted(results_by_idx)]

        for idx, raw, key, is_trace, ing, source, level in results_ordered:
            if use_api_fallback:
                if ing is not None:
                    resolved.append(ing)
                    resolved_raw.append(raw)
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
                        resolution_levels.append("high")
                    elif source == "api":
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
                    resolved_raw.append(raw)
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
        triggered_ingredient_to_input: Dict[str, str] = {}  # canonical -> raw user input for display
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
                    if ing.canonical_name not in triggered_ingredient_to_input and idx < len(resolved_raw):
                        triggered_ingredient_to_input[ing.canonical_name] = resolved_raw[idx]
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
            triggered_ingredient_to_input=triggered_ingredient_to_input or None,
            uncertain_ingredients=uncertain_raw,
            informational_ingredients=informational_raw,
            confidence_score=round(confidence, 4),
            ontology_version=self._ingredients.get_version(),
        )
