"""IKE-2 evaluation for /api/v1/evaluate-* (Item 16 Prompt 7).

User-facing verdict is always IKE-2 (fail-closed to UNCERTAIN). Legacy
``ComplianceEngine`` and observational legacy-diff scheduling are removed.
``comparator.compare`` and ``ike2_shadow_diffs`` remain as reusable cutover
infrastructure with no current serve-path caller.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.models.verdict import ComplianceVerdict, VerdictStatus

logger = logging.getLogger(__name__)


def _run_ike2_evaluate_with_flags(
    ingredients: List[str],
    restriction_ids: Optional[List[str]],
    *,
    region_scope: Optional[str] = None,
    raw_label: Optional[str] = None,
) -> Tuple[ComplianceVerdict, List[dict]]:
    from core.bridge import _run_ike2_compliance, map_ike2_to_compliance_verdict
    from core.knowledge.ike2.shadow.runner import flags_from_compliance_inputs

    try:
        result, inputs, display_map = _run_ike2_compliance(
            ingredients,
            restriction_ids,
            prepared_decomposed=None,
            region=region_scope,
            raw_label=raw_label,
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


def evaluate_http(
    ingredients: List[str],
    restriction_ids: Optional[List[str]] = None,
    *,
    region_scope: Optional[str] = None,
    include_matrix: bool = False,
    raw_label: Optional[str] = None,
) -> Tuple[ComplianceVerdict, dict]:
    """Verdict dict source plus the sibling ike2 object (schema_version, breakdown).

    ``verdict`` at the HTTP top level stays ``ComplianceVerdict.to_dict()``.
    ``assemble``'s integer ``verdict`` lives only inside the sibling object.
    """
    from core.bridge import _profile_from_restriction_ids, _run_ike2_compliance
    from core.bridge import map_ike2_to_compliance_verdict
    from core.knowledge.ike2.breakdown import by_restriction, restriction_matrix
    from core.knowledge.ike2.response import SCHEMA_VERSION, assemble

    try:
        result, inputs, display_map = _run_ike2_compliance(
            ingredients,
            restriction_ids,
            prepared_decomposed=None,
            region=region_scope,
            raw_label=raw_label,
        )
        verdict = map_ike2_to_compliance_verdict(
            result, inputs, input_display_map=display_map
        )
        profile = _profile_from_restriction_ids(restriction_ids)
        block = assemble(inputs, result, profile, mode="b2b")
        block["by_restriction"] = by_restriction(result, restriction_ids or [])
        if include_matrix:
            block["restriction_matrix"] = restriction_matrix(result)
        return verdict, block
    except Exception:
        logger.exception(
            "IKE2_API_EVALUATE_FAILED ingredients=%s restriction_ids=%s",
            (ingredients or [])[:20],
            restriction_ids,
        )
        return ComplianceVerdict(status=VerdictStatus.UNCERTAIN), {
            "schema_version": SCHEMA_VERSION,
            "by_restriction": [],
        }


def evaluate_ingredients(
    ingredients: List[str],
    restriction_ids: Optional[List[str]] = None,
    *,
    region_scope: Optional[str] = None,
    use_api_fallback: bool = True,
    profile_context: Optional[Dict[str, Any]] = None,
    source_route: str = "api_evaluate_compliance",
) -> ComplianceVerdict:
    """Serve IKE-2 for the v1 evaluate endpoints.

    ``use_api_fallback`` / ``profile_context`` / ``source_route`` are accepted
    for request-schema compatibility but unused (legacy path removed).
    """
    _ = (use_api_fallback, profile_context, source_route)

    raw = None
    if ingredients and len(ingredients) == 1:
        raw = ingredients[0]
    elif ingredients:
        raw = ", ".join(str(x) for x in ingredients if x)
    ike2, _flags = _run_ike2_evaluate_with_flags(
        ingredients,
        restriction_ids,
        region_scope=region_scope,
        raw_label=raw,
    )
    return ike2
