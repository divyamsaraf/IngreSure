"""Classify a single ingredient segment's parenthetical.

Kinds:
  function_header_numbers — Emulsifier (322, 471)
  function_header_payload — Emulsifier (Soya lecithin) / Thickener (guar gum)
  ins_e_list              — colour (E102, E110) / Antioxidant (E300)
  name_function           — soy lecithin (an emulsifier)
  name_origin             — lecithin (soya)
  sub_ingredient_list     — chocolate (sugar, cocoa butter, milk)
  quantity                — PEANUTS (49.5%)
  translation             — sugar (sucre)
  claim                   — flavour (nature identical)
  additive_subvariant     — INS 322(ii)
  none                    — no parenthetical
"""
from __future__ import annotations

import re
from core.parsing.translation_pairs import is_translation_pair

FUNCTION_HEADERS = frozenset({
    "emulsifier",
    "emulsifiers",
    "thickener",
    "thickeners",
    "acidity regulator",
    "acidity regulators",
    "preservative",
    "preservatives",
    "antioxidant",
    "antioxidants",
    "colour",
    "colouring",
    "color",
    "coloring",
    "colours",
    "colors",
    "flavour",
    "flavor",
    "flavouring",
    "flavoring",
    "flavours",
    "flavors",
    "stabiliser",
    "stabilizer",
    "stabilisers",
    "stabilizers",
    "humectant",
    "humectants",
    "raising agent",
    "raising agents",
    "firming agent",
    "gelling agent",
    "sweetener",
    "sweeteners",
    "glazing agent",
    "anti-caking agent",
    "sequestrant",
    "flour treatment agent",
    "flour treatment agents",
    "sequestering agent",
    "binding agent",
    "gelling agents",
    "firming agents",
})

_FUNCTION_PHRASE = re.compile(
    r"^(?:an?\s+|the\s+)?"
    r"(?:emulsifier|thickener|preservative|antioxidant|acidity\s+regulator|"
    r"stabiliser|stabilizer|humectant|raising\s+agent|colour(?:ing)?|color(?:ing)?|"
    r"flavour(?:ing)?|flavor(?:ing)?|to\s+preserve|for\s+colou?r|nature\s+identical|"
    r"identical\s+to\s+natural)\b",
    re.IGNORECASE,
)
_QUANTITY = re.compile(
    r"^(?:(?:min|max|minimum|maximum|approx|approximately|about|ca)\.?\s+)?"
    r"~?\s*\d+(?:[.,]\d+)?\s*%$",
    re.IGNORECASE,
)
_ADDITIVE_ITEM = re.compile(
    r"^(?:e|ins)?\s*\d{2,4}\s*(?:\([ivxlcdm]+\)|\([a-z]\)|[a-z]|[ivxlcdm]+)?$",
    re.IGNORECASE,
)
_ADDITIVE_HEAD = re.compile(r"^(?:e|ins)\s*\d{2,4}$", re.IGNORECASE)
_ROMAN = re.compile(r"^[ivxlcdm]+$", re.IGNORECASE)
_HAZARD_ORIGIN = re.compile(
    r"\b(?:soy|soya|soja|milk|lait|wheat|blé|ble|egg|peanut|sesame|fish|"
    r"shellfish|almond|cashew|hazelnut|mustard|celery|lupin|barley|rye|oat)\b",
    re.IGNORECASE,
)


def _split_inner(inner: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\s*,\s*", inner) if p.strip()]
    out: list[str] = []
    for part in parts:
        if re.search(r"\d{2,4}", part) and re.search(r"\s+(?:and|&)\s+", part, re.I):
            out.extend(
                x.strip()
                for x in re.split(r"\s+(?:and|&)\s+", part, flags=re.I)
                if x.strip()
            )
        else:
            out.append(part)
    return out


def _outer_paren(text: str) -> tuple[str, str, str] | None:
    start = text.find("(")
    if start < 0:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[:start].strip(), text[start + 1 : i].strip(), text[i + 1 :].strip()
    return text[:start].strip(), text[start + 1 :].strip(), ""


def classify_parenthetical(segment: str) -> tuple[str, dict]:
    """Return (kind, payload) for one comma-level segment."""
    text = (segment or "").strip()
    outer = _outer_paren(text)
    if not outer:
        return "none", {"text": text}
    base, inner, rest = outer
    if rest:
        return "none", {"text": text}
    payload = {"base": base, "inner": inner, "text": text}
    if not inner:
        return "none", payload

    base_key = re.sub(r"\s+", " ", base.lower())
    items = _split_inner(inner)

    if _ADDITIVE_HEAD.match(base) and _ROMAN.match(inner):
        payload["codes"] = [f"{base}({inner})"]
        return "additive_subvariant", payload

    if all(_QUANTITY.match(x) for x in items) and any("%" in x or _QUANTITY.match(x) for x in items):
        if len(items) == 1 and (_QUANTITY.match(inner)):
            return "quantity", payload

    if items and all(_ADDITIVE_ITEM.match(x.replace(" ", "")) or _ADDITIVE_ITEM.match(x) for x in items):
        payload["codes"] = items
        if base_key in FUNCTION_HEADERS or not base:
            return "function_header_numbers", payload
        return "ins_e_list", payload

    if _FUNCTION_PHRASE.match(inner) or inner.lower() in FUNCTION_HEADERS:
        return "name_function", payload

    if base_key in FUNCTION_HEADERS:
        payload["inners"] = items or [inner]
        return "function_header_payload", payload

    if _HAZARD_ORIGIN.search(inner):
        return "name_origin", payload

    if len(items) >= 2:
        return "sub_ingredient_list", payload

    if base and is_translation_pair(base, inner):
        return "translation", payload

    if re.search(r"\b(?:free|claim|organic|identical)\b", inner, re.I):
        return "claim", payload

    if _QUANTITY.match(inner):
        return "quantity", payload

    return "synonym", payload


def additive_atom(token: str) -> str:
    """Canonicalise a number/E/INS token to one additive surface form."""
    t = (token or "").strip()
    t = re.sub(r"\s+", " ", t)
    m = re.match(
        r"^(?:e|ins)?\s*(\d{2,4})\s*(?:\(([ivxlcdm]+)\)|\(([a-z])\)|([a-z])|([ivxlcdm]+))?$",
        t,
        re.IGNORECASE,
    )
    if not m:
        return t
    num = m.group(1)
    roman = m.group(2) or m.group(5)
    letter = m.group(3) or m.group(4)
    if roman:
        return f"e{num}({roman.lower()})"
    if letter:
        return f"e{num}{letter.lower()}"
    return f"e{num}"
