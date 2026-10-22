"""Select the ingredient block a later stage should evaluate."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from core.parsing.label_text import select_ingredient_label_text

_RECIPE = re.compile(
    r"\b(?:how\s+do\s+i\s+make|recipe\s+for|ingredients\s+for\s+(?:a\s+)?(?:pesto|cake|soup|curry))\b",
    re.IGNORECASE,
)
_MULTI_PRODUCT = re.compile(
    r"\bproduct\s+([a-z0-9]+)\s*:",
    re.IGNORECASE,
)
_BARCODE = re.compile(r"^\s*\d{8,14}\s*$")
_ING_HEADER = re.compile(r"\bingredients?\s*[:;]", re.IGNORECASE)
_Q_PREFIX = re.compile(
    r"^\s*(?:is|are|can\s+i\s+(?:eat|have)|does|what\s+about|how\s+about)\s+",
    re.IGNORECASE,
)
_DIET_TAIL = re.compile(
    r"\b(?:vegan|vegetarian|jain|halal|kosher|gluten[\s-]*free|"
    r"dairy[\s-]*free|peanut[\s-]*free|nut[\s-]*free|"
    r"safe(?:\s+for\s+me)?|ok(?:ay)?(?:\s+for\s+me)?)\s*\??\s*$",
    re.IGNORECASE,
)
_LIST_HINT = re.compile(r"\b(?:with|and|or)\b|,")


@dataclass
class IngredientBlock:
    kind: str  # label | recipe | multi_product | product_name | none
    text: str
    atoms: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)


def _product_question_subject(text: str) -> str | None:
    """Return the name in 'Is Nutella vegan?' when there is no ingredient list."""
    if _ING_HEADER.search(text or ""):
        return None
    if _LIST_HINT.search(text or ""):
        return None
    t = (text or "").strip()
    if not (_Q_PREFIX.search(t) or "?" in t):
        return None
    t = _Q_PREFIX.sub("", t)
    t = _DIET_TAIL.sub("", t).strip(" ?.")
    if not t or len(t.split()) > 6:
        return None
    return t


def _is_known_single_ingredient(name: str) -> bool:
    """True for a one-token L1/L2 commodity. No synonymy ladder (Cadbury ≠ milk)."""
    if len((name or "").split()) != 1:
        return False
    from core.knowledge.ike2 import truth_anchor
    from core.knowledge.ike2.stores import local_ontology
    from core.normalization.normalizer import normalize_ingredient_key

    raw = (name or "").strip()
    key = normalize_ingredient_key(raw) or raw.lower()
    if truth_anchor.lookup(raw) is not None or truth_anchor.lookup(key) is not None:
        return True
    # Exact index keys only — lookup() would commodity-head "Dairy Milk" to milk.
    index = local_ontology._index()
    for candidate in local_ontology._index_keys_for_label(raw):
        if candidate in index:
            return True
    return False


def extract_ingredient_block(raw: str) -> IngredientBlock:
    """Classify paste and return the atoms a later stage may evaluate."""
    text = (raw or "").strip()
    if not text:
        return IngredientBlock(kind="none", text="")

    subject = _product_question_subject(text)
    if subject and not _is_known_single_ingredient(subject):
        return IngredientBlock(kind="product_name", text=text, unparsed=[subject])

    if _BARCODE.match(text):
        return IngredientBlock(kind="product_name", text=text, unparsed=[text])

    if _RECIPE.search(text):
        from core.parsing.ingredient_parser import preprocess_ingredients_to_strings

        atoms = preprocess_ingredients_to_strings(text)
        return IngredientBlock(kind="recipe", text=text, atoms=atoms)

    products = _MULTI_PRODUCT.findall(text)
    if len(products) >= 2:
        chunks = _MULTI_PRODUCT.split(text)
        # split keeps delimiters out; pair names with following text
        named: list[str] = []
        parts = re.split(r"\bproduct\s+[a-z0-9]+\s*:", text, flags=re.IGNORECASE)
        for p in parts:
            p = p.strip(" .")
            if p:
                named.append(p)
        return IngredientBlock(
            kind="multi_product",
            text=text,
            products=named,
            unparsed=["multiple products; will not combine into one SAFE"],
        )

    if _ING_HEADER.search(text) or "," in text:
        from core.parsing.ingredient_parser import preprocess_ingredients_to_strings

        selected = select_ingredient_label_text(text)
        atoms = preprocess_ingredients_to_strings(selected)
        return IngredientBlock(kind="label", text=selected, atoms=atoms)

    if re.match(r"^\s*can\s+i\s+eat\s+this\b", text, re.IGNORECASE) and "," not in text:
        return IngredientBlock(kind="product_name", text=text, unparsed=[text])

    words = text.split()
    looks_like_question = bool(
        re.search(r"\b(?:is|are|can|does|do|what|how|check)\b", text, re.IGNORECASE)
        or "?" in text
    )
    if (
        1 <= len(words) <= 4
        and not re.search(r"\d", text)
        and not looks_like_question
    ):
        return IngredientBlock(kind="product_name", text=text, unparsed=[text])

    from core.parsing.ingredient_parser import preprocess_ingredients_to_strings

    atoms = preprocess_ingredients_to_strings(text)
    return IngredientBlock(kind="label", text=text, atoms=atoms)
