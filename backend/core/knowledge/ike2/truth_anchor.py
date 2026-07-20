from dataclasses import dataclass
import json
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class TruthAnchorFact:
    canonical_name: str
    flags: dict
    knowledge_state: str = "LOCKED"


def _f(**kw):
    return kw


_ANCHORS: dict[str, TruthAnchorFact] = {}

# E-number keys removed from hand curation — covered by generated map below.
_E_NUMBER_KEYS = frozenset({
    "e120", "e441", "e901", "e904", "e542", "e631", "e920", "e966", "e1105",
})


def _add(keys, canonical, flags, *, knowledge_state: str = "LOCKED"):
    fact = TruthAnchorFact(canonical_name=canonical, flags=flags, knowledge_state=knowledge_state)
    for k in keys:
        if k not in _E_NUMBER_KEYS:
            _ANCHORS[k] = fact


def _add_compound(keys, canonical):
    """Unresolvable compound terms: never firm-SAFE (design §4B)."""
    _add(keys, canonical, _f(verdict_cap="WARN"), knowledge_state="VERIFIED")


_E_NUMBER_ANCHORS: dict[str, TruthAnchorFact] | None = None


def _load_e_number_anchors() -> dict[str, TruthAnchorFact]:
    path = Path(__file__).with_name("truth_anchor_e_numbers.json")
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, TruthAnchorFact] = {}
    for key, payload in raw.items():
        flags = dict(payload.get("flags") or {})
        out[key] = TruthAnchorFact(
            canonical_name=payload["canonical_name"],
            flags=flags,
            knowledge_state=payload.get("knowledge_state", "LOCKED"),
        )
    return out


def _e_number_anchors() -> dict[str, TruthAnchorFact]:
    global _E_NUMBER_ANCHORS
    if _E_NUMBER_ANCHORS is None:
        _E_NUMBER_ANCHORS = _load_e_number_anchors()
    return _E_NUMBER_ANCHORS


# --- animal-derived additives (named forms; E-codes from generated map) -------
_add(
    ["gelatin", "gelatine"],
    "gelatin",
    _f(
        animal_origin=True,
        animal_species="bovine/porcine/fish depending on source",
        fish_source=True,
        verdict_cap="WARN",
        uncertainty_flags=["source_species_unspecified_on_label"],
    ),
)
_add(["fish gelatin", "fish_gelatin"], "fish gelatin",
     _f(animal_origin=True, animal_species="fish", fish_source=True))
_add(["carmine", "cochineal", "carminic acid"], "carmine",
     _f(animal_origin=True, insect_derived=True))
_add(["isinglass", "fish bladder"], "isinglass",
     _f(animal_origin=True, animal_species="fish", fish_source=True))
_add(["shellac", "confectioners glaze", "pharmaceutical glaze"], "shellac",
     _f(animal_origin=True, insect_derived=True))
_add(["beeswax"], "beeswax", _f(animal_origin=True, insect_derived=True))
_add(["bone phosphate"], "bone phosphate", _f(animal_origin=True))
_add(["disodium inosinate"], "disodium inosinate", _f(animal_origin=True))
_add(["l-cysteine", "cysteine"], "l-cysteine", _f(animal_origin=True))
_add(["lanolin", "wool grease", "wool wax", "wool fat"], "lanolin", _f(animal_origin=True))
_add(["rennet", "animal rennet"], "rennet", _f(animal_origin=True))
_add(["pepsin"], "pepsin", _f(animal_origin=True))
_add(["collagen"], "collagen", _f(animal_origin=True))
_add(["honey"], "honey", _f(animal_origin=True, bee_product=True))
_add(["castoreum"], "castoreum", _f(animal_origin=True))
_add(["lactitol"], "lactitol", _f(animal_origin=True, dairy_source=True))
_add(["lysozyme"], "lysozyme", _f(animal_origin=True, egg_source=True))

# --- pork / beef species cases -----------------------------------------------
_add(["lard"], "lard", _f(animal_origin=True, animal_species="pig"))
_add(["tallow"], "tallow", _f(animal_origin=True, animal_species="cow"))
_add(["pork", "pepperoni", "salami", "prosciutto"], "pork",
     _f(animal_origin=True, animal_species="pig"))
_add(["bacon", "ham"], "bacon", _f(animal_origin=True, animal_species="pig"))
_add(["beef", "steak"], "beef", _f(animal_origin=True, animal_species="cow"))
_add(["veal"], "veal", _f(animal_origin=True, animal_species="cow"))

# --- fish / shellfish --------------------------------------------------------
_add(["fish", "fish sauce"], "fish",
     _f(animal_origin=True, animal_species="fish", fish_source=True))
_add(["anchovy", "anchovy paste", "anchovy extract"], "anchovy",
     _f(animal_origin=True, animal_species="fish", fish_source=True))
_add(["tuna"], "tuna", _f(animal_origin=True, animal_species="fish", fish_source=True))
_add(["salmon"], "salmon", _f(animal_origin=True, animal_species="fish", fish_source=True))
_add(["cod"], "cod", _f(animal_origin=True, animal_species="fish", fish_source=True))
_add(["sardine"], "sardine", _f(animal_origin=True, animal_species="fish", fish_source=True))
_add(["fish oil"], "fish oil",
     _f(animal_origin=True, animal_species="fish", fish_source=True))
