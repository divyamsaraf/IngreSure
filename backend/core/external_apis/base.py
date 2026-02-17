"""
Types and helpers for external API enrichment.
"""
from dataclasses import dataclass
from typing import Optional, Literal

from core.ontology.ingredient_schema import Ingredient

ConfidenceLevel = Literal["high", "medium", "low"]


@dataclass
class EnrichmentResult:
    """Result of fetching an ingredient from an external API."""
    ingredient: Optional[Ingredient]
    confidence: ConfidenceLevel
    source: str  # "usda_fdc" | "open_food_facts"
    raw_response_summary: str = ""  # for logging
