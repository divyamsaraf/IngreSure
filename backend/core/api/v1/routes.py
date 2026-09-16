from fastapi import APIRouter, HTTPException, Request

from core.api.v1_evaluate import evaluate_ingredients
from core.knowledge.canonicalizer import CanonicalResolver
from core.ontology.ingredient_registry import IngredientRegistry
from core.parsing.ingredient_parser import preprocess_ingredients_to_strings
from core.security.rate_limit import rate_limit, api_v1_rate_limit

from .schemas import (
    ResolveIngredientRequest,
    ResolvedIngredientResponse,
    EvaluateComplianceRequest,
    EvaluateComplianceResponse,
    EvaluateProductRequest,
    EvaluateProductResponse,
)


router = APIRouter(prefix="/api/v1", tags=["api-v1"])


@router.post("/resolve-ingredient", response_model=ResolvedIngredientResponse)
@rate_limit(api_v1_rate_limit)
def resolve_ingredient(request: Request, req: ResolveIngredientRequest) -> ResolvedIngredientResponse:
    """
    Resolve a single ingredient into the canonical Ingredient object.

    Note: This endpoint never makes compliance decisions. It only resolves facts.
    """
    registry = IngredientRegistry()
    resolver = CanonicalResolver(registry)
    res = resolver.resolve_with_fallback(
        req.name,
        try_api=req.try_api,
        log_unknown=req.log_unknown,
        restriction_ids=None,
        profile_context=None,
    )
    return ResolvedIngredientResponse(
        ingredient=res.ingredient.to_dict() if res.ingredient else None,
        source_layer=res.source_layer,
        confidence_band=res.confidence_band,
        knowledge_state=res.knowledge.state.value,
        knowledge_source=res.knowledge.source,
    )


@router.get("/ingredient/{name}", response_model=ResolvedIngredientResponse)
@rate_limit(api_v1_rate_limit)
def get_ingredient(request: Request, name: str, try_api: bool = False) -> ResolvedIngredientResponse:
    """
    Get an ingredient resolution by name.

    Defaults to try_api=False so callers can do deterministic, local-only lookups.
    """
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    registry = IngredientRegistry()
    resolver = CanonicalResolver(registry)
    res = resolver.resolve_with_fallback(name, try_api=try_api, log_unknown=False)
    return ResolvedIngredientResponse(
        ingredient=res.ingredient.to_dict() if res.ingredient else None,
        source_layer=res.source_layer,
        confidence_band=res.confidence_band,
        knowledge_state=res.knowledge.state.value,
        knowledge_source=res.knowledge.source,
    )


@router.post("/evaluate-compliance", response_model=EvaluateComplianceResponse)
@rate_limit(api_v1_rate_limit)
def evaluate_compliance(request: Request, req: EvaluateComplianceRequest) -> EvaluateComplianceResponse:
    """
    Deterministically evaluate ingredients against restriction_ids.

    Engine selection is gated by ``IKE2_MODE`` (legacy | shadow | primary).
    See ``core.api.v1_evaluate.evaluate_ingredients`` and Item 16 cutover spec.
    Response shape remains ``ComplianceVerdict.to_dict()``.
    """
    verdict = evaluate_ingredients(
        req.ingredients,
        req.restriction_ids or None,
        region_scope=req.region_scope,
        use_api_fallback=req.use_api_fallback,
        profile_context=req.profile_context,
        source_route="api_evaluate_compliance",
    )
    return EvaluateComplianceResponse(verdict=verdict.to_dict())


@router.post("/evaluate-product", response_model=EvaluateProductResponse)
@rate_limit(api_v1_rate_limit)
def evaluate_product(request: Request, req: EvaluateProductRequest) -> EvaluateProductResponse:
    """
    Parse an ingredient label text into atomic ingredients, then evaluate compliance.

    Parsing is unchanged; evaluation uses the same ``IKE2_MODE``-gated path as
    ``/evaluate-compliance``.
    """
    parsed = preprocess_ingredients_to_strings(req.ingredients_text)
    verdict = evaluate_ingredients(
        parsed,
        req.restriction_ids or None,
        use_api_fallback=req.use_api_fallback,
        profile_context=req.profile_context,
        source_route="api_evaluate_product",
    )
    return EvaluateProductResponse(parsed_ingredients=parsed, verdict=verdict.to_dict())

