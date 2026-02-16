"""
Deterministic normalization only. No LLM, no substring guessing.
Used to produce a key for ontology lookup; unknown keys are not resolved here.
"""
import re
from typing import List


def normalize_ingredient_key(text: str) -> str:
    """
    Normalize a raw ingredient string for lookup.
    - Lowercase, strip, remove common punctuation.
    - No substring or fuzzy matching.
    """
    if not text or not isinstance(text, str):
        return ""
    t = text.lower().strip()
    t = t.replace("*", "").replace(".", "")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def tokenize_ingredients(raw_text: str) -> List[str]:
    """
    Split raw text into candidate ingredient tokens (e.g. by comma, newline).
    Does not resolve or validate; just deterministic split and trim.
    """
    if not raw_text:
        return []
    # Split on comma, newline, semicolon; trim each
    parts = re.split(r"[\n,;]", raw_text)
    return [normalize_ingredient_key(p) for p in parts if normalize_ingredient_key(p)]
