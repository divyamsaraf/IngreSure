"""
LLM-powered intent extraction — fallback when rule-based detector returns
GENERAL_QUESTION with no ingredients (i.e. rules couldn't parse the query).

Uses Ollama (local LLM) to extract structured intent from free-form text.
The compliance engine remains 100% deterministic — LLM only parses input.
"""
import json
import logging
import re
from typing import Optional

import requests

from core.config import get_ollama_url, get_ollama_model

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a JSON parser for a grocery safety assistant. Your ONLY job is to extract structured data from user messages.

Given a user message, return a JSON object with these fields:
- "intent": one of "PROFILE_UPDATE", "INGREDIENT_QUERY", "MIXED", "GREETING", "GENERAL_QUESTION"
- "dietary_preference": string or null (e.g. "Jain", "Vegan", "Halal", "Kosher", "Hindu Veg", "Vegetarian", "Pescatarian", null)
- "ingredients": list of ingredient strings, or empty list
- "allergens": list of allergen strings the user mentions having, or empty list
- "lifestyle": list like ["no alcohol", "no onion"] or empty list
- "remove_allergens": list of allergens user wants removed, or empty list
- "is_greeting": true if the message is a greeting or conversational (hi, thanks, bye, how are you)
- "is_general_question": true if asking about food science/nutrition in general (not about specific ingredient safety)

RULES:
- Extract ACTUAL ingredient names only. "protein bar" is a product, "eggs" is an ingredient.
- Do NOT invent ingredients. Only extract what the user explicitly mentions.
- "can jain eat onion?" → dietary_preference="Jain", ingredients=["onion"], intent="MIXED"
- "is pork halal?" → dietary_preference="Halal", ingredients=["pork"], intent="MIXED"
- "hi how are you" → is_greeting=true, intent="GREETING"
- "eggs, milk, flour" → ingredients=["eggs","milk","flour"], intent="INGREDIENT_QUERY"
- Return ONLY valid JSON. No markdown, no explanation."""


def _call_ollama(prompt: str, timeout: int = 30) -> Optional[str]:
    """Call Ollama and return the response text, or None on failure."""
    try:
        resp = requests.post(
            get_ollama_url(),
            json={
                "model": get_ollama_model(),
                "prompt": prompt,
                "system": _SYSTEM_PROMPT,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 300},
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.RequestException as e:
        logger.warning("LLM_INTENT ollama call failed: %s", e)
        return None


def _parse_json_response(raw: str) -> Optional[dict]:
    """Extract JSON from LLM response (may contain markdown fences)."""
    if not raw:
        return None
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = cleaned.strip().rstrip("`")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    logger.warning("LLM_INTENT could not parse JSON from: %s", raw[:200])
    return None


def llm_extract_intent(query: str) -> Optional[dict]:
    """
    Use LLM to extract structured intent from a query.

    Returns dict with keys: intent, dietary_preference, ingredients, allergens,
    lifestyle, remove_allergens, is_greeting, is_general_question.
    Returns None if LLM is unavailable or response is unparseable.
    """
    if not query or not query.strip():
        return None

    prompt = f'User message: "{query}"\n\nExtract the structured JSON:'

    raw = _call_ollama(prompt)
    if not raw:
        return None

    data = _parse_json_response(raw)
    if not data:
        return None

    # Validate and normalize the response
    result = {
        "intent": data.get("intent", "GENERAL_QUESTION"),
        "dietary_preference": data.get("dietary_preference"),
        "ingredients": data.get("ingredients", []),
        "allergens": data.get("allergens", []),
        "lifestyle": data.get("lifestyle", []),
        "remove_allergens": data.get("remove_allergens", []),
        "is_greeting": data.get("is_greeting", False),
        "is_general_question": data.get("is_general_question", False),
    }

    # Ensure ingredients is a list of strings
    if not isinstance(result["ingredients"], list):
        result["ingredients"] = []
    result["ingredients"] = [str(i).strip() for i in result["ingredients"] if str(i).strip()]

    # Override intent based on flags
    if result["is_greeting"]:
        result["intent"] = "GREETING"
    elif result["is_general_question"] and not result["ingredients"]:
        result["intent"] = "GENERAL_QUESTION"

    logger.info(
        "LLM_INTENT success query=%s intent=%s diet=%s ingredients=%s",
        query[:60], result["intent"], result["dietary_preference"], result["ingredients"],
    )
    return result
