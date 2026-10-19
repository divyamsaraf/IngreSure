"""
Whether an ingredient resolution is trusted enough for compliance verdicts.

Conservative policy:
- Static ontology / truth anchor: trusted (caller already on curated path).
- Bulk ETL sources (USDA, INFOODS, IFCT, FSSAI, …): never trusted for firm
  SAFE — absence of a flag in a bulk dump is not evidence (same trap as
  asserted_flags default-false, at the verdict level).
- Unknown / NULL / missing group provenance: **untrusted** (fail-closed).
  Do not treat absent ``source`` as curated.
- Any ``*inferred*`` / ``*category_derived*`` marker: untrusted.
- Dynamic/API medium/low confidence: never trusted for marking Safe.
"""
from core.ontology.ingredient_schema import Ingredient

# Provenance labels on ike2_ingredient_groups.source (and dump aliases).
# Firm SAFE requires curated evidence (ontology / truth anchor / e-number).
_BULK_SAFE_CEILING_SOURCES = frozenset({
    "usda",
    "usda_fdc",
    "infoods",
    "infoods_anfood",
    "anfood",
    "ifct",
    "fssai",
    "openfoodfacts",
    "open_food_facts",
    "off",
    "pubchem",
    "chebi",
    "wikidata",
    "foodex2",
    "enrichment_api",
    "produce_catalog",
    "animal_catalog",
})

# Only these group.source values may firm-SAFE on the DB path.
# Everything else (including NULL/missing) fails closed.
_TRUSTED_GROUP_SOURCES = frozenset({
    "ontology",
    "human",
    "e_number_catalog",
    "truth_anchor",
})


def _is_cacheable(result) -> bool:
    """Only cache successful high/medium confidence resolutions."""
    if result is None:
        return False
    if hasattr(result, "confidence_band"):
        return result.confidence_band in ("high", "medium")
    if hasattr(result, "ingredient") and result.ingredient is None:
        return False
    return True


def _uncertainty_tokens(ing) -> list[str]:
    raw = getattr(ing, "uncertainty_flags", None)
    if raw is None and isinstance(ing, dict):
        raw = ing.get("uncertainty_flags")
    return [str(f or "") for f in (raw or [])]


def _group_source(ing) -> str:
    raw = getattr(ing, "source", None)
    if raw is None and isinstance(ing, dict):
        raw = ing.get("source")
    if raw:
        return str(raw).strip().lower()
    # Alias-resolution view historically omitted ``source``; fall back to
    # ``classification_method`` like ``bulk:fssai`` / ``bulk:usda``.
    # If both are missing, return "" — caller must fail closed.
    method = getattr(ing, "classification_method", None)
    if method is None and isinstance(ing, dict):
        method = ing.get("classification_method")
    method_s = str(method or "").strip().lower()
    if method_s.startswith("bulk:"):
        return method_s.split(":", 1)[1]
    return ""


def is_trusted_for_compliance(
    ing: Ingredient,
    source: str,
    level: str,
) -> bool:
    """True when this resolution may drive Avoid or Safe verdicts.

    SAFE ceiling is a property of the *source* for bulk dumps (marker or not).
    Missing/NULL provenance is untrusted. Item 42 still lets allergy/medical
    FAIL stand when untrusted.
    """
    if source == "static":
        return True
    group_src = _group_source(ing)
    channel = str(source or "").strip().lower()
    if group_src in _BULK_SAFE_CEILING_SOURCES:
        return False
    if channel in _BULK_SAFE_CEILING_SOURCES:
        return False
    flags = _uncertainty_tokens(ing)
    if any("inferred" in f or "category_derived" in f for f in flags):
        return False
    if channel in ("api", "dynamic"):
        return level == "high"
    # DB / unknown channel: allowlist only. NULL/missing/unknown → untrusted.
    if group_src not in _TRUSTED_GROUP_SOURCES:
        return False
    return level == "high"
