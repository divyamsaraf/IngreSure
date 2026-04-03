"""
LLM classification for discovered ingredients (DISCOVERED / AUTO_CLASSIFIED).
When APIs return description only, use Ollama to infer origin_type, animal_origin, etc.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import requests

from core.config import get_ollama_url, get_ollama_model, llm_enabled

logger = logging.getLogger(__name__)

_CLASSIFY_TIMEOUT = 15

_PROMPT = """You are a food ingredient classifier for dietary compliance. Given an ingredient name and optional description, return a JSON object with EXACTLY these boolean or string fields:

- "origin_type": one of "plant", "animal", "synthetic", "microbial", "fungal", "insect", "unknown"
- "animal_origin": boolean
- "plant_origin": boolean
- "synthetic": boolean
- "egg_source": boolean
- "dairy_source": boolean
- "gluten_source": boolean
- "soy_source": boolean
- "nut_source": null or string (e.g. "peanut", "tree_nut")
- "sesame_source": boolean
- "animal_species": null or string (e.g. "fish", "cow", "pig") if animal_origin is true

Rules: Infer from name and description only. "carmine" -> animal_origin true, insect. "chickpea" -> plant_origin true. Return ONLY valid JSON, no markdown."""


def classify_ingredient_origin(
    name: str,
    description: str = "",
    timeout: int = _CLASSIFY_TIMEOUT,
) -> Optional[dict[str, Any]]:
    """
    Call LLM to classify ingredient. Returns dict with origin_type, animal_origin, etc.
    Returns None on failure or if Ollama is unavailable.
    """
    if not llm_enabled() or not name or not name.strip():
        return None
    prompt = f"Ingredient name: {name.strip()}\n"
    if description and description.strip():
        prompt += f"Description: {description.strip()}\n"
    prompt += "Return the JSON classification:"
    try:
        resp = requests.post(
            get_ollama_url(),
            json={
                "model": get_ollama_model(),
                "prompt": prompt,
                "system": _PROMPT,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 200},
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        raw = (resp.json().get("response") or "").strip()
    except requests.RequestException as e:
        logger.debug("LLM classify failed name=%s: %s", name[:40], e)
        return None
    if not raw:
        return None
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`")
    try:
        out = json.loads(cleaned)
        if isinstance(out, dict):
            return out
    except json.JSONDecodeError:
        pass
    return None


def apply_classification_to_ingredient(ing: Any, classification: dict[str, Any]) -> Any:
    """Return a new Ingredient with flags updated from classification dict (from classify_ingredient_origin)."""
    from core.ontology.ingredient_schema import Ingredient
    return Ingredient(
        id=ing.id,
        canonical_name=ing.canonical_name,
        aliases=ing.aliases,
        derived_from=ing.derived_from,
        contains=ing.contains,
        may_contain=ing.may_contain,
        animal_origin=bool(classification.get("animal_origin", ing.animal_origin)),
        plant_origin=bool(classification.get("plant_origin", ing.plant_origin)),
        synthetic=bool(classification.get("synthetic", ing.synthetic)),
        fungal=ing.fungal,
        insect_derived=ing.insect_derived,
        animal_species=classification.get("animal_species") or ing.animal_species,
        egg_source=bool(classification.get("egg_source", ing.egg_source)),
        dairy_source=bool(classification.get("dairy_source", ing.dairy_source)),
        gluten_source=bool(classification.get("gluten_source", ing.gluten_source)),
        nut_source=classification.get("nut_source") if classification.get("nut_source") is not None else ing.nut_source,
        soy_source=bool(classification.get("soy_source", ing.soy_source)),
        sesame_source=bool(classification.get("sesame_source", ing.sesame_source)),
        alcohol_content=ing.alcohol_content,
        root_vegetable=ing.root_vegetable,
        onion_source=ing.onion_source,
        garlic_source=ing.garlic_source,
        fermented=ing.fermented,
        uncertainty_flags=list(ing.uncertainty_flags or []) + ["llm_classified"],
        regions=ing.regions,
    )
