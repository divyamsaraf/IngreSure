"""
LLM-powered response composer — generates human-like conversational responses
from structured compliance verdict data.

The LLM NEVER decides safety. It only formats the deterministic verdict
into natural language. Falls back to template-based response_composer on failure.

Post-generation validation catches contradictions; if found, we fall back
to the deterministic template response.
"""
import logging
import re
from typing import List, Optional, Dict, Any

import requests

from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.config import get_ollama_url, get_ollama_model, LLM_RESPONSE_TIMEOUT
from core.response_composer import INGREDIENT_REASONS

logger = logging.getLogger(__name__)

_RESPONSE_SYSTEM_PROMPT = """You are a friendly grocery safety assistant. You compose natural responses from STRUCTURED VERDICT DATA.

ABSOLUTE RULES — VIOLATION MEANS FAILURE:
1. Each ingredient has an EXACT verdict: NOT_SAFE, SAFE, or UNCERTAIN. You MUST use the EXACT same classification. NEVER change any ingredient's verdict.
2. Every NOT_SAFE ingredient MUST be described as "not suitable" / "not safe" / "restricted" / "should be avoided".
3. Every SAFE ingredient MUST be described as "fine" / "safe" / "okay" / "compatible".
4. Every UNCERTAIN ingredient MUST be described as "couldn't verify" / "uncertain" / "needs checking".
5. NEVER say a NOT_SAFE ingredient is "fine" or "safe". NEVER say a SAFE ingredient is "not suitable" or "restricted".
6. Use the EXACT REASON provided for each ingredient. Do NOT invent your own reasons.
7. Keep it concise: 2-4 sentences. Be warm but direct.
8. Use **bold** for ingredient names. No emojis. No markdown headers.
9. Do NOT add medical disclaimers unless the verdict is UNCERTAIN.
10. Mention the user's diet name naturally.
11. NEVER offer to brainstorm alternatives, suggest recipes, or provide unsolicited follow-up offers. End the response naturally after delivering the answer."""


