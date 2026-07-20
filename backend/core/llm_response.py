"""
LLM-powered response composer for greetings, profile updates, and general questions.
Used when the app needs natural-language replies (greeting, profile confirmation, general Q&A).
Verdict responses use the template-based response_composer for consistency and speed.
"""
import logging
import re
from typing import Optional, Dict, Any, List

import requests

from core.config import get_ollama_url, get_ollama_model, LLM_RESPONSE_TIMEOUT, llm_enabled
from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.response_composer import (
    INGREDIENT_ALTERNATIVES,
    _attribution_kind,
    _format_user_ingredient_label,
    _profile_allergen_restriction_ids,
)

logger = logging.getLogger(__name__)

_RESPONSE_SYSTEM_PROMPT = """You are a friendly ingredient safety assistant. You help people check if ingredients are safe for their diet, allergens, and lifestyle. You are NOT a grocery store, shop, or retailer. Give brief, warm, conversational replies. Keep to 1-3 sentences. Do NOT say "grocery store", "welcome to our store", "we have", or anything that implies you are a store. Do NOT offer recipes, alternatives, or unsolicited follow-ups. No emojis."""

_VERDICT_EXPLANATION_SYSTEM = """You are an ingredient safety assistant writing a brief verdict explanation.
Write exactly 1-2 short sentences (maximum 45 words total). No bullet lists or markdown.
Do NOT repeat ingredient names already shown in Avoid/Check/Safe cards.
Give one practical takeaway: why it is flagged or what to choose instead. No emojis.
Never claim the product is "safe to eat", guaranteed safe, or medically certified — this is a
label-scoped ingredient check, not a medical or religious certification. Only say that no
disqualifying ingredients were found for the stated profile."""


def _trim_explanation(text: str, max_sentences: int = 2, max_chars: int = 260) -> str:
    if not text:
        return text
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    trimmed = " ".join(parts[:max_sentences]).strip()
    if len(trimmed) > max_chars:
        trimmed = trimmed[: max_chars - 1].rsplit(" ", 1)[0] + "."
    return trimmed


