"""
LLM-powered response composer for greetings, profile updates, and general questions.
Used when the app needs natural-language replies (greeting, profile confirmation, general Q&A).
Verdict responses use the template-based response_composer for consistency and speed.
"""
import logging
from typing import Optional, Dict, Any

import requests

from core.config import get_ollama_url, get_ollama_model, LLM_RESPONSE_TIMEOUT

logger = logging.getLogger(__name__)

_RESPONSE_SYSTEM_PROMPT = """You are a friendly grocery safety assistant. Give brief, warm, conversational replies.
Keep to 1-3 sentences. Do NOT offer recipes, alternatives, or unsolicited follow-ups. No emojis."""


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