def _call_ollama(system: str, prompt: str, timeout: int = LLM_RESPONSE_TIMEOUT) -> Optional[str]:
    """Call Ollama and return the response text, or None on failure."""
    try:
        resp = requests.post(
            get_ollama_url(),
            json={
                "model": get_ollama_model(),
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 400},
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.RequestException as e:
        logger.warning("LLM_RESPONSE ollama call failed: %s", e)
        return None


def _normalize_for_match(s: str) -> str:
    """Normalize ingredient name: lowercase, strip trailing s/es."""
    s = s.lower().strip()
    if s.endswith("es") and len(s) > 3:
        return s[:-2]
    if s.endswith("s") and len(s) > 2:
        return s[:-1]
    return s


def _get_reason(ingredient: str) -> str:
    """Get the reason for an ingredient's classification."""
    key = ingredient.lower().strip()
    reason = INGREDIENT_REASONS.get(key)
    if reason:
        return reason
    norm = _normalize_for_match(key)
    reason = INGREDIENT_REASONS.get(norm)
    if reason:
        return reason
    return "conflicts with dietary requirements"


def _build_verdict_prompt(
    verdict: ComplianceVerdict,
    profile: Any,
    ingredients: List[str],
    profile_was_updated: bool = False,
    updated_fields: Optional[Dict[str, Any]] = None,
) -> str:
    """Build a structured per-ingredient verdict table for the LLM."""
    diet = getattr(profile, "dietary_preference", "your preferences") or "your preferences"
    triggered = {_normalize_for_match(i) for i in (verdict.triggered_ingredients or [])}
    uncertain = {_normalize_for_match(i) for i in (verdict.uncertain_ingredients or [])}

    lines = [
        "=== VERDICT DATA (you MUST follow this EXACTLY) ===",
        f"Diet: {diet}",
        f"Overall: {verdict.status.value}",
        "",
        "Per-ingredient verdicts:",
    ]

    for ing in ingredients:
        norm = _normalize_for_match(ing)
        if norm in triggered:
            reason = _get_reason(ing)
            lines.append(f"  - {ing}: NOT_SAFE (reason: {reason})")
        elif norm in uncertain:
            lines.append(f"  - {ing}: UNCERTAIN (could not verify)")
        else:
            lines.append(f"  - {ing}: SAFE")

    if profile_was_updated and updated_fields:
        changes = [f"{k} -> {v}" for k, v in updated_fields.items()]
        lines.append(f"\nProfile just updated: {'; '.join(changes)}")
        lines.append("Acknowledge the profile update first.")

    lines.append("")
    lines.append("Write a natural, friendly response. Follow ALL rules in your system prompt.")
    return "\n".join(lines)


def _validate_response(
    response: str,
    triggered_ingredients: List[str],
    safe_ingredients: List[str],
) -> bool:
    """Validate the LLM response doesn't contradict the verdict."""
    resp_lower = response.lower()
    safe_words = {"fine", "safe", "okay", "compatible", "suitable for", "good for", "no issue", "perfectly"}
    unsafe_words = {"not suitable", "not safe", "restricted", "avoid", "unsuitable", "not compatible",
                    "not okay", "not fine", "cannot", "shouldn't", "should not"}

    for ing in triggered_ingredients:
        ing_lower = ing.lower()
        if ing_lower not in resp_lower:
            continue
        for sentence in re.split(r'[.!]', resp_lower):
            if ing_lower in sentence:
                if any(w in sentence for w in safe_words) and not any(w in sentence for w in unsafe_words):
                    logger.warning("LLM_VALIDATION_FAIL triggered '%s' described as safe", ing)
                    return False

    for ing in safe_ingredients:
        ing_lower = ing.lower()
        if ing_lower not in resp_lower:
            continue
        for sentence in re.split(r'[.!]', resp_lower):
            if ing_lower in sentence:
                if any(w in sentence for w in unsafe_words) and not any(w in sentence for w in safe_words):
                    logger.warning("LLM_VALIDATION_FAIL safe '%s' described as unsafe", ing)
                    return False

    return True


def llm_compose_verdict(
    verdict: ComplianceVerdict,
    profile: Any,
    ingredients: List[str],
    profile_was_updated: bool = False,
    updated_fields: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Use LLM to compose a natural response from verdict data.
    Returns None if LLM unavailable or validation fails (caller falls back to templates).
    """
    prompt = _build_verdict_prompt(verdict, profile, ingredients, profile_was_updated, updated_fields)
    response = _call_ollama(_RESPONSE_SYSTEM_PROMPT, prompt)

    if not response:
        return None

    triggered_norm = {_normalize_for_match(i) for i in (verdict.triggered_ingredients or [])}
    uncertain_norm = {_normalize_for_match(i) for i in (verdict.uncertain_ingredients or [])}
    safe_ings = [i for i in ingredients
                 if _normalize_for_match(i) not in triggered_norm
                 and _normalize_for_match(i) not in uncertain_norm]

    if not _validate_response(response, verdict.triggered_ingredients or [], safe_ings):
        logger.warning("LLM_RESPONSE validation failed, falling back to template")
        return None

    logger.info("LLM_RESPONSE success verdict=%s len=%d", verdict.status.value, len(response))
    return response


def llm_compose_greeting(profile: Any = None) -> Optional[str]:
    """Use LLM for greeting response."""
    diet = ""
    if profile and hasattr(profile, "dietary_preference"):
        diet = profile.dietary_preference or ""
    if diet and diet != "No rules":
        prompt = f"The user said hello. Their dietary profile is: {diet}. Greet them warmly and mention you can check ingredients for their {diet} diet. Keep it to 1-2 sentences. Do NOT offer recipes or alternatives."
    else:
        prompt = "The user said hello. They haven't set up a dietary profile yet. Greet them warmly and invite them to tell you their dietary preferences or ask about any ingredient. Keep it to 1-2 sentences. Do NOT offer recipes or alternatives."
    return _call_ollama(_RESPONSE_SYSTEM_PROMPT, prompt)


def llm_compose_profile_update(
    profile: Any,
    updated_fields: Dict[str, Any],
    has_ingredients: bool = False,
) -> Optional[str]:
    """Use LLM for profile update acknowledgment."""
    diet = getattr(profile, "dietary_preference", "") or ""
    changes = [f"{k}: {v}" for k, v in updated_fields.items()]
    prompt = f"The user updated their profile. Changes: {'; '.join(changes)}. Current diet: {diet}."
    if has_ingredients:
        prompt += " They also asked about ingredients (answered separately)."
    else:
        prompt += " Confirm the update warmly and invite them to ask about ingredients. Keep it to 1-2 sentences."
    return _call_ollama(_RESPONSE_SYSTEM_PROMPT, prompt)


def llm_compose_general(query: str, profile: Any = None) -> Optional[str]:
    """Use LLM for general questions / conversational responses."""
    diet = ""
    if profile and hasattr(profile, "dietary_preference"):
        diet = profile.dietary_preference or ""
    context = f" Their diet is: {diet}." if diet and diet != "No rules" else ""
    prompt = (
        f"The user asked: \"{query}\".{context} "
        f"If this is a general food/nutrition question, give a brief helpful answer. "
        f"If they didn't ask about specific ingredients, gently guide them to ask about specific ingredients so you can check safety. "
        f"Keep it to 2-3 sentences. Do NOT offer to brainstorm, suggest recipes, or suggest alternative ingredients."
    )
    return _call_ollama(_RESPONSE_SYSTEM_PROMPT, prompt)
