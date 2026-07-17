"""Prepare ingredient atoms for chat compliance (label decomposer vs compound expansion)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from core.compound_expansion import expand_compounds
from core.intent_detector import ParsedIntent, _has_ingredient_list_indicator
from core.parsing.label_decomposer import DecomposedItem, decompose_label
from core.parsing.label_text import fix_ocr_label_noise, select_ingredient_label_text

_INGREDIENTS_HEADER = re.compile(r"\bingredients?\s*[:;]", re.IGNORECASE)
_TRACE_BOILERPLATE = re.compile(
    r"contains\s+2%|less\s+than\s+2%|less\s+of\s+each|gravy\s*:|contains\s*:|"
    r"cooked\s+[a-z]+\s+steak|may\s+contain|produced\s+in\s+a\s+facility",
    re.IGNORECASE,
)
_NEWLINE_LIST = re.compile(r"ingredients?\s*[:;\-]?\s*[^\n,]{0,40}\n", re.IGNORECASE)
_BULLET_LIST = re.compile(r"[•·▪‣●]")


@dataclass(frozen=True)
class PreparedChatIngredients:
    """Atoms and display metadata for compliance + IKE-2 shadow."""

    eval_names: list[str]
    compound_map: dict[str, str] = field(default_factory=dict)
    decomposed: list[DecomposedItem] | None = None
    label_text: str | None = None


def _needs_label_decomposer(query: str, ingredients: list[str]) -> bool:
    q = query or ""
    if _INGREDIENTS_HEADER.search(q):
        return True
    if _NEWLINE_LIST.search(q) or _BULLET_LIST.search(q):
        return True
    if _TRACE_BOILERPLATE.search(q):
        return True
    blob = " ".join(ingredients or [])
    if "[" in blob or ("(" in blob and "," in blob):
        return True
    if _TRACE_BOILERPLATE.search(blob):
        return True
    if re.search(r"\s+and\s+", blob, re.IGNORECASE) and len(ingredients or []) <= 3:
        return True
    if len(ingredients or []) > 12:
        return True
    return False


def _label_source_text(query: str) -> str:
    return select_ingredient_label_text(fix_ocr_label_noise((query or "").strip()))


def prepare_chat_ingredients(query: str, parsed: ParsedIntent) -> PreparedChatIngredients:
    """Route label-shaped pastes through ``decompose_label``; simple lists through compounds."""
    ingredients = list(parsed.ingredients or [])
    if not ingredients and not _has_ingredient_list_indicator(query):
        return PreparedChatIngredients(eval_names=[], compound_map={})

    if _needs_label_decomposer(query, ingredients):
        label_text = _label_source_text(query)
        items = decompose_label(label_text)
        names = [i.name for i in items]
        return PreparedChatIngredients(
            eval_names=names,
            compound_map={},
            decomposed=items,
            label_text=label_text,
        )

    eval_names, compound_map = expand_compounds(ingredients)
    return PreparedChatIngredients(
        eval_names=eval_names,
        compound_map=compound_map,
        decomposed=None,
        label_text=None,
    )
