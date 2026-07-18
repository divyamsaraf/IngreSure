"""Helpers for IKE-2 golden audit matrix tests."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.bridge import profile_to_restriction_ids, run_new_engine_chat
from core.normalization.normalizer import substance_key
from core.response_composer import build_ingredient_audit_payload, compose_verdict_explanation


def _profile(diet: str, allergens: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "dietary_preference": diet,
        "allergens": list(allergens or []),
    }


def _item_substance_keys(name: str) -> set[str]:
    keys = {substance_key(name), name.lower().strip()}
    if " · " in name:
        keys.add(substance_key(name.split(" · ", 1)[1]))
    return {k for k in keys if k}


def _matches_input(ing: str, display: str, item_keys: set[str]) -> bool:
    ing_key = ing.lower().strip()
    ing_sk = substance_key(ing) or ing_key
    display_lower = display.lower()
    return (
        ing_key in display_lower
        or ing_sk in item_keys
        or any(ing_key in k or k in ing_key for k in item_keys)
    )


def run_audit_case(
    diet: str,
    ingredients: List[str],
    allergens: Optional[List[str]] = None,
) -> dict:
    profile = _profile(diet, allergens)
    restriction_ids = profile_to_restriction_ids(profile)
    verdict = run_new_engine_chat(
        ingredients,
        user_profile=profile,
        restriction_ids=restriction_ids,
        use_api_fallback=False,
    )
    explanation = compose_verdict_explanation(verdict, profile, ingredients)
    payload = build_ingredient_audit_payload(
        verdict=verdict,
        profile=profile,
        ingredients=ingredients,
        explanation_text=explanation,
    )

    bucket_by_name: Dict[str, str] = {}
    reason_category_by_name: Dict[str, Optional[str]] = {}
    reasons_parts: List[str] = []

    for group in payload.get("groups", []):
        status = group.get("status", "")
        for item in group.get("items", []):
            display = item.get("name", "")
            reason = item.get("reason")
            if reason:
                reasons_parts.append(str(reason))
            cat = item.get("reason_category")
            item_keys = _item_substance_keys(display)

            for ing in ingredients:
                if _matches_input(ing, display, item_keys):
                    ing_key = ing.lower().strip()
                    bucket_by_name[ing_key] = status
                    reason_category_by_name[ing_key] = cat

            display_key = display.lower()
            bucket_by_name[display_key] = status
            reason_category_by_name[display_key] = cat

    triggered = {x.lower() for x in (verdict.triggered_ingredients or [])}
    uncertain = {x.lower() for x in (verdict.uncertain_ingredients or [])}
    for ing in ingredients:
        key = ing.lower().strip()
        if key in bucket_by_name:
            continue
        if key in triggered or any(key in t or t in key for t in triggered):
            bucket_by_name[key] = "avoid"
            reason_category_by_name.setdefault(key, None)
        elif key in uncertain or any(key in u or u in key for u in uncertain):
            bucket_by_name[key] = "depends"
            reason_category_by_name.setdefault(key, None)
        else:
            bucket_by_name[key] = "safe"
            reason_category_by_name.setdefault(key, None)

    return {
        "bucket_by_name": bucket_by_name,
        "reason_category_by_name": reason_category_by_name,
        "explanation": payload.get("explanation") or explanation,
        "triggered_restrictions": list(verdict.triggered_restrictions or []),
        "reasons_text": " ".join(reasons_parts),
    }
