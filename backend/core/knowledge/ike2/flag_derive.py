"""Derive allergen/diet flags from identity fields (systemic, not per-ingredient).

Single place used by ETL ``map_record`` and commodity promotion so chat,
Tier-2 ontology, and bulk inject stay consistent.

Rules (fail-closed for allergens):
  - animal_species fish/shellfish => fish_source / shellfish_source
  - canonical name token peanut/sesame/soy => matching *_source
  - tree-nut tokens => tree_nut_source, with explicit non-triggers
    (water chestnut, coconut*, nutmeg, butternut squash)
  - egg tokens => egg_source, never from \"eggplant\"
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from core.normalization.normalizer import normalize_ingredient_key

_TREE_NUT_TOKENS = frozenset({
    "almond", "hazelnut", "filbert", "cashew", "walnut", "pecan", "pistachio",
    "macadamia", "brazil", "pinenut", "pine", "chestnut", "praline",
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

_SHELLFISH_SPECIES = frozenset({
    "shellfish", "crustacean", "crustaceans", "mollusk", "mollusks",
    "shrimp", "prawn", "crab", "lobster", "clam", "mussel", "oyster",
    "scallop", "squid", "octopus",
})

_EGG_NAMES = frozenset({
    "egg", "eggs", "egg white", "egg whites", "egg yolk", "egg yolks",
    "chicken egg", "chicken eggs", "duck egg", "duck eggs",
    "quail egg", "quail eggs",
})


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

    # --- name tokens => allergen flags ---
    if _has_token(name, "peanut") or name.startswith("peanut"):
        out["peanut_source"] = True

    if _has_token(name, "sesame") or "sesame" in name:
        out["sesame_source"] = True

    if _has_token(name, "soy") or _has_token(name, "soya") or name.startswith("soy"):
        # avoid "soy" inside unrelated tokens; startswith/token is enough
        out["soy_source"] = True
    if name in ("edamame", "soya", "soybean", "soybeans"):
        out["soy_source"] = True

    if name in _EGG_NAMES or (
        (_has_token(name, "egg") or _has_token(name, "eggs"))
        and "eggplant" not in name
        and "egg plant" not in name
    ):
        out["egg_source"] = True
        out["animal_origin"] = True
        out["plant_origin"] = False
        if not out.get("animal_species"):
            out["animal_species"] = "bird"

    if not _is_non_tree_nut(name):
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

    return out