_add(["shellfish"], "shellfish",
     _f(animal_origin=True, shellfish_source=True))
_add(["shrimp", "prawn"], "shrimp",
     _f(animal_origin=True, animal_species="shellfish", shellfish_source=True))
_add(["crab"], "crab", _f(animal_origin=True, shellfish_source=True))
_add(["lobster"], "lobster", _f(animal_origin=True, shellfish_source=True))
_add(["oyster"], "oyster", _f(animal_origin=True, shellfish_source=True))
_add(["clam"], "clam", _f(animal_origin=True, shellfish_source=True))
_add(["mussel"], "mussel", _f(animal_origin=True, shellfish_source=True))
_add(["scallop"], "scallop", _f(animal_origin=True, shellfish_source=True))
_add(["squid"], "squid", _f(animal_origin=True, shellfish_source=True))
_add(["octopus"], "octopus", _f(animal_origin=True, shellfish_source=True))

# --- common allergens: peanuts / tree nuts -----------------------------------
_add(["peanut", "peanut butter", "peanut oil"], "peanut", _f(peanut_source=True))
_add(["almond"], "almond", _f(tree_nut_source=True))
_add(["walnut"], "walnut", _f(tree_nut_source=True))
_add(["cashew"], "cashew", _f(tree_nut_source=True))
_add(["hazelnut"], "hazelnut", _f(tree_nut_source=True))
_add(["pecan"], "pecan", _f(tree_nut_source=True))
_add(["pistachio"], "pistachio", _f(tree_nut_source=True))
_add(["macadamia"], "macadamia", _f(tree_nut_source=True))

# --- dairy / egg -------------------------------------------------------------
_add(["milk", "whole milk", "skim milk"], "milk",
     _f(animal_origin=True, dairy_source=True))
_add(["whey", "whey protein"], "whey", _f(animal_origin=True, dairy_source=True))
_add(["casein", "sodium caseinate", "calcium caseinate"], "casein",
     _f(animal_origin=True, dairy_source=True))
_add(["lactose"], "lactose", _f(animal_origin=True, dairy_source=True))
_add(["butter"], "butter", _f(animal_origin=True, dairy_source=True))
_add(["cream"], "cream", _f(animal_origin=True, dairy_source=True))
_add(["cheese"], "cheese", _f(animal_origin=True, dairy_source=True))
_add(["ghee"], "ghee", _f(animal_origin=True, dairy_source=True))
_add(["yogurt", "yoghurt"], "yogurt", _f(animal_origin=True, dairy_source=True))
_add(["curd"], "curd", _f(animal_origin=True, dairy_source=True))
_add(["egg", "eggs"], "egg", _f(animal_origin=True, egg_source=True))
_add(["egg white"], "egg white", _f(animal_origin=True, egg_source=True))
_add(["egg yolk"], "egg yolk", _f(animal_origin=True, egg_source=True))
_add(["albumin"], "albumin", _f(animal_origin=True, egg_source=True))
_add(["ovalbumin"], "ovalbumin", _f(animal_origin=True, egg_source=True))

# --- gluten / soy / sesame / mustard / celery / lupin / sulphite -------------
_add(["wheat"], "wheat", _f(gluten_source=True))
_add(["gluten"], "gluten", _f(gluten_source=True))
_add(["barley"], "barley", _f(gluten_source=True))
_add(["rye"], "rye", _f(gluten_source=True))
_add(["soy", "soybean", "edamame"], "soy", _f(soy_source=True))
_add(["tofu"], "tofu", _f(soy_source=True))
_add(["tempeh"], "tempeh", _f(soy_source=True))
_add(["soy sauce"], "soy sauce", _f(soy_source=True))
_add(["soy lecithin"], "soy lecithin", _f(soy_source=True))
_add(["sesame", "sesame seed"], "sesame", _f(sesame_source=True))
_add(["tahini"], "tahini", _f(sesame_source=True))
_add(["mustard", "mustard seed"], "mustard", _f(mustard_source=True))
_add(["celery", "celeriac"], "celery", _f(celery_source=True))
_add(["lupin", "lupin flour"], "lupin", _f(lupin_source=True))
_add(["sulphite", "sulfite", "sodium metabisulfite", "potassium metabisulfite"],
     "sulphite", _f(sulphite_source=True))
_add(["wheat flour", "enriched wheat flour", "bleached wheat flour"], "wheat",
     _f(gluten_source=True))
