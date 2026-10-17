"""Surface-form hazard lexicon for parser conservation checks.

Invariant: if a hazard token appears in the raw ingredient list, at least one
parsed atom must still carry that hazard class. Used by conservation audits and
(design) a product-level raw-string backstop that can only add hazards.
"""
from __future__ import annotations

import re
from typing import Iterable

# class -> surface forms (lowercase). Longer forms first for greedy matching.
HAZARD_LEXICON: dict[str, tuple[str, ...]] = {
    "peanut": (
        "peanut butter",
        "peanut oil",
        "peanuts",
        "peanut",
        "groundnut",
        "groundnuts",
        "arachide",
        "arachides",
        "cacahuete",
        "cacahuète",
        "erdnuss",
    ),
    "gluten": (
        "wheat flour",
        "all purpose flour",
        "enriched flour",
        "wheatberries",
        "wheat berries",
        "wheat gluten",
        "malted barley",
        "barley malt",
        "barley",
        "wheat",
        "maida",
        "atta",
        "durum",
        "gluten",
        "rye",
        "spelt",
        "einkorn",
        "khorasan",
        "triticale",
        "farine de blé",
        "blé",
        "seigle",
        "orge",
        "mehl",
        "weizen",
        "gerste",
    ),
    "dairy": (
        "milk powder",
        "skim milk",
        "whole milk",
        "milk fat",
        "milk solids",
        "butterfat",
        "butter",
        "cream",
        "cheese",
        "whey",
        "casein",
        "lactose",
        "yoghurt",
        "yogurt",
        "milk",
        "lait",
        "beurre",
        "fromage",
        "milch",
        "butter",
        "käse",
    ),
    "egg": (
        "egg whites",
        "egg white",
        "egg yolks",
        "egg yolk",
        "whole egg",
        "eggs",
        "egg",
        "albumin",
        "albumen",
        "blanc d'oeuf",
        "blanc d'œuf",
        "blanc d oeuf",
        "blanc dœuf",
        "blanc doeuf",
        "jaune d'oeuf",
        "jaune d'œuf",
        "oeuf",
        "œuf",
        "eier",
    ),
    "soy": (
        "soy lecithin",
        "soya lecithin",
        "soybean oil",
        "soy protein",
        "soy sauce",
        "soyabeans",
        "soyabean",
        "soybeans",
        "soybean",
        "soya",
        "soy",
        "tofu",
        "tempeh",
        "edamame",
        "soja",
    ),
    "sesame": (
        "sesame oil",
        "sesame seeds",
        "sesame seed",
        "sesame",
        "tahini",
        "sésame",
        "sesam",
    ),
    "fish": (
        "anchovy",
        "anchovies",
        "fish oil",
        "fish sauce",
        "cod",
        "salmon",
        "tuna",
        "fish",
        "poisson",
        "fisch",
    ),
    "shellfish": (
        "shellfish",
        "shrimp",
        "prawn",
        "crab",
        "lobster",
        "crustacean",
        "mollusc",
        "mollusk",
        "crevette",
        "krebs",
    ),
    "tree_nut": (
        "almond",
        "almonds",
        "cashew",
        "cashews",
        "walnut",
        "walnuts",
        "hazelnut",
        "hazelnuts",
        "pistachio",
        "pistachios",
        "pecan",
        "pecans",
        "macadamia",
        "brazil nut",
        "pine nut",
        "amande",
        "noisette",
        "noix",
        "mandel",
    ),
}

# Compile word-boundary patterns; skip trailing-space-only forms.
_PATTERNS: dict[str, re.Pattern[str]] = {}
for _cls, forms in HAZARD_LEXICON.items():
    parts = []
    for f in forms:
        f = f.strip()
        if not f:
            continue
        parts.append(re.escape(f))
    if parts:
        _PATTERNS[_cls] = re.compile(
            r"(?<![a-z0-9])(?:" + "|".join(parts) + r")(?![a-z0-9])",
            re.IGNORECASE,
        )


