"""Text-level normalization before label clause/atom parsing (classes E, F, I, K)."""
from __future__ import annotations

import re

_BULLET_SEP = re.compile(r"\s*(?:[•·▪‣●])\s*")
# Top-level " and " between ingredients (not inside nesting delimiters).
_TOP_LEVEL_AND = re.compile(
    r"\s+and\s+(?![^(\[\{]*[\)\]\}])",
    re.IGNORECASE,
)
# Phrases where ``and`` is part of a name/header, not a list separator.
_PROTECTED_AND_PHRASES = re.compile(
    r"\b(?:"
    r"vitamins?\s+and\s+minerals|minerals?\s+and\s+vitamins|"
    r"onion\s+and\s+leek|celery\s+and\s+carrot|"
    r"disodium\s+inosinate\s+and\s+disodium\s+guanylate|"
    r"mono(?:glycerides?)?\s+and\s+di(?:glycerides?)?|"
    r"fruits?\s+and\s+vegetables|"
    r"herbs?\s+and\s+spices"
    r")\b",
    re.IGNORECASE,
)
_INGREDIENTS_LINE = re.compile(r"^\s*ingredients?\s*[:;\-]?\s*", re.IGNORECASE)


def _protect_and_phrases(text: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}

    def _repl(match: re.Match[str]) -> str:
        key = f"\x00AND{len(placeholders)}\x00"
        placeholders[key] = match.group(0)
        return key

    return _PROTECTED_AND_PHRASES.sub(_repl, text), placeholders


def _restore_and_phrases(text: str, placeholders: dict[str, str]) -> str:
    for key, value in placeholders.items():
        text = text.replace(key, value)
    return text


def _newline_rich_list_to_commas(text: str) -> str:
    """Turn newline-separated ingredient lines into commas when few commas exist."""
    if not text or "\n" not in text:
        return text
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return text
    comma_lines = sum(1 for ln in lines if "," in ln)
    if comma_lines >= max(1, len(lines) // 2):
        return text
    header = ""
    body_lines = lines
    if _INGREDIENTS_LINE.match(lines[0]):
        header = _INGREDIENTS_LINE.match(lines[0]).group(0)
        first_body = _INGREDIENTS_LINE.sub("", lines[0]).strip()
        body_lines = ([first_body] if first_body else []) + lines[1:]
    joined = ", ".join(ln for ln in body_lines if ln)
    return f"{header}{joined}" if header else joined


def normalize_label_separators(text: str) -> str:
    """Normalize bullets, newlines, and top-level ``and`` before atom parsing."""
    if not text:
        return text
    t = text.strip()
    t = _BULLET_SEP.sub(", ", t)
    t = _newline_rich_list_to_commas(t)
    if _TOP_LEVEL_AND.search(t):
        protected, placeholders = _protect_and_phrases(t)
        parts = []
        for chunk in re.split(r"([,;](?![^(\[\{]*[\)\]\}]))", protected):
            if chunk in {",", ";"}:
                parts.append(chunk)
            else:
                parts.append(_TOP_LEVEL_AND.sub(", ", chunk))
        t = _restore_and_phrases("".join(parts), placeholders)
    t = re.sub(r",\s*,+", ", ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t
