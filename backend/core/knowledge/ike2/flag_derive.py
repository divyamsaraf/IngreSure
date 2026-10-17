"""Derive allergen/diet flags from identity fields (systemic, not per-ingredient).

Single place used by ETL ``map_record`` and commodity promotion so chat,
Tier-2 ontology, and bulk inject stay consistent.

Rules (fail-closed for allergens):
  - animal_species fish/shellfish => fish_source / shellfish_source
  - canonical name token peanut/sesame/soy => matching *_source
  - tree-nut tokens => tree_nut_source, with explicit non-triggers
    (water chestnut, coconut*, nutmeg, butternut squash)
  - egg tokens => egg_source, never from \"eggplant\"
  - wheat/atta/maida/semolina/suji => gluten_source (never buckwheat)
  - groundnut => peanut_source (not tree-nut)
  - yeast / mushroom / tempeh / mycoprotein / koji tokens => fungal
  - sulfite / sulphite / bisulfite / metabisulfite / sulfur dioxide => sulphite_source
    (never sulfate / sulphate / acesulfame)
  - dairy tokens (milk/casein/whey/…) with plant-milk / cocoa-butter exclusions
  - lupin / lupine / lupini => lupin_source
  - mustard (not mustard greens/spinach/oil alone as allergen seed)
  - celery / celeriac => celery_source
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from core.normalization.normalizer import normalize_ingredient_key

_TREE_NUT_TOKENS = frozenset({
    "almond", "hazelnut", "filbert", "cashew", "walnut", "pecan", "pistachio",
    "macadamia", "brazil", "pinenut", "pine", "chestnut", "praline",
    # Indian vernacular (cashew / almond / pistachio / walnut)
    "kaju", "badam", "pista", "akhrot",
})

# Phrases that contain a tree-nut substring/token but are not tree-nut allergens
# for our policy (or would false-trigger token matching).
_NON_TREE_NUT_PHRASES = (
    "water chestnut",
    "waterchestnuts",
    "coconut",
    "nutmeg",
    "butternut",
    "groundnut oil",  # regional peanut name handled via peanut; do not also tree-nut
)

_GLUTEN_NAMES = frozenset({
    "wheat", "wheat flour", "whole wheat flour", "atta", "maida", "semolina",
    "suji", "sooji", "rava", "all purpose flour", "allpurpose flour",
    "barley", "rye", "spelt", "kamut", "farro", "freekeh", "bulgur",
    "couscous", "seitan", "graham flour", "durum", "durum wheat",
    "einkorn", "khorasan", "khorasan wheat", "gluten",
    "chapati", "chapatti", "roti", "paratha", "naan", "puri", "dalia",
})
_GLUTEN_TOKENS = frozenset({
    "wheat", "barley", "rye", "spelt", "einkorn", "khorasan", "seitan",
    "semolina", "atta", "maida", "suji", "sooji", "rava", "farro", "freekeh",
    "bulgur", "couscous", "kamut", "durum", "gluten",
    "chapati", "chapatti", "roti", "paratha", "naan", "puri", "dalia",
})
# Rice-marked "rava" forms — do not auto-set gluten from the rava token.
# (Truth anchor / ontology may still WARN-cap idli/rice rava; brands blend.)
_NON_GLUTEN_RAVA_PHRASES = (
    "idli rava",
    "idli ravai",
    "rice rava",
    "rice sooji",
    "rice suji",
)

_DAIRY_TOKENS = frozenset({
    "milk", "casein", "caseinate", "whey", "lactose", "lactalbumin",
    "butter", "buttermilk", "cream", "yogurt", "yoghurt", "cheese", "ghee",
    "curd", "paneer",
    # Indian vernacular
    "dahi", "khoa", "mawa", "lassi", "chaas", "malai",
})
_NON_DAIRY_PHRASES = (
    "coconut milk", "coconut cream", "almond milk", "oat milk", "soy milk",
    "soya milk", "rice milk", "hemp milk", "cashew milk", "pea milk",
    "milk thistle", "milkweed", "milkfish", "milk fish",
    "shea butter", "cocoa butter", "cacao butter", "peanut butter",
    "almond butter", "cashew butter", "seed butter", "apple butter",
    "butter bean", "butterbean", "butternut", "cream of tartar", "cream soda",
    "kokum butter",
    "tofu yogurt", "tofu yoghurt", "soy yogurt", "soy yoghurt",
    "coconut yogurt", "oat yogurt", "almond yogurt",
)

_MUSTARD_NON_ALLERGEN_PHRASES = (
    "mustard green", "mustard greens", "mustard spinach", "mustard oil",
    "sarson oil", "sarson ka tel",
)
_MUSTARD_TOKENS = frozenset({"mustard", "rai", "sarson"})

_SHELLFISH_SPECIES = frozenset({
    "shellfish", "crustacean", "crustaceans", "mollusk", "mollusks",
    "shrimp", "prawn", "crab", "lobster", "clam", "mussel", "oyster",
    "scallop", "squid", "octopus",
})

_EGG_NAMES = frozenset({
    "egg", "eggs", "egg white", "egg whites", "egg yolk", "egg yolks",
    "chicken egg", "chicken eggs", "duck egg", "duck eggs",
    "quail egg", "quail eggs",
    "anda",  # Hindi
})

# Fungal / yeast-culture identity — drives Jain fungal FAIL (and similar diet rules).
# Token "yeast" covers yeast extract, nutritional yeast, baker's yeast, etc.
# Explicit whole-name set covers fermented fungal foods that lack the yeast token.
_FUNGAL_NAME_TOKENS = frozenset({
    "yeast",
    "mushroom",
    "shiitake",
    "portobello",
    "portabella",
    "cremini",
    "chanterelle",
    "enoki",
    "maitake",
    "mycoprotein",
    "quorn",
    "koji",
    "tempeh",
    "torula",
    "aspergillus",
    "penicillium",
})
_FUNGAL_WHOLE_NAMES = frozenset({
    "tempeh",
    "mycoprotein",
    "quorn",
    "koji",
    "marmite",
    "vegemite",
    "yeast extract",
    "yeast extract spread",
})

# High-confidence animal enzyme name tokens / wholes (Item 3.1 Prompt 3).
# Fail-closed: only explicit animal enzyme vocabulary — no fuzzy "enzyme" alone.
_ANIMAL_ENZYME_WHOLE_NAMES = frozenset({
    "rennet",
    "animal rennet",
    "pepsin",
    "trypsin",
    "chymotrypsin",
    "pancreatin",
    "lipase animal",
})
_ANIMAL_ENZYME_TOKENS = frozenset({
    "rennet",
    "pepsin",
    "trypsin",
    "chymotrypsin",
    "pancreatin",
})

# EU/US declarable sulfites (SO2 liberators). Do not match sulfate/sulphate salts
# or acesulfame (sweetener) — substring "sulf" is too broad.
_SULPHITE_TOKENS = frozenset({
    "sulfite",
    "sulphite",
    "bisulfite",
    "bisulphite",
    "metabisulfite",
    "metabisulphite",
    "disulfite",
    "disulphite",
    "pyrosulfite",
    "pyrosulphite",
    # Fruit/veg SO2 treatment labels (not sulfate/sulphate/sulfated).
    "sulfured",
    "sulphured",
    "sulfited",
    "sulphited",
})
_SULPHITE_PHRASES = (
    "sulfur dioxide",
    "sulphur dioxide",
)
_SULPHITE_E_CODES = frozenset({f"e22{i}" for i in range(9)})


def _tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[\s\-_/,]+", name) if t]


def _has_token(name: str, token: str) -> bool:
    """Whole-token match (handles simple plurals)."""
    tok = token.lower()
    for part in _tokens(name):
        if part == tok or part == tok + "s" or (tok.endswith("s") and part == tok[:-1]):
            return True
        # pine nut: token "pine" alone is weak; require pine+nut elsewhere
    return False


def _is_non_tree_nut(name: str) -> bool:
    return any(p in name for p in _NON_TREE_NUT_PHRASES)


def _family_negated(name: str, tokens: tuple[str, ...] | frozenset[str] | list[str]) -> bool:
    """True when the label is a free-from / contains-no claim for this family.

    Suppresses identity derive for that family only (dairy-free cheese must not
    pick up dairy from \"dairy\"; egg-free pasta must not pick up egg).
    """
    for tok in tokens:
        t = re.escape(tok)
        if re.search(rf"\b{t}s?[\s-]*free\b", name):
            return True
        if re.search(rf"\bfree[\s-]+(?:from[\s-]+)?{t}s?\b", name):
            return True
        if re.search(rf"\b(?:no|without)[\s-]+(?:added[\s-]+)?{t}s?\b", name):
            return True
        if re.search(rf"\bcontains\s+no\s+{t}s?\b", name):
            return True
    return False


# Token → family tokens used for free-from negation (compound expand + derive).
_KEYWORD_NEGATION_FAMILY: dict[str, tuple[str, ...]] = {
    "egg": ("egg", "eggs"),
    "eggs": ("egg", "eggs"),
    "milk": ("dairy", "milk", "lactose", "whey", "casein"),
    "cheese": ("dairy", "milk", "lactose", "whey", "casein", "cheese"),
    "butter": ("dairy", "milk", "lactose", "whey", "casein", "butter"),
    "cream": ("dairy", "milk", "lactose", "whey", "casein", "cream"),
    "yogurt": ("dairy", "milk", "lactose", "whey", "casein", "yogurt"),
    "ghee": ("dairy", "milk", "lactose", "whey", "casein", "ghee"),
    "paneer": ("dairy", "milk", "lactose", "whey", "casein", "paneer"),
    "whey": ("dairy", "milk", "lactose", "whey", "casein"),
    "curd": ("dairy", "milk", "lactose", "whey", "casein", "curd"),
    "dahi": ("dairy", "milk", "lactose", "whey", "casein", "dahi", "curd"),
    "khoa": ("dairy", "milk", "lactose", "whey", "casein", "khoa"),
    "mawa": ("dairy", "milk", "lactose", "whey", "casein", "mawa"),
    "anda": ("egg", "eggs", "anda"),
    "peanut": ("peanut", "groundnut"),
    "wheat": ("gluten", "wheat", "barley", "rye"),
    "barley": ("gluten", "wheat", "barley", "rye"),
    "rye": ("gluten", "wheat", "barley", "rye"),
    "atta": ("gluten", "wheat", "barley", "rye", "atta"),
    "maida": ("gluten", "wheat", "barley", "rye", "maida"),
    "soy": ("soy", "soya", "soybean"),
    "tofu": ("soy", "soya", "soybean"),
    "almond": ("nut", "almond", "tree nut"),
    "walnut": ("nut", "walnut", "tree nut"),
    "cashew": ("nut", "cashew", "tree nut"),
    "hazelnut": ("nut", "hazelnut", "tree nut"),
    "pecan": ("nut", "pecan", "tree nut"),
    "kaju": ("nut", "cashew", "tree nut", "kaju"),
    "badam": ("nut", "almond", "tree nut", "badam"),
    "pista": ("nut", "pistachio", "tree nut", "pista"),
    "til": ("sesame", "tahini", "til"),
    "rai": ("mustard", "rai"),
    "sarson": ("mustard", "sarson"),
}


def keyword_negated_in_phrase(phrase: str, keyword: str) -> bool:
    """True when ``keyword`` appears only inside a free-from / contains-no claim."""
    name = normalize_ingredient_key(phrase or "")
    if not name or not keyword:
        return False
    family = _KEYWORD_NEGATION_FAMILY.get(keyword.lower()) or (keyword.lower(),)
    return _family_negated(name, family)


def is_free_from_claim(phrase: str) -> bool:
    """True when the phrase looks like any allergen free-from / contains-no claim."""
    name = normalize_ingredient_key(phrase or "")
    if not name:
        return False
    if re.search(r"\bcontains\s+no\b", name) or re.search(r"\bno\s+added\s+sulph?ites?\b", name):
        return True
    if re.search(r"\bfree[\s-]+from\b", name):
        return True
    if re.search(r"\b[\w]+[\s-]*free\b", name):
        return True
    return False


def derive_identity_flags(
    canonical_name: str,
    flags: Mapping[str, Any] | None = None,
    *,
    animal_species: str | None = None,
) -> dict[str, Any]:
    """Return a new flags dict with identity-derived allergen bits OR-ed in."""
    out: dict[str, Any] = dict(flags or {})
    name = normalize_ingredient_key(canonical_name or "")
    species = (animal_species if animal_species is not None else out.get("animal_species")) or ""
    species_l = str(species).strip().lower()

    # --- species => allergen source flags (never under-flag fish) ---
    if species_l == "fish" or species_l.startswith("fish"):
        out["fish_source"] = True
        out["animal_origin"] = True
        out["plant_origin"] = False
    if species_l in _SHELLFISH_SPECIES or any(s in species_l for s in ("shellfish", "crustacean", "mollusk")):
        out["shellfish_source"] = True
        out["animal_origin"] = True
        out["plant_origin"] = False

    if not name:
        return out

    neg_peanut = _family_negated(name, ("peanut", "groundnut"))
    neg_gluten = _family_negated(name, ("gluten", "wheat", "barley", "rye"))
    neg_sesame = _family_negated(name, ("sesame", "tahini"))
    neg_soy = _family_negated(name, ("soy", "soya", "soybean"))
    neg_lupin = _family_negated(name, ("lupin", "lupine", "lupini"))
    neg_mustard = _family_negated(name, ("mustard",))
    neg_celery = _family_negated(name, ("celery", "celeriac"))
    neg_dairy = _family_negated(name, ("dairy", "milk", "lactose", "whey", "casein"))
    neg_egg = _family_negated(name, ("egg", "eggs"))
    neg_shellfish = _family_negated(name, ("shellfish", "crustacean", "mollusk", "mollusc"))
    neg_tree_nut = _family_negated(name, ("nut", "tree nut", "treenut", *_TREE_NUT_TOKENS))
    neg_sulphite = _family_negated(
        name, ("sulphite", "sulfite", "sulphur", "sulfur")
    ) or bool(re.search(r"\bno\s+added\s+sulph?ites?\b", name))

    # --- name tokens => allergen flags ---
    if not neg_peanut and (
        _has_token(name, "peanut")
        or name.startswith("peanut")
        or _has_token(name, "groundnut")
        or name.startswith("groundnut")
        or "groundnut" in name
    ):
        out["peanut_source"] = True

    non_gluten_rava = any(p in name for p in _NON_GLUTEN_RAVA_PHRASES)
    if not neg_gluten and not non_gluten_rava and (
        name in _GLUTEN_NAMES
        or (
            any(_has_token(name, t) for t in _GLUTEN_TOKENS)
            and "buckwheat" not in name
            and "buck wheat" not in name
        )
    ):
        out["gluten_source"] = True

    if not neg_sesame and (
        _has_token(name, "sesame")
        or "sesame" in name
        or _has_token(name, "tahini")
        or name.startswith("tahini")
        or _has_token(name, "til")
    ):
        out["sesame_source"] = True

    if not neg_soy and (
        _has_token(name, "soy") or _has_token(name, "soya") or name.startswith("soy")
    ):
        out["soy_source"] = True
    if not neg_soy and name in ("edamame", "soya", "soybean", "soybeans"):
        out["soy_source"] = True

    if not neg_lupin and (
        _has_token(name, "lupin")
        or _has_token(name, "lupine")
        or _has_token(name, "lupini")
        or name.startswith("lupin")
    ):
        out["lupin_source"] = True

    if not neg_mustard and not any(p in name for p in _MUSTARD_NON_ALLERGEN_PHRASES):
        if any(_has_token(name, t) for t in _MUSTARD_TOKENS):
            out["mustard_source"] = True

    if not neg_celery and (
        _has_token(name, "celery") or _has_token(name, "celeriac") or "celeriac" in name
    ):
        out["celery_source"] = True

    if (
        not neg_dairy
        and not any(p in name for p in _NON_DAIRY_PHRASES)
        and any(_has_token(name, t) for t in _DAIRY_TOKENS)
    ):
        out["dairy_source"] = True
        out["animal_origin"] = True
        out["plant_origin"] = False

    # shellfish umbrella labels (species path already covers shrimp/crab/…)
    if not neg_shellfish and any(
        _has_token(name, t)
        for t in ("crustacean", "crustaceans", "mollusk", "mollusks", "mollusc", "molluscs", "shellfish")
    ):
        out["shellfish_source"] = True
        out["animal_origin"] = True
        out["plant_origin"] = False

    if not neg_egg and (
        name in _EGG_NAMES
        or _has_token(name, "anda")
        or (
            (_has_token(name, "egg") or _has_token(name, "eggs"))
            and "eggplant" not in name
            and "egg plant" not in name
        )
    ):
        out["egg_source"] = True
        out["animal_origin"] = True
        out["plant_origin"] = False
        if not out.get("animal_species"):
            out["animal_species"] = "bird"

    # --- fungal / yeast-culture identity (never under-flag Jain fungal FAIL) ---
    if name in _FUNGAL_WHOLE_NAMES or any(
        _has_token(name, tok) for tok in _FUNGAL_NAME_TOKENS
    ):
        out["fungal"] = True

    # --- animal enzyme subtype (Item 3.1); bare "enzymes" stays unknown ---
    if name in _ANIMAL_ENZYME_WHOLE_NAMES or any(
        _has_token(name, tok) for tok in _ANIMAL_ENZYME_TOKENS
    ):
        # "microbial rennet" / "vegetarian rennet" are not animal.
        if "microbial" not in name and "vegetarian" not in name and "vegan" not in name:
            out["enzyme_animal_source"] = True
            out["animal_origin"] = True
            out["plant_origin"] = False

    if not neg_tree_nut and not _is_non_tree_nut(name):
        # pine nut: need both pine and nut, or pinenut
        tokens = set(_tokens(name))
        if "pinenut" in name.replace(" ", "") or (
            "pine" in tokens and ("nut" in tokens or "nuts" in tokens)
        ):
            out["tree_nut_source"] = True
        elif any(_has_token(name, t) for t in _TREE_NUT_TOKENS if t not in ("pine",)):
            out["tree_nut_source"] = True
        elif _has_token(name, "brazil"):
            out["tree_nut_source"] = True

    # --- sulfites (never sulfate/sulphate; never acesulfame) ---
    if not neg_sulphite and (
        name in _SULPHITE_E_CODES
        or any(p in name for p in _SULPHITE_PHRASES)
        or any(_has_token(name, t) for t in _SULPHITE_TOKENS)
    ):
        out["sulphite_source"] = True

    return out
