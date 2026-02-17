"""
Confidence score from resolved vs uncertain and conditional flags.
Weights: ontology match = high, API validated = medium, unknown = low.
Minor ingredients: violation only from minor -> 0.2-0.5; safe with minor -> 0.2-1.0.
"""
from typing import List, Optional, Any

# Avoid circular import; caller can pass status for minor-ingredient bands
_VerdictStatus = Any


def compute_confidence(
    total_ingredients: int,
    resolved_count: int,
    uncertain_ingredients: List[str],
    warning_count: int = 0,
    resolution_levels: Optional[List[str]] = None,
    triggered_only_by_minor: bool = False,
    has_minor_ingredients: bool = False,
    status: Any = None,
) -> float:
    """
    confidence = max(0, effective_ratio - uncertainty_penalty - conditional_penalty)
    - If resolution_levels provided: effective = sum(high=1.0, medium=0.7, low=0, api_failed=0.35) / total.
    - uncertainty_penalty = len(uncertain_ingredients) * 0.1
    - If NOT_SAFE and only minor ingredients triggered: clamp to [0.2, 0.5].
    - If SAFE and has minor ingredients: floor 0.2 (confidence 0.2-1.0).
    """
    if total_ingredients <= 0:
        return 0.0
    if resolution_levels is not None and len(resolution_levels) == total_ingredients:
        level_scores = {"high": 1.0, "medium": 0.7, "low": 0.0, "api_failed": 0.35}
        effective = sum(level_scores.get(l, 0.0) for l in resolution_levels)
        effective_ratio = effective / total_ingredients
        has_api_failed = "api_failed" in resolution_levels
    else:
        effective_ratio = resolved_count / total_ingredients
        has_api_failed = False
    uncertainty_penalty = len(uncertain_ingredients) * 0.1
    conditional_penalty = warning_count * 0.05
    base = max(0.0, effective_ratio - uncertainty_penalty - conditional_penalty)

    # When any ingredient had all external lookups fail: UNCERTAIN, confidence 0.0-0.4
    if has_api_failed:
        base = min(0.4, base)

    # Minor ingredient bands: violation only from <2% -> 0.2-0.5; safe with minor -> 0.2-1.0
    status_val = getattr(status, "value", None) or str(status) if status is not None else None
    if triggered_only_by_minor and status_val == "NOT_SAFE":
        return round(min(0.5, max(0.2, base)), 4)
    if has_minor_ingredients and status_val == "SAFE":
        return round(max(0.2, base), 4)
    return round(base, 4)
