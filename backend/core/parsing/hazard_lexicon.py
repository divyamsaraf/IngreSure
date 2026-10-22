"""Surface-form hazard lexicon for parser conservation and atom flag derive.

Single source for raw-string sweep and ``flag_derive``: tokens, false-friend
exclusions, and free-from / negation guards. Positives only — absence of a hit
is never negative evidence.
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
        "rolled oats",
        "oat flour",
        "oatmeal",
        "oats",
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
        "caseinate",
        "caseinates",
        "casein",
        "lactose",
        "yoghurt",
        "yogurt",
        "milk",
        "lait",
        "beurre",
        "fromage",
        "milch",
        "käse",
        "leche",
        "mantequilla",
        "queso",
        "latte",
        "burro",
        "formaggio",
        "melk",
        "boter",
        "kaas",
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
        "huevo",
        "uovo",
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


# Plant modifier adjacent to an animal-product noun → mask (structural rule).
# EN/FR/DE/ES/IT/NL. Span-blanking only: an independent animal token elsewhere
# in the same string still fires (e.g. "almond milk, milk").
_PLANT_MOD = (
    r"(?:coconut|almond|soy|soya|oat|rice|cashew|hemp|pea|pistachio|tofu|"
    r"cocoa|cacao|shea|peanut|groundnut|apple|seed|kokum|"
    r"plant[\s\-]*based|vegetable|vegan|vegetarian|"
    r"coco|amande|avoine|soja|riz|cajou|karit[eé]|cacahu[eè]te|arachide|"
    r"kokos|mandel|hafer|erdnuss|almendra|avena|arroz|"
    r"cocco|mandorla|soia|riso|amandel)"
)
_ANIMAL_NOUN = (
    r"(?:milk|cream|butter|yogurt|yoghurt|cheese|egg|eggs|"
    r"chicken|meat|beef|pork|fish|"
    r"lait|beurre|cr[eè]me|fromage|oeuf|œuf|"
    r"milch|butter|k[aä]se|joghurt|jogurt|eier|"
    r"leche|mantequilla|queso|huevo|"
    r"latte|burro|formaggio|uovo|"
    r"melk|boter|kaas|ei|"
    r"drink)"  # Haferdrink / oat drink class
)
# plant + animal (almond milk, vegan egg, plant-based chicken, cashew cheese).
# Group 1 = plant (kept), group 2 = separator+animal (blanked).
_STRUCT_PLANT_ANIMAL = re.compile(
    rf"(?ix)\b({_PLANT_MOD})([\s\-]+{_ANIMAL_NOUN})\b"
)
# FR/ES/IT animal de plant — blank animal+"de", keep plant (peanut in cacahuète).
_STRUCT_ANIMAL_DE_PLANT = re.compile(
    rf"(?ix)\b({_ANIMAL_NOUN}\s+(?:de\s+|d['\u2019]\s*))({_PLANT_MOD})\b"
)
# Closed German/Dutch compounds (Hafermilch, Sojajoghurt, Kakaobutter, Haferdrink)
_STRUCT_COMPOUND = re.compile(
    r"""(?ix)\b(?:
        (?:kokos|mandel|hafer|soja|erdnuss|kakao|cacao|shea|amandel)
        (?:milch|butter|joghurt|jogurt|drink|kaas|melk|boter)
      | kakaobutter | cacaoboter
    )\b"""
)

# Non-structural false friends (not plant+animal adjacency).
_SPECIAL_FALSE_FRIEND_MASK = re.compile(
    r"""(?ix)
    (?:
        butter\s*bean | butternut
      | cream\s+of\s+tartar | cream\s+soda
      | milk\s+thistle | milkweed | milkfish | milk\s+fish
      | lobster\s+mushroom | crab\s+mushroom
        # coconut is not a tree-nut under our policy
      | noix\s+de\s+coco | nuez\s+de\s+coco | kokosnuss
      | noce\s+di\s+cocco | kokosnoot
    )
    """
)

# Free-from / negation claims — mask so "soya free" / "NO SOY" / "sans gluten"
# do not count as hazard presence.
_NEGATION_MASK = re.compile(
    r"""(?ix)
    (?:
        (?:gluten|dairy|milk|lactose|soy|soya|soybean|nut|peanut|egg|eggs|
           sesame|wheat|fish|shellfish|tree[\s\-]*nut)
        [\s\-]*free
        # claim + residual noun in the same phrase (dairy-free cheese)
        (?:\s+(?:cheese|butter|creamer|cream|milk|yogurt|yoghurt|eggs?))?
      | free[\s\-]+(?:from[\s\-]+)?
        (?:gluten|dairy|milk|lactose|soy|soya|soybean|nut|peanut|egg|eggs|
           sesame|wheat|fish|shellfish|tree[\s\-]*nut)s?
      | (?:no|non|without|sans|ohne|sin|senza|zonder)[\s\-]+
        (?:added[\s\-]+)?
        (?:gluten|dairy|milk|lactose|soy|soya|soybean|nut|peanut|egg|eggs|
           sesame|wheat|fish|shellfish|tree[\s\-]*nut|milch|lait|soja|blé)s?
        (?:\s+(?:cheese|butter|creamer|cream|milk|yogurt|yoghurt|eggs?))?
      | contains\s+no\s+
        (?:gluten|dairy|milk|lactose|soy|soya|soybean|nut|peanut|egg|eggs|
           sesame|wheat)s?
    )
    """
)


def _blank(m: re.Match[str]) -> str:
    return " " * len(m.group(0))


def _blank_keep_plant_first(m: re.Match[str]) -> str:
    """Keep plant modifier (g1), blank animal tail (g2)."""
    return m.group(1) + (" " * len(m.group(2)))


def _blank_keep_plant_second(m: re.Match[str]) -> str:
    """Blank animal+de (g1), keep plant (g2)."""
    return (" " * len(m.group(1))) + m.group(2)


def mask_non_hazards(text: str) -> str:
    """Blank plant+animal false-friend spans and free-from claims before match.

    Structural rule: animal-product noun adjacent to a plant modifier is masked
    unless the animal token also appears independently elsewhere in the string.
    Plant tokens are preserved so peanut in "beurre de cacahuète" still hits.
    """
    if not text:
        return text
    masked = _STRUCT_PLANT_ANIMAL.sub(_blank_keep_plant_first, text)
    masked = _STRUCT_ANIMAL_DE_PLANT.sub(_blank_keep_plant_second, masked)
    masked = _STRUCT_COMPOUND.sub(_blank, masked)
    masked = _SPECIAL_FALSE_FRIEND_MASK.sub(_blank, masked)
    masked = _NEGATION_MASK.sub(_blank, masked)
    return masked


# Back-compat alias for callers that imported the private name.
_mask_non_hazards = mask_non_hazards


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

_ANIMAL_CLASSES = frozenset({"dairy", "egg", "fish", "shellfish"})


def family_negated(name: str, tokens: Iterable[str]) -> bool:
    """True when ``name`` is a free-from / contains-no claim for any of ``tokens``.

    Shared by flag_derive and the sweep so "soya free" / "sans lait" agree.
    """
    if not name:
        return False
    low = name.lower()
    for tok in tokens:
        t = re.escape(tok)
        if re.search(rf"\b{t}s?[\s-]*free\b", low):
            return True
        if re.search(rf"\bfree[\s-]+(?:from[\s-]+)?{t}s?\b", low):
            return True
        if re.search(
            rf"\b(?:no|non|without|sans|ohne|sin|senza|zonder)[\s-]+(?:added[\s-]+)?{t}s?\b",
            low,
        ):
            return True
        if re.search(rf"\bcontains\s+no\s+{t}s?\b", low):
            return True
    return False


def hazard_hits_in_text(text: str) -> set[str]:
    """Return hazard class names found as surface forms in ``text``."""
    if not text:
        return set()
    masked = _mask_non_hazards(text)
    hits: set[str] = set()
    for cls, pat in _PATTERNS.items():
        if pat.search(masked):
            hits.add(cls)
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


def apply_lexicon_flags(name: str, flags: dict | None = None) -> dict:
    """OR lexicon hazard hits onto a flags dict (atom-level derive path).

    Free-from / non-dairy claims are handled by masking in ``hazard_hits_in_text``;
    independent dairy tokens (e.g. caseinate after a non-dairy claim) still fire.
    """
    out = dict(flags or {})
    raw = name or ""
    for cls in hazard_hits_in_text(raw):
        flag = HAZARD_CLASS_TO_FLAG.get(cls)
        if not flag:
            continue
        out[flag] = True
        if cls in _ANIMAL_CLASSES:
            out["animal_origin"] = True
            out["plant_origin"] = False
    return out


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
