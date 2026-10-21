"""Select and clean pasted label text (multi-block labels, OCR noise)."""
from __future__ import annotations

import re

_ING_HEADER = re.compile(r"\bingredients?\s*[:;]\s*", re.IGNORECASE)
# Multilingual one-product packs (CA/BE/CH/EU): Ingredients / Ingrédients / Zutaten.
_LANG_ING_HEADER = re.compile(
    r"(?:^|(?<=[\n.]))\s*"
    r"(?P<header>"
    r"ingredients?(?:\s*\([^)]+\))?|"
    r"ingr[eé]dients?|"
    r"zutaten|"
    r"ingredienti|"
    r"ingredientes|"
    r"ingredi[eë]nten|"
    r"ingredienser|"
    r"složen[ií]|"
    r"składniki"
    r")\s*[:\-]",
    re.IGNORECASE,
)
_LANG_VARIANT_HEADER = re.compile(
    r"(?:zutaten|ingrédients?|ingredienti|ingredientes|"
    r"ingrediënten|ingredienser|složen[ií]|składniki|"
    r"ingredients?\s*\([^)]+\))",
    re.IGNORECASE,
)
_ACTIVE_INGREDIENT_SUFFIX = re.compile(
    r"\.\s+Active\s+Ingredient\s+Name\b.*",
    re.IGNORECASE | re.DOTALL,
)
# Trailing chat/profile prose after an ingredient list (not part of the label).
_TRAILING_PROFILE_PROSE = re.compile(
    r"\.\s+(?:"
    r"i\s+have\b|i'?m\b|i\s+am\b|i'?ve\b|my\s+(?:diet|allerg)|"
    r"i\s+(?:follow|eat|avoid|can'?t|cannot|don'?t|practice)|"
    r"please\s+(?:note|check|set)|"
    r"allergic\b|"
    r"is\s+this\b|are\s+these\b|can\s+i\b|does\s+this\b"
    r").*$",
    re.IGNORECASE | re.DOTALL,
)
_OCR_PREFIX_FIXES = (
    (re.compile(r"\bingred1ents\b", re.IGNORECASE), "Ingredients"),
    (re.compile(r"\b1ngredients\b", re.IGNORECASE), "Ingredients"),
    (re.compile(r"\bingredlents\b", re.IGNORECASE), "Ingredients"),
)
# OCR sometimes renders a comma as the letter "l" followed by a period.
_BROKEN_COMMA = re.compile(r"\bl\s*\.\s+(?=[a-z])", re.IGNORECASE)


def fix_ocr_label_noise(text: str) -> str:
    """High-confidence OCR repairs on full label paste (prefix + comma glitches)."""
    if not text:
        return text
    t = text
    for pattern, replacement in _OCR_PREFIX_FIXES:
        t = pattern.sub(replacement, t)
    t = _BROKEN_COMMA.sub(", ", t)
    t = re.sub(r"\s+,", ",", t)
    t = re.sub(r",\s+", ", ", t)
    return t


def _strip_active_ingredient_suffix(text: str) -> str:
    m = _ACTIVE_INGREDIENT_SUFFIX.search(text)
    if m:
        return text[: m.start()].strip().rstrip(".")
    return text


def strip_trailing_profile_prose(text: str) -> str:
    """Drop first-person / trailing question prose after an ingredient list.

    Chat often pastes ``Ingredients: A, B, C. I have a peanut allergy.`` — the
    second sentence is a profile update, not an ingredient atom. Without this,
    label decomposition glues it onto the last name (``peanut i have…``).
    """
    if not text:
        return text
    m = _TRAILING_PROFILE_PROSE.search(text)
    if m:
        return text[: m.start()].strip().rstrip(".")
    return text


def _segment_comma_count(segment: str) -> int:
    return segment.count(",")


def _join_language_ingredient_blocks(text: str) -> str | None:
    """Concatenate multilingual Ingredients/Zutaten/Ingrédients bodies (A31)."""
    matches = list(_LANG_ING_HEADER.finditer(text))
    if len(matches) < 2:
        return None
    if not any(_LANG_VARIANT_HEADER.search(m.group("header")) for m in matches):
        return None
    bodies: list[str] = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip(" .;")
        if body:
            bodies.append(body)
    if not bodies:
        return None
    return ", ".join(bodies)


def select_ingredient_label_text(text: str) -> str:
    """Pick the best ingredient list from multi-block pastes.

    Language-variant headers (Ingredients / Ingrédients / Zutaten) are one
    product: join every block. Same-language repeated ``Ingredients:`` still
    prefers the **last** block (nutrition facts then the list).
    """
    if not text or not text.strip():
        return text
    t = fix_ocr_label_noise(text.strip())

    joined = _join_language_ingredient_blocks(t)
    if joined is not None:
        t = joined
    else:
        headers = list(_ING_HEADER.finditer(t))
        if len(headers) >= 2:
            t = t[headers[-1].start() :].strip()
        elif len(headers) == 1:
            t = t[headers[0].start() :].strip()
        else:
            segments = [s.strip() for s in re.split(r"\n{2,}|\.\s+(?=Nutrition\b)", t) if s.strip()]
            if segments:
                best = max(segments, key=_segment_comma_count)
                if _segment_comma_count(best) > 0:
                    t = best

    return strip_trailing_profile_prose(_strip_active_ingredient_suffix(t))
