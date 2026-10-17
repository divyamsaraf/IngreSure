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


# Plant milks / cocoa butters / milk thistle — mask before matching so FR/DE/ES
# forms do not fire dairy (sweep previously missed these; flag_derive had EN only).
_FALSE_FRIEND_MASK = re.compile(
    r"""(?ix)
    (?:
        # cocoa / cacao butter (EN + FR/DE/ES/IT/NL)
        (?:cocoa|cacao)\s+butter
        | beurre\s+de\s+cacao
        | kakaobutter
        | manteca\s+de\s+cacao
        | burro\s+di\s+cacao
        | cacaoboter
        # plant milks
        | (?:coconut|almond|soy|soya|oat|rice|cashew|hemp|pea|pistachio)
          [\s\-]*(?:milk|cream|butter|yogurt|yoghurt)
        | lait\s+de\s+(?:coco|amande|avoine|soja|riz|cajou)
        | lait\s+d['\u2019]?\s*amande
        | leche\s+de\s+(?:coco|almendra|avena|soja|arroz)
        | kokosmilch
        | mandelmilch
        | hafermilch
        | sojamilch
        | latte\s+di\s+(?:cocco|mandorla|avena|soia|riso)
        | kokosmelk
        | amandelmelk
        | shea\s+butter
        | kokum\s+butter
        | peanut\s+butter
        | almond\s+butter
        | cashew\s+butter
        | seed\s+butter
        | apple\s+butter
        | butter\s*bean
        | butternut
        | cream\s+of\s+tartar
        | cream\s+soda
        | milk\s+thistle
        | milkweed
        | milkfish
        | milk\s+fish
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
      | free[\s\-]+(?:from[\s\-]+)?
        (?:gluten|dairy|milk|lactose|soy|soya|soybean|nut|peanut|egg|eggs|
           sesame|wheat|fish|shellfish|tree[\s\-]*nut)s?
      | (?:no|without|sans|ohne|sin|senza|zonder)[\s\-]+
        (?:added[\s\-]+)?
        (?:gluten|dairy|milk|lactose|soy|soya|soybean|nut|peanut|egg|eggs|
           sesame|wheat|fish|shellfish|tree[\s\-]*nut|milch|lait|soja|blé)s?
      | contains\s+no\s+
        (?:gluten|dairy|milk|lactose|soy|soya|soybean|nut|peanut|egg|eggs|
           sesame|wheat)s?
    )
    """
)


def _mask_non_hazards(text: str) -> str:
    """Blank out false-friend and free-from spans before lexicon match."""
    if not text:
        return text
    masked = _FALSE_FRIEND_MASK.sub(lambda m: " " * len(m.group(0)), text)
    masked = _NEGATION_MASK.sub(lambda m: " " * len(m.group(0)), masked)
    return masked


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
            rf"\b(?:no|without|sans|ohne|sin|senza|zonder)[\s-]+(?:added[\s-]+)?{t}s?\b",
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


# Tokens used to suppress a class when the whole phrase is a free-from claim
# (e.g. "dairy free cheese" must not pick up dairy from residual "cheese").
_CLASS_NEGATION_TOKENS: dict[str, tuple[str, ...]] = {
    "peanut": ("peanut", "groundnut"),
    "gluten": ("gluten", "wheat", "barley", "rye"),
    "dairy": ("dairy", "milk", "lactose", "whey", "casein", "lait", "milch", "leche"),
    "egg": ("egg", "eggs"),
    "soy": ("soy", "soya", "soybean", "soja"),
    "sesame": ("sesame", "tahini"),
    "fish": ("fish", "poisson", "fisch"),
    "shellfish": ("shellfish", "crustacean", "mollusk", "mollusc"),
    "tree_nut": ("nut", "tree nut", "treenut", "almond", "amande"),
}


def apply_lexicon_flags(name: str, flags: dict | None = None) -> dict:
    """OR lexicon hazard hits onto a flags dict (atom-level derive path)."""
    out = dict(flags or {})
    raw = name or ""
    for cls in hazard_hits_in_text(raw):
        toks = _CLASS_NEGATION_TOKENS.get(cls)
        if toks and family_negated(raw, toks):
            continue
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
