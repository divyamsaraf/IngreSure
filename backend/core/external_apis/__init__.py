"""
External food DB connectors for ingredient enrichment.
USDA FoodData Central and Open Food Facts (free).
"""
from .base import EnrichmentResult, ConfidenceLevel
from .usda_fdc import fetch_usda_fdc
from .open_food_facts import fetch_open_food_facts
from .fetcher import fetch_ingredient_from_apis, enrich_unknown_ingredient

__all__ = [
    "EnrichmentResult",
    "ConfidenceLevel",
    "fetch_usda_fdc",
    "fetch_open_food_facts",
    "fetch_ingredient_from_apis",
    "enrich_unknown_ingredient",
]
