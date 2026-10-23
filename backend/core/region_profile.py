"""Region profile is defaults only; allergen detection uses the union.

The profile supplies vocabulary aliases, emergency numbers, and display
text. It never narrows which allergen families are detected. Unknown
region shows the generic emergency list rather than silently applying
one country's numbers.
"""
from __future__ import annotations

from core.emergency import NUMBERS, generic_guidance, number_for_region

# Union of allergen/medical restriction ids used for detection in every region.
UNION_ALLERGEN_IDS: tuple[str, ...] = (
    "peanut_allergy",
    "tree_nut_allergy",
    "soy_allergy",
    "sesame_allergy",
    "fish_allergy",
    "shellfish_allergy",
    "mustard_allergy",
    "lupin_allergy",
    "celery_allergy",
    "onion_allergy",
    "garlic_allergy",
    "gluten_free",
    "celiac_strict",
    "lactose_free",
    "dairy_free",
    "egg_free",
    "sulfite_sensitive",
)

# Onboarding order (owner decision): India, USA, Canada, UK, AU/NZ, EU-by-language, UAE.
ONBOARDING_ORDER = (
    "IN",
    "US",
    "CA",
    "GB",
    "AU",
    "NZ",
    "EU",
    "AE",
)

# Display defaults only — not detection filters.
DEFAULTS: dict[str, dict] = {
    "IN": {"emergency": "112", "label_languages": ("en", "hi")},
    "US": {"emergency": "911", "label_languages": ("en",)},
    "CA": {"emergency": "911", "label_languages": ("en", "fr")},
    "GB": {"emergency": "999", "label_languages": ("en",)},
    "UK": {"emergency": "999", "label_languages": ("en",)},
    "AU": {"emergency": "000", "label_languages": ("en",)},
    "NZ": {"emergency": "111", "label_languages": ("en",)},
    "EU": {"emergency": "112", "label_languages": ("en",)},
    "AE": {"emergency": "998", "label_languages": ("ar", "en")},
}


def allergen_detection_ids(region: str | None = None) -> tuple[str, ...]:
    """Union of allergen restriction ids. ``region`` is ignored on purpose."""
    del region
    return UNION_ALLERGEN_IDS


def emergency_message(region: str | None) -> str:
    number = number_for_region(region)
    if not number:
        return generic_guidance()
    code = (region or "").strip().upper()
    return (
        f"If this is a medical emergency, stop using this app and call {number} "
        "now (or your local emergency number). I am not emergency services and I will "
        "not evaluate ingredients while you may need urgent care."
        + (f" [{code}]" if code in NUMBERS else "")
    )


def defaults_for(region: str | None) -> dict:
    if not region:
        return {"emergency": None, "label_languages": ()}
    return dict(DEFAULTS.get(region.strip().upper()) or {"emergency": None, "label_languages": ()})