def _call_ollama(system: str, prompt: str, timeout: int = LLM_RESPONSE_TIMEOUT) -> Optional[str]:
    """Call Ollama and return the response text, or None on failure."""
    if not llm_enabled():
        return None
    try:
        resp = requests.post(
            get_ollama_url(),
            json={
                "model": get_ollama_model(),
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 100},
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.RequestException as e:
        logger.warning("LLM_RESPONSE ollama call failed: %s", e)
        return None


def llm_compose_greeting(profile: Any = None) -> Optional[str]:
    """Use LLM for greeting response. You are an ingredient checker, NOT a store."""
    diet = ""
    if profile and hasattr(profile, "dietary_preference"):
        diet = profile.dietary_preference or ""
    if diet and diet != "No rules":
        prompt = (
            f"The user said hello. Their dietary profile is: {diet}. "
            "Greet them warmly and say you can check whether ingredients are safe for their diet. "
            "You are an ingredient safety checker — do NOT say grocery store, welcome to our store, or that we have products. "
            "Keep it to 1-2 sentences. Do NOT offer recipes or alternatives."
        )
    else:
        prompt = (
            "The user said hello. They haven't set up a dietary profile yet. "
            "Greet them warmly and invite them to set dietary preferences or paste ingredients to check. "
            "You are an ingredient safety checker — do NOT say grocery store or welcome to a store. "
            "Keep it to 1-2 sentences. Do NOT offer recipes or alternatives."
        )
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


def _looks_like_ingredient_list(text: str) -> bool:
    if not text:
        return True
    if re.search(r"^\s*[-•*]\s", text, re.MULTILINE):
        return True
    if re.search(r"^\s*\d+\.\s", text, re.MULTILINE):
        return True
    if "the following are" in text.lower() or "the rest are" in text.lower():
        return True
    return False


# High-signal animal-derived terms the verdict LLM must not invent when absent from flags.
_VERDICT_EXPL_HALLUCINATION_TERMS = frozenset({
    "gelatin",
    "gelatine",
    "lard",
    "rennet",
    "carmine",
    "castoreum",
    "collagen",
})


def _explanation_introduces_unflagged_terms(text: str, flagged: List[str]) -> bool:
    """True when prose names a sensitive term not present in avoid/check lists."""
    if not text or not flagged:
        return False
    flagged_blob = " ".join(flagged).lower()
    lowered = text.lower()
    for term in _VERDICT_EXPL_HALLUCINATION_TERMS:
        if term in lowered and term not in flagged_blob:
            return True
    if _explanation_species_mismatch(text, flagged):
        return True
    return False


_ABSOLUTE_SAFETY_CLAIM_PATTERNS = (
    r"safe to (?:eat|consume)",
    r"guarantee(?:d|s)?\s+safe",
    r"100%\s*safe",
    r"certified\s+safe",
    r"medically\s+(?:safe|certified|approved)",
)


def _explanation_makes_absolute_safety_claim(text: str) -> bool:
    """Reject LLM copy that overreaches into an absolute/medical guarantee.
    Safe must read as label-scoped ("no disqualifying ingredients found"),
    never as a blanket "safe to eat" claim (Phase 3 product-honesty)."""
    if not text:
        return False
    lowered = text.lower()
    return any(re.search(p, lowered) for p in _ABSOLUTE_SAFETY_CLAIM_PATTERNS)


def _explanation_species_mismatch(text: str, flagged: List[str]) -> bool:
    """True when explanation names a different meat species than flagged ingredients."""
    from core.external_apis.enrichment_relevance import species_groups_in_text

    flagged_groups: set[str] = set()
    for item in flagged:
        flagged_groups |= species_groups_in_text(item)
    if not flagged_groups:
        return False
    text_groups = species_groups_in_text(text)
    if not text_groups:
        return False
    return flagged_groups.isdisjoint(text_groups)


def llm_compose_verdict_explanation(
    verdict: ComplianceVerdict,
    profile: Any,
    avoid_substances: List[str],
    check_names: List[str],
    safe_count: int,
    avoid_user_labels: Optional[List[str]] = None,
) -> Optional[str]:
    """LLM verdict explanation: context and nuance only, no ingredient lists."""
    diet = ""
    if profile and hasattr(profile, "dietary_preference"):
        diet = profile.dietary_preference or ""
    diet_phrase = diet if diet and diet != "No rules" else "the user's dietary profile"
    user_labels = avoid_user_labels or avoid_substances

    if verdict.status == VerdictStatus.SAFE and not avoid_substances and not check_names:
        prompt = (
            f"No disqualifying ingredients were found among the {safe_count} ingredients on this "
            f"label for a {diet_phrase} diet. One short confirmation sentence scoped to this label "
            f"only — do NOT say it is safe to eat or medically guaranteed. Do NOT list names."
        )
    elif avoid_substances:
        primary = avoid_substances[0]
        user_label = user_labels[0] if user_labels else primary
        user_note = ""
        if user_label.strip().lower() != primary.strip().lower():
            formatted_user = _format_user_ingredient_label(user_label)
            user_note = f" User typed {formatted_user} (= {primary})."
        alts = INGREDIENT_ALTERNATIVES.get(primary.lower(), [])
        alt_hint = f" Suggest {alts[0]} as a swap." if alts else ""
        prompt = (
            f"NOT SUITABLE for {diet_phrase}. Primary flagged ingredient: {primary}.{user_note}{alt_hint} "
            f"Discuss ONLY {primary}. Do not mention gelatin or any other ingredient unless it is {primary}. "
            f"One practical sentence on why it appears in products and what to pick instead. "
            f"Max 45 words. Do NOT list all ingredients."
        )
    elif check_names:
        prompt = (
            f"NEEDS VERIFICATION for {diet_phrase}. Uncertain: {', '.join(check_names[:3])}. "
            f"One sentence on what to verify on the label. Max 45 words."
        )
    else:
        return None

    result = _call_ollama(_VERDICT_EXPLANATION_SYSTEM, prompt, timeout=LLM_RESPONSE_TIMEOUT)
    if result and _looks_like_ingredient_list(result):
        return None
    if result and _explanation_makes_absolute_safety_claim(result):
        logger.info("LLM_VERDICT_EXPL rejected absolute safety claim")
        return None
    if result and _explanation_introduces_unflagged_terms(
        result, list(avoid_substances) + list(check_names)
    ):
        logger.info("LLM_VERDICT_EXPL rejected unflagged sensitive terms")
        return None
    # Attribution guard (spec §7.2): when the primary Avoid ingredient's FAIL
    # is diet-attributed, the LLM must not contradict the template by saying
    # "allergen(s)" -- fall back to the template rather than risk that copy.
    allergen_rids = _profile_allergen_restriction_ids(profile)
    primary_rids = list(verdict.triggered_restrictions or [])
    by_ing = getattr(verdict, "triggered_restrictions_by_ingredient", None) or {}
    if avoid_substances:
        primary_name = (avoid_substances[0] or "").lower().strip()
        for key in (primary_name, avoid_substances[0]):
            if key in by_ing:
                primary_rids = list(by_ing[key] or [])
                break
    if (
        result
        and avoid_substances
        and _attribution_kind(primary_rids, allergen_rids) == "diet"
        and re.search(r"allerg", result, re.IGNORECASE)
    ):
        logger.info("LLM_VERDICT_EXPL rejected allergen wording contradicting diet attribution")
        return None
    return _trim_explanation(result) if result else None
