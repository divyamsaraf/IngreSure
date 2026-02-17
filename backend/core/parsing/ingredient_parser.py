"""
Preprocess complex ingredient strings into atomic ingredients for evaluation.
- Split by parentheses and flatten nested lists.
- Normalize each part via normalizer.
- Detect <2% trace ingredients (informational unless they conflict with user profile).
"""
import re
import logging
from typing import List, Dict, Any, Optional, Callable

from core.normalization.normalizer import normalize_ingredient_key

logger = logging.getLogger(__name__)

# Patterns for trace/minor ingredient labels (often at end of ingredient list)
TRACE_PATTERNS = [
    re.compile(r"less than 2%? of", re.IGNORECASE),
    re.compile(r"<2%?\s*of", re.IGNORECASE),
    re.compile(r"2%?\s*or less", re.IGNORECASE),
    re.compile(r"contains 2%?\s*or less", re.IGNORECASE),
    re.compile(r"\(&lt;2%\)", re.IGNORECASE),
    re.compile(r"\(\s*&lt;\s*2\s*%?\s*\)", re.IGNORECASE),
]


def _split_by_parentheses(text: str) -> List[str]:
    """
    Split a string by top-level parentheses, preserving content inside.
    'Enriched Flour (Wheat Flour, Niacin, Iron)' ->
    ['Enriched Flour', 'Wheat Flour', 'Niacin', 'Iron']
    Handles nested parentheses by flattening inner content.
    """
    if not text or not text.strip():
        return []
    out: List[str] = []
    depth = 0
    start = 0
    i = 0
    while i < len(text):
        if text[i] == "(":
            if depth == 0 and i > start:
                chunk = text[start:i].strip()
                if chunk:
                    out.append(chunk)
            depth += 1
            if depth == 1:
                start = i + 1
            i += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                inner = text[start:i].strip()
                if inner:
                    # Split inner by comma (sub-ingredients)
                    for part in re.split(r"\s*,\s*", inner):
                        part = part.strip()
                        if part:
                            # Recursively handle any nested parens in part
                            out.extend(_split_by_parentheses(part))
                start = i + 1
            i += 1
        else:
            i += 1
    if depth == 0 and start < len(text):
        chunk = text[start:].strip()
        if chunk:
            out.append(chunk)
    return out


def _is_trace_section(text: str) -> bool:
    """Return True if this segment introduces trace/minor ingredients (<2%)."""
    for pat in TRACE_PATTERNS:
        if pat.search(text):
            return True
    return False


def _strip_trace_markers(text: str) -> str:
    """Remove '<2%' and similar markers from ingredient name for normalization."""
    t = text
    t = re.sub(r"\s*[<(]\s*&lt;\s*2\s*%?\s*[>)]\s*", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*<\s*2\s*%?\s*", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*less than 2%?\s*of\s*:?\s*", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*contains 2%?\s*or less\s*(?:of\s*)?:?\s*", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"^\s*:+\s*", "", t)
    t = re.sub(r"^\s*of\s*:?\s*", "", t, flags=re.IGNORECASE)
    return t.strip()


def preprocess_ingredients(
    raw_str: str,
    normalizer_fn: Optional[Callable[[str], str]] = None,
) -> List[Dict[str, Any]]:
    """
    Preprocess a raw ingredient label string into a list of atomic ingredients.

    Step 1: Split by parentheses and flatten (commas inside parentheses become separate items).
    Step 2: Detect <2% trace segments; mark subsequent ingredients as trace until next major segment.
    Step 3: Normalize each with normalizer_fn or normalize_ingredient_key.
    Step 4: Deduplicate by normalized key, preserving trace flag (if any occurrence is trace, keep trace=True).

    Returns list of {"name": normalized_key, "trace": bool}.
    """
    if not raw_str or not isinstance(raw_str, str):
        return []
    norm_fn = normalizer_fn or normalize_ingredient_key

    # Split by parentheses and flatten
    raw_flat: List[str] = []
    # First split by comma at top level (no parens) to get major segments
    segments = re.split(r",(?![^(]*\))", raw_str)
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        parts = _split_by_parentheses(seg)
        raw_flat.extend(parts)

    # Mark trace: if we see "contains 2% or less" or "<2% of" then following items are trace
    # For simplicity: scan each segment for embedded trace marker or preceding trace phrase
    result_by_key: Dict[str, Dict[str, Any]] = {}
    trace_until_end = False
    for i, part in enumerate(raw_flat):
        part_clean = _strip_trace_markers(part)
        if not part_clean:
            continue
        is_trace = trace_until_end or _is_trace_section(part)
        if _is_trace_section(part):
            trace_until_end = True
        key = norm_fn(part_clean)
        if not key:
            continue
        if key in result_by_key:
            result_by_key[key]["trace"] = result_by_key[key]["trace"] or is_trace
        else:
            result_by_key[key] = {"name": key, "trace": is_trace}

    return list(result_by_key.values())


def preprocess_ingredients_to_strings(
    raw_str: str,
    normalizer_fn: Optional[Callable[[str], str]] = None,
) -> List[str]:
    """
    Same as preprocess_ingredients but returns only the list of normalized name strings.
    Useful when trace handling is done at engine level via a separate trace set.
    """
    items = preprocess_ingredients(raw_str, normalizer_fn=normalizer_fn)
    return [x["name"] for x in items]


def get_trace_keys(preprocessed: List[Dict[str, Any]]) -> set:
    """Return set of normalized ingredient keys that are marked as trace (<2%)."""
    return {x["name"] for x in preprocessed if x.get("trace")}


def filter_trace_by_profile(
    preprocessed: List[Dict[str, Any]],
    profile_allergens: List[str],
    profile_restriction_ids: List[str],
) -> List[Dict[str, Any]]:
    """
    Optional: keep trace ingredients in the list only if they might conflict with profile.
    E.g. user allergic to peanuts -> keep trace peanut for evaluation.
    Otherwise trace items can be excluded from evaluation (informational only).
    """
    if not profile_allergens and not profile_restriction_ids:
        return preprocessed
    # For now we keep all trace in the list; engine will evaluate and only NOT_SAFE on conflict.
    # Informational logging for trace+unknown is in the engine.
    return preprocessed
