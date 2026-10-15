import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from core.api.v1_evaluate import evaluate_http
from core.bridge import contradictory_diet_pair
from core.knowledge.ike2.resolve_response import map_ike2_to_resolved_response
from core.knowledge.ike2.resolver import resolve as ike2_resolve
from core.parsing.ingredient_parser import preprocess_ingredients_to_strings
from core.security.rate_limit import api_v1_rate_limit, rate_limit, require_b2b_api_key

from .schemas import (
    ResolveIngredientRequest,
    ResolvedIngredientResponse,
    EvaluateComplianceRequest,
    EvaluateComplianceResponse,
    EvaluateProductRequest,
    EvaluateProductResponse,
)


router = APIRouter(
    prefix="/api/v1",
    tags=["api-v1"],
    dependencies=[Depends(require_b2b_api_key)],
)
logger = logging.getLogger(__name__)


def _resolve_facts(name: str, *, try_api: bool) -> ResolvedIngredientResponse:
    """IKE-2 fact lookup. ``try_api`` / ``log_unknown`` do not change behavior:
    enrichment is offline (Items 18+23) and L5 always enqueues.
    """
    if try_api:
        logger.debug("resolve try_api ignored (IKE-2; enrichment is offline): %s", name[:80])
    payload = map_ike2_to_resolved_response(ike2_resolve(name, None))
    return ResolvedIngredientResponse(**payload)


@router.post("/resolve-ingredient", response_model=ResolvedIngredientResponse)
@rate_limit(api_v1_rate_limit)
def resolve_ingredient(request: Request, req: ResolveIngredientRequest) -> ResolvedIngredientResponse:
    """
    Resolve a single ingredient into canonical facts (no compliance decision).

    Served by IKE-2 (Item 33). ``try_api`` and ``log_unknown`` are accepted and ignored.
    """
    return _resolve_facts(req.name, try_api=req.try_api)


@router.get("/ingredient/{name}", response_model=ResolvedIngredientResponse)
@rate_limit(api_v1_rate_limit)
def get_ingredient(request: Request, name: str, try_api: bool = False) -> ResolvedIngredientResponse:
    """
    Get an ingredient resolution by name (IKE-2, Item 33).

    ``try_api`` is accepted and ignored; lookups stay on local tiers.
    """
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    return _resolve_facts(name, try_api=try_api)


@router.post("/evaluate-compliance", response_model=EvaluateComplianceResponse)
@rate_limit(api_v1_rate_limit)
def evaluate_compliance(request: Request, req: EvaluateComplianceRequest) -> EvaluateComplianceResponse:
    """
    Deterministically evaluate ingredients against restriction_ids.

    Served engine is IKE-2 (Item 16 Prompt 7). ``verdict`` remains
    ``ComplianceVerdict.to_dict()``. The sibling ``ike2`` object carries
    ``schema_version`` and the per-restriction breakdown.
    """
    ids = req.restriction_ids or []
    pair = contradictory_diet_pair(ids)
    if pair:
        raise HTTPException(
            status_code=400,
            detail=f"{pair[0]} and {pair[1]} cannot be combined",
        )
    verdict, block = evaluate_http(
        req.ingredients,
        ids,
        region_scope=req.region_scope,
        include_matrix=req.include_restriction_matrix,
    )
    _ = (req.use_api_fallback, req.profile_context)
    return EvaluateComplianceResponse(verdict=verdict.to_dict(), ike2=block)


@router.post("/evaluate-product", response_model=EvaluateProductResponse)
@rate_limit(api_v1_rate_limit)
def evaluate_product(request: Request, req: EvaluateProductRequest) -> EvaluateProductResponse:
    """
    Parse an ingredient label text into atomic ingredients, then evaluate compliance.

    Parsing is unchanged; evaluation uses the same IKE-2 path as
    ``/evaluate-compliance`` (Item 16 Prompt 7).
    """
    parsed = preprocess_ingredients_to_strings(req.ingredients_text)
    ids = req.restriction_ids or []
    pair = contradictory_diet_pair(ids)
    if pair:
        raise HTTPException(
            status_code=400,
            detail=f"{pair[0]} and {pair[1]} cannot be combined",
        )
    verdict, block = evaluate_http(
        parsed,
        ids,
        include_matrix=req.include_restriction_matrix,
    )
    _ = (req.use_api_fallback, req.profile_context)
    return EvaluateProductResponse(
        parsed_ingredients=parsed, verdict=verdict.to_dict(), ike2=block
    )

