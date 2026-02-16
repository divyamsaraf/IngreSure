"""
Confidence score from resolved vs uncertain and conditional flags.
No static "High"; formula only.
"""
from typing import List


def compute_confidence(
    total_ingredients: int,
    resolved_count: int,
    uncertain_ingredients: List[str],
    warning_count: int = 0,
) -> float:
    """
    confidence = max(0, resolved_ratio - uncertainty_penalty - conditional_penalty)
    - resolved_ratio = resolved_ingredients / total_ingredients (0 if total 0)
    - uncertainty_penalty = len(uncertain_ingredients) * 0.1
    - conditional_penalty = warning_count * 0.05
    """
    if total_ingredients <= 0:
        return 0.0
    resolved_ratio = resolved_count / total_ingredients
    uncertainty_penalty = len(uncertain_ingredients) * 0.1
    conditional_penalty = warning_count * 0.05
    return max(0.0, resolved_ratio - uncertainty_penalty - conditional_penalty)
