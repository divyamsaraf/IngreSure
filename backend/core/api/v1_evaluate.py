"""IKE2_MODE-gated evaluation for /api/v1/evaluate-* (Item 16).

Chat already uses IKE-2 as primary via ``bridge.run_new_engine_chat``; leave that
path alone. This module only routes the two programmatic evaluate endpoints.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.config import get_ike2_mode
from core.models.verdict import ComplianceVerdict, VerdictStatus

logger = logging.getLogger(__name__)


def _run_legacy_evaluate(
    ingredients: List[str],
    restriction_ids: Optional[List[str]],
    *,
    region_scope: Optional[str] = None,
    use_api_fallback: bool = True,
    profile_context: Optional[Dict[str, Any]] = None,
) -> ComplianceVerdict:
    from core.evaluation.compliance_engine import ComplianceEngine

    return ComplianceEngine().evaluate(
        ingredient_strings=ingredients,
        restriction_ids=restriction_ids or None,
        region_scope=region_scope,
        use_api_fallback=use_api_fallback,
        profile_context=profile_context,
    )


def _run_ike2_evaluate_with_flags(
    ingredients: List[str],
    restriction_ids: Optional[List[str]],
    *,
    region_scope: Optional[str] = None,
) -> Tuple[ComplianceVerdict, List[dict]]:
    from core.bridge import _run_ike2_compliance, map_ike2_to_compliance_verdict
    from core.knowledge.ike2.shadow.runner import flags_from_compliance_inputs

    try:
        result, inputs, display_map = _run_ike2_compliance(
            ingredients,
            restriction_ids,
            prepared_decomposed=None,
            region=region_scope,
        )
        verdict = map_ike2_to_compliance_verdict(
            result, inputs, input_display_map=display_map
        )
        return verdict, flags_from_compliance_inputs(inputs)
    except Exception:
        logger.exception(
            "IKE2_API_EVALUATE_FAILED ingredients=%s restriction_ids=%s",
            (ingredients or [])[:20],
            restriction_ids,
        )
        return ComplianceVerdict(status=VerdictStatus.UNCERTAIN), []


def _run_ike2_evaluate(
    ingredients: List[str],
    restriction_ids: Optional[List[str]],
    *,
    region_scope: Optional[str] = None,
) -> ComplianceVerdict:
    verdict, _flags = _run_ike2_evaluate_with_flags(
        ingredients, restriction_ids, region_scope=region_scope
    )
    return verdict


def _log_shadow_diff(
    legacy_status: str,
    ike2_status: str,
    ingredients: List[str],
    restriction_ids: Optional[List[str]],
    *,
    ingredient_flags: Optional[List[dict]] = None,
    source_route: str = "api_evaluate_compliance",
) -> None:
    """Compare and persist mismatches to ``ike2_shadow_diffs`` (fail-safe)."""
    try:
        from core.knowledge.ike2.shadow.comparator import compare
        from core.knowledge.ike2.shadow.runner import _log_diff

        raw_input = ", ".join(ingredients or [])
        diff = compare(
            legacy_status,
            ike2_status,
            raw_input,
            restriction_ids=restriction_ids,
            ingredient_flags=ingredient_flags,
        )
        diff["source_route"] = source_route
        logger.info(
            "IKE2_API_DIFF legacy=%s ike2=%s match=%s false_safe_regression=%s "
            "source_route=%s restriction_ids=%s ingredients=%s",
            diff["legacy_verdict"],
            diff["ike2_verdict"],
            diff["match"],
            diff["false_safe_regression"],
            source_route,
            restriction_ids,
            raw_input[:200] if raw_input else "",
        )
        if not diff["match"]:
            _log_diff(diff)
    except Exception:
        logger.warning("IKE-2 API shadow diff failed; served result unaffected", exc_info=True)


def _schedule_primary_legacy_diff(
    ingredients: List[str],
    restriction_ids: Optional[List[str]],
    primary_status: str,
    *,
    ingredient_flags: Optional[List[dict]] = None,
    source_route: str = "api_evaluate_compliance",
) -> None:
    """Background legacy comparison when serving IKE-2 (same pattern as chat)."""
    try:
        from core.bridge import _schedule_legacy_diff

        _schedule_legacy_diff(
            ingredients,
            restriction_ids,
            primary_status,
            ingredient_flags=ingredient_flags,
            source_route=source_route,
        )
    except Exception:
        logger.warning("IKE-2 API primary legacy-diff schedule failed", exc_info=True)


def evaluate_ingredients(
    ingredients: List[str],
    restriction_ids: Optional[List[str]] = None,
    *,
    region_scope: Optional[str] = None,
    use_api_fallback: bool = True,
    profile_context: Optional[Dict[str, Any]] = None,
    source_route: str = "api_evaluate_compliance",
) -> ComplianceVerdict:
    """Route evaluation by ``IKE2_MODE`` for the v1 evaluate endpoints.

    | Mode     | Served result | Side effect                                      |
    |----------|---------------|--------------------------------------------------|
    | legacy   | ComplianceEngine | none                                          |
    | shadow   | ComplianceEngine | IKE-2 computed + diff logged to ike2_shadow_diffs |
    | primary  | IKE-2         | legacy diff scheduled in background              |

    ``use_api_fallback`` / ``profile_context`` are accepted for backward
    compatibility; they only affect the legacy engine path (Item 16 Option A).
    """
    mode = get_ike2_mode()

    if mode == "legacy":
        return _run_legacy_evaluate(
            ingredients,
            restriction_ids,
            region_scope=region_scope,
            use_api_fallback=use_api_fallback,
            profile_context=profile_context,
        )

    if mode == "shadow":
        legacy = _run_legacy_evaluate(
            ingredients,
            restriction_ids,
            region_scope=region_scope,
            use_api_fallback=use_api_fallback,
            profile_context=profile_context,
        )
        ike2, flags = _run_ike2_evaluate_with_flags(
            ingredients,
            restriction_ids,
            region_scope=region_scope,
        )
        _log_shadow_diff(
            legacy.status.value,
            ike2.status.value,
            ingredients,
            restriction_ids,
            ingredient_flags=flags,
            source_route=source_route,
        )
        return legacy

    # primary
    ike2, flags = _run_ike2_evaluate_with_flags(
        ingredients,
        restriction_ids,
        region_scope=region_scope,
    )
    _schedule_primary_legacy_diff(
        ingredients,
        restriction_ids,
        ike2.status.value,
        ingredient_flags=flags,
        source_route=source_route,
    )
    return ike2