# Negated contexts: surface forms that look like hazards but are not.
_NEGATED = (
    # "gluten-free" / "gluten free" is a claim, not gluten
    (re.compile(r"gluten[\s\-]*free", re.I), {"gluten"}),
    # Plant milks / butters: "milk"/"butter" substring is not dairy
    (
        re.compile(
            r"\b(?:coconut|almond|soy|soya|oat|rice|cashew|hemp|pea|pistachio)"
            r"[\s\-]*(?:milk|butter)\b",
            re.I,
        ),
        {"dairy"},
    ),
    (re.compile(r"\bpeanut\s+butter\b", re.I), {"dairy"}),
    (re.compile(r"\bcocoa\s+butter\b", re.I), {"dairy"}),
    (re.compile(r"\bshea\s+butter\b", re.I), {"dairy"}),
)


def hazard_hits_in_text(text: str) -> set[str]:
    """Return hazard class names found as surface forms in ``text``."""
    if not text:
        return set()
    hits: set[str] = set()
    for cls, pat in _PATTERNS.items():
        if pat.search(text):
            hits.add(cls)
    for pat, drop in _NEGATED:
        if pat.search(text):
            hits -= drop
    return hits


def hazard_hits_in_atoms(atoms: Iterable[str]) -> set[str]:
    """Union of hazard classes found across parsed atoms."""
    hits: set[str] = set()
    for a in atoms:
        hits |= hazard_hits_in_text(a or "")
    return hits


def conservation_misses(raw: str, atoms: Iterable[str]) -> set[str]:
    """Hazard classes present in raw text but absent from parsed atoms."""
    return hazard_hits_in_text(raw) - hazard_hits_in_atoms(atoms)


# Lexicon class -> compliance flag column (allergy/medical).
HAZARD_CLASS_TO_FLAG: dict[str, str] = {
    "peanut": "peanut_source",
    "gluten": "gluten_source",
    "dairy": "dairy_source",
    "egg": "egg_source",
    "soy": "soy_source",
    "sesame": "sesame_source",
    "fish": "fish_source",
    "shellfish": "shellfish_source",
    "tree_nut": "tree_nut_source",
}


_MAY_CONTAIN_SPLIT = re.compile(
    r"(?i)(?:^|[.\n])\s*(?:may\s+contain|traces?\s+of)\s*[:\-]?\s*"
)


def label_text_hazard_inputs(raw: str):
    """Product-level ComplianceInputs from raw label surface forms.

    Positives only — absence of a hit is never negative evidence. Attribution
    is the canonical name ``label text`` so audits show the source.

    Hazards found only under a ``may contain`` / ``traces of`` clause are
    marked ``may_contain=True`` (lifestyle → WARN/UNCERTAIN; medical → FAIL).
    """
    from core.knowledge.ike2.seam import ComplianceInput

    text = raw or ""
    if not text.strip():
        return []

    # Split definite body vs trailing may-contain clause (last match wins).
    may_parts = _MAY_CONTAIN_SPLIT.split(text)
    if len(may_parts) >= 2:
        definite = may_parts[0]
        may_body = may_parts[-1]
    else:
        definite = text
        may_body = ""

    outs = []
    for body, may_contain in ((definite, False), (may_body, True)):
        if not (body or "").strip():
            continue
        hits = hazard_hits_in_text(body)
        flags = {HAZARD_CLASS_TO_FLAG[c]: True for c in hits if c in HAZARD_CLASS_TO_FLAG}
        if not flags:
            continue
        outs.append(
            ComplianceInput(
                canonical_name="label text",
                flags=flags,
                knowledge_state="AUTO_CLASSIFIED",
                trusted=True,
                alcohol_role=None,
                verdict_cap=None,
                trace=False,
                may_contain=may_contain,
            )
        )
    return outs
