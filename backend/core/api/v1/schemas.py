from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class ResolveIngredientRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Raw ingredient name to resolve")
    try_api: bool = Field(default=True, description="Allow external API fallback if not found locally")
    log_unknown: bool = Field(default=True, description="Log unknown ingredient when not resolved")


class ResolvedIngredientResponse(BaseModel):
    ingredient: Optional[Dict[str, Any]] = None
    source_layer: str
    confidence_band: Optional[str] = None
    knowledge_state: str
    knowledge_source: str


class EvaluateComplianceRequest(BaseModel):
    ingredients: List[str] = Field(default_factory=list)
    restriction_ids: List[str] = Field(default_factory=list)
    region_scope: Optional[str] = None
    use_api_fallback: bool = True
    profile_context: Optional[Dict[str, Any]] = None


class EvaluateComplianceResponse(BaseModel):
    verdict: Dict[str, Any]


class EvaluateProductRequest(BaseModel):
    product_name: Optional[str] = None
    ingredients_text: str = Field(..., min_length=1, description="Raw ingredient label text")
    restriction_ids: List[str] = Field(default_factory=list)
    use_api_fallback: bool = True
    profile_context: Optional[Dict[str, Any]] = None


class EvaluateProductResponse(BaseModel):
    parsed_ingredients: List[str]
    verdict: Dict[str, Any]