_add(["wheat gluten"], "gluten", _f(gluten_source=True))
_add(["malted barley flour"], "barley", _f(gluten_source=True))
_add(["flour", "all purpose flour"], "flour", _f(gluten_source=True))
_add(["sugar"], "sugar", _f(animal_origin=False, plant_origin=True))
_add(["cane sugar"], "cane sugar", _f(animal_origin=False, plant_origin=True))
_add(["beet sugar"], "beet sugar", _f(animal_origin=False, plant_origin=True))
_add(["chicken"], "chicken", _f(animal_origin=True, animal_species="chicken"))
_add(["potato"], "potato", _f(root_vegetable=True, plant_origin=True))
_add(["water"], "water", _f())
_add(["salt", "sea salt"], "salt", _f())
_add(["yeast"], "yeast", _f())
_add_compound(["enzymes", "enzyme"], "enzymes")

# --- alcohol sources ---------------------------------------------------------
_add(["ethanol", "ethyl alcohol"], "ethanol", _f(alcohol_content=1.0))
_add(["wine"], "wine", _f(alcohol_content=1.0, alcohol_role="ingredient"))
_add(["beer"], "beer", _f(alcohol_content=1.0, alcohol_role="ingredient"))
_add(["vodka"], "vodka", _f(alcohol_content=1.0, alcohol_role="ingredient"))
_add(["rum"], "rum", _f(alcohol_content=1.0, alcohol_role="ingredient"))
_add(["whiskey", "whisky"], "whiskey", _f(alcohol_content=1.0, alcohol_role="ingredient"))
_add(["brandy"], "brandy", _f(alcohol_content=1.0, alcohol_role="ingredient"))
_add(["sake"], "sake", _f(alcohol_content=1.0, alcohol_role="ingredient"))
_add(["liqueur"], "liqueur", _f(alcohol_content=1.0, alcohol_role="ingredient"))
_add(["vanilla extract"], "vanilla extract",
     _f(alcohol_content=1.0, alcohol_role="ingredient"))
# Culinary vinegars made from wine retain alcohol-relevant identity for Halal/Jain.
_add(["wine vinegar", "red wine vinegar", "white wine vinegar"], "wine vinegar",
     _f(alcohol_content=1.0, alcohol_role="ingredient"))
# Culinary plant vinegars without wine identity — Halal/Kosher-safe when anchored.
_add(["apple cider vinegar", "cider vinegar"], "apple cider vinegar",
     _f(animal_origin=False, plant_origin=True, alcohol_role="none"))
_add(["balsamic vinegar"], "balsamic vinegar",
     _f(animal_origin=False, plant_origin=True, alcohol_role="none"))
_add_compound(["natural flavoring", "natural flavouring"], "natural flavors")

# --- Jain / no-onion-no-garlic ---------------------------------------------
# Regional parsing rewrites "yam"/"suran" -> "elephant foot yam" and
# "arbi"/"taro" -> "taro root" (see data/regional_ingredient_names.json), so the
# resolver receives the canonical. Anchor those canonicals as root vegetables so
# Jain avoids them offline. Bare "yam" is deliberately left unanchored: it is
# region-ambiguous (IN elephant foot yam vs US dioscorea) and must reach Tier-3.
_add(["elephant foot yam"], "elephant foot yam",
     _f(root_vegetable=True, plant_origin=True))
_add(["taro root"], "taro root", _f(root_vegetable=True, plant_origin=True))
_add(["onion"], "onion", _f(onion_source=True, root_vegetable=True))
_add(["garlic"], "garlic", _f(garlic_source=True, root_vegetable=True))
_add(["shallot"], "shallot", _f(onion_source=True, root_vegetable=True))
_add(["leek"], "leek", _f(onion_source=True, root_vegetable=True))
_add(["chives"], "chives", _f(onion_source=True))

# --- compound / umbrella terms (never firm-SAFE) -----------------------------
_add_compound(["natural flavors", "natural flavor"], "natural flavors")
_add_compound(["artificial flavors", "artificial flavor"], "artificial flavors")
_add_compound(["flavor", "flavors", "flavour", "flavours"], "flavor")
_add_compound(["spices", "spice", "seasoning", "seasonings"], "spices")
_add_compound(["herbs and spices", "herbs & spices"], "spices")
_add_compound(
    ["preservatives", "preservative"],
    "preservatives",
)
_add_compound(
    ["colors", "colours", "color", "colour", "coloring", "colouring"],
    "colors",
)
# enzymes already registered above near water/salt


def lookup(normalized_key: str) -> Optional[TruthAnchorFact]:
    from core.normalization.normalizer import normalize_ingredient_key

    if not normalized_key:
        return None
    canon = normalize_ingredient_key(normalized_key)
    for key in (normalized_key, canon):
        hit = _ANCHORS.get(key) or _e_number_anchors().get(key)
        if hit is not None:
            return hit
    return None


def all_anchors() -> dict[str, TruthAnchorFact]:
    """Every Tier-1 alias -> fact, including generated E-number anchors.

    Hand-curated ``_ANCHORS`` wins on a key collision, same precedence as
    ``lookup()`` (e.g. hand-curated "soy lecithin" must not be shadowed by the
    more conservative generated E322 catalog entry of the same key).

    Used to boot-seed the ResolutionCache (design §9.5) with zero network
    calls; not used for lookup (``lookup`` remains the single source of truth
    for that, including its normalization fallback).
    """
    merged = dict(_e_number_anchors())
    merged.update(_ANCHORS)
    return merged
