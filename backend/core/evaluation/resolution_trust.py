"""
Whether an ingredient resolution is trusted enough for compliance verdicts.

Conservative policy:
- Static ontology: always trusted.
- Dynamic/API with *_inferred flags: never trusted (PubChem/ChEBI guesses).
- API medium/low confidence: never trusted for marking Safe.
"""
from core.ontology.ingredient_schema import Ingredient


def _is_cacheable(result) -> bool:
    """Only cache successful high/medium confidence resolutions."""
    if result is None:
        return False
    if hasattr(result, "confidence_band"):
        return result.confidence_band in ("high", "medium")
    if hasattr(result, "ingredient") and result.ingredient is None:
        return False
    return True


def is_trusted_for_compliance(
    ing: Ingredient,
    source: str,
    level: str,
) -> bool:
    """True when this resolution may drive Avoid or Safe verdicts."""
    if source == "static":
        return True
    flags = ing.uncertainty_flags or []
    if any("inferred" in (f or "") for f in flags):
        return False
    if source in ("api", "dynamic"):
        return level == "high"
    return level == "high"
