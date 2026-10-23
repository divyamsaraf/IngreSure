"""Slash translation pairs vs worst-case alternatives (A32)."""
from __future__ import annotations

import re

from core.normalization.normalizer import normalize_ingredient_key

_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"sugar", "sucre", "zucker", "azucar", "zucchero", "suiker"}),
    frozenset({"milk", "lait", "milch", "leche", "latte"}),
    frozenset({"water", "eau", "wasser", "agua", "acqua"}),
    frozenset({"salt", "sel", "salz", "sal", "sale"}),
    frozenset({"wheat", "ble", "blé", "weizen", "trigo"}),
    frozenset({"flour", "farine", "mehl", "harina", "farina"}),
    frozenset({"egg", "eggs", "oeuf", "œuf", "oeufs", "ei", "huevo", "uovo"}),
    frozenset({"butter", "beurre", "butter", "mantequilla", "burro"}),
    frozenset({"oil", "huile", "ol", "öl", "aceite", "olio"}),
    frozenset({"soy", "soya", "soja"}),
    frozenset({"peanut", "arachide", "erdnuss", "cacahuete", "cacahuète"}),
)
_PAIR_INDEX: dict[str, frozenset[str]] = {}
for _group in _GROUPS:
    for _name in _group:
        _PAIR_INDEX[normalize_ingredient_key(_name)] = _group

_SECTION_HEADER = re.compile(
    r"^(?:contains|contient|enthält|gluten\s+source|source\s+de\s+gluten)\s*:",
    re.IGNORECASE,
)
_AND_OR = re.compile(r"\band\s*/\s*or\b", re.IGNORECASE)


def is_translation_pair(left: str, right: str) -> bool:
    a = normalize_ingredient_key(left)
    b = normalize_ingredient_key(right)
    if not a or not b or a == b:
        return False
    group = _PAIR_INDEX.get(a)
    return bool(group and b in group)


def expand_slash_atom(atom: str) -> list[str]:
    """Keep translation pairs as one atom; split non-translation slashes.

    Section headers after `` / `` (Contient:, gluten source:) are not pairs.
    Japanese 原材料名 ``／`` (NFKC → ``/``) is ingredients|additives in CAA
    examples, not a translation pair. See deploy/japan_parser_plan.md.
    UNVERIFIED; no JP ingest.
    """
    raw = (atom or "").strip()
    if not raw or "/" not in raw or _AND_OR.search(raw):
        return [raw] if raw else []
    if _SECTION_HEADER.search(raw):
        return [raw]
    parts = [p.strip() for p in raw.split("/") if p.strip()]
    if len(parts) != 2:
        return [raw]
    left, right = parts
    if _SECTION_HEADER.search(right):
        return [raw]
    if is_translation_pair(left, right):
        return [f"{left}/{right}"]
    return [left, right]
