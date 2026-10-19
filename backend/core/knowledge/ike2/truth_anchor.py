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


_COMPOUND_CANONICALS: set[str] = set()


def _add_compound(keys, canonical):
    """Unresolvable compound terms: never firm-SAFE (design §4B)."""
    _COMPOUND_CANONICALS.add(canonical)
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
_add(
    ["l-cysteine", "cysteine"],
    "l-cysteine",
    _f(
        # Source is contested (feather/hair or microbial fermentation). A firm
        # animal_origin would Avoid the name while E910 stays Depends.
        verdict_cap="WARN",
        uncertainty_flags=[
            "may_be_synthetic_or_from_plant_fermentation",
            "traditionally_from_poultry_feathers_or_hog_hair",
        ],
    ),
)
_add(["lanolin", "wool grease", "wool wax", "wool fat"], "lanolin", _f(animal_origin=True))
_add(["rennet", "animal rennet"], "rennet", _f(animal_origin=True, enzyme_animal_source=True))
_add(["pepsin"], "pepsin", _f(animal_origin=True, enzyme_animal_source=True))
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
_add(["seafood"], "seafood",
     _f(animal_origin=True, fish_source=True, shellfish_source=True))
_add(["snail", "snails", "escargot"], "snail",
     _f(animal_origin=True, animal_species="mollusk"))
_add(
    ["worcestershire sauce", "worcestershire", "worcester sauce"],
    "worcestershire sauce",
    _f(animal_origin=True, fish_source=True),
)

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
_add(["yolk", "yolks", "egg yolks"], "egg yolk", _f(animal_origin=True, egg_source=True))
_add(["albumin"], "albumin", _f(animal_origin=True, egg_source=True))
_add(["ovalbumin"], "ovalbumin", _f(animal_origin=True, egg_source=True))

# --- gluten / soy / sesame / mustard / celery / lupin / sulphite -------------
_add(["wheat"], "wheat", _f(gluten_source=True))
_add(["gluten"], "gluten", _f(gluten_source=True))
_add(["barley"], "barley", _f(gluten_source=True))
_add(["rye"], "rye", _f(gluten_source=True))
_add(["einkorn"], "einkorn", _f(gluten_source=True))
_add(["khorasan", "khorasan wheat"], "khorasan", _f(gluten_source=True))
_add(["spelt"], "spelt", _f(gluten_source=True))
# Idli rava is *usually* parboiled rice grits, but brands blend wheat — same
# honesty class as L-cysteine. WARN cap, no firm gluten bit either way.
_add(
    ["idli rava", "idli ravai", "rice rava", "rice sooji", "rice suji"],
    "idli rava",
    _f(
        plant_origin=True,
        verdict_cap="WARN",
        uncertainty_flags=["usually_parboiled_rice_check_blend"],
    ),
)
_add(["soy", "soybean", "edamame"], "soy", _f(soy_source=True))
_add(["tofu"], "tofu", _f(soy_source=True))
_add(["tempeh"], "tempeh", _f(soy_source=True, fungal=True))
_add(["soy sauce"], "soy sauce", _f(soy_source=True))
_add(["soy lecithin"], "soy lecithin", _f(soy_source=True))
_add(["sesame", "sesame seed"], "sesame", _f(sesame_source=True))
_add(["tahini", "tahini paste"], "tahini", _f(sesame_source=True))
_add(["mustard", "mustard seed", "mustard seeds", "rai"], "mustard", _f(mustard_source=True))
_add(["celery", "celeriac", "celery stalk"], "celery", _f(celery_source=True))
_add(
    ["lupin", "lupin flour", "lupins", "lupini", "lupini beans", "lupine beans"],
    "lupin",
    _f(lupin_source=True),
)
_add(
    ["crustaceans", "crustacean"],
    "crustaceans",
    _f(animal_origin=True, shellfish_source=True, animal_species="crustacean"),
)
_add(
    ["mollusks", "mollusk", "molluscs", "mollusc"],
    "mollusks",
    _f(animal_origin=True, shellfish_source=True, animal_species="mollusk"),
)
# Hand sulphite cluster must cover common EU/US spellings so generated e-number
# anchors cannot shadow them with sulphite_source=false (Item 7 / 2026-10-07).
_add(
    [
        "sulphite",
        "sulfite",
        "sulphites",
        "sulfites",
        "sulphur dioxide",
        "sulfur dioxide",
        "e220",
        "sodium sulphite",
        "sodium sulfite",
        "e221",
        "sodium hydrogen sulphite",
        "sodium hydrogen sulfite",
        "sodium bisulfite",
        "sodium bisulphite",
        "e222",
        "sodium metabisulfite",
        "sodium metabisulphite",
        "sodium pyrosulfite",
        "e223",
        "potassium metabisulfite",
        "potassium metabisulphite",
        "e224",
        "potassium sulphite",
        "potassium sulfite",
        "e225",
        "calcium sulphite",
        "calcium sulfite",
        "e226",
        "calcium hydrogen sulphite",
        "calcium hydrogen sulfite",
        "calcium bisulfite",
        "calcium bisulphite",
        "e227",
        "potassium hydrogen sulphite",
        "potassium hydrogen sulfite",
        "potassium bisulfite",
        "potassium bisulphite",
        "e228",
    ],
    "sulphite",
    _f(sulphite_source=True),
)
_add(["wheat flour", "enriched wheat flour", "bleached wheat flour"], "wheat",
     _f(gluten_source=True))
_add(["wheat gluten"], "gluten", _f(gluten_source=True))
_add(["malted barley flour"], "barley", _f(gluten_source=True))
_add(["flour", "flours", "all purpose flour"], "flour", _f(gluten_source=True))
# Bone-char refining is a process ambiguity on some cane sugars, not a labeled
# ingredient. We treat bare sugar as plant SAFE (not WARN): FAIL would over-block
# nearly every list; WARN would erase firm SAFE on the most common staple. Named
# cane/beet sugar stay plant SAFE the same way.
_add(["sugar"], "sugar", _f(animal_origin=False, plant_origin=True))
_add(["cane sugar"], "cane sugar", _f(animal_origin=False, plant_origin=True))
_add(["beet sugar"], "beet sugar", _f(animal_origin=False, plant_origin=True))
_add(["chicken"], "chicken", _f(animal_origin=True, animal_species="chicken"))
_add(["potato"], "potato", _f(root_vegetable=True, plant_origin=True))
_add(["water", "filtered water", "purified water", "drinking water"], "water", _f())
_add(
    [
        "salt",
        "sea salt",
        "iodised salt",
        "iodized salt",
        "lodised salt",  # OCR / typography variant of iodised
        "lodized salt",
        "edible common salt",
        "table salt",
        "rock salt",
    ],
    "salt",
    _f(),
)
# Culinary oils — named plant oils are L1 staples. Unspecified "vegetable oil"
# blends may include peanut/sesame/soy/tree-nut oils → WARN-cap only those
# allergy profiles (not vegan/gluten/dairy where oil is irrelevant).
_VEGETABLE_OIL_CAP_RESTRICTIONS = (
    "peanut_allergy",
    "sesame_allergy",
    "soy_allergy",
    "tree_nut_allergy",
)
_add(
    ["vegetable oil", "edible vegetable oil"],
    "vegetable oil",
    _f(
        animal_origin=False,
        plant_origin=True,
        # Scoped cap only — do not set uncertainty_flags (those also ceiling
        # vegan/dairy via _uncertainty_ceiling and would undo the scope).
        verdict_cap="WARN",
        verdict_cap_restrictions=list(_VEGETABLE_OIL_CAP_RESTRICTIONS),
    ),
)
for _oil in (
    "sunflower oil",
    "rapeseed oil",
    "canola oil",
    "olive oil",
    "corn oil",
    "coconut oil",
    "palm oil",
    "refined palm oil",
    "safflower oil",
):
    _add([_oil], _oil, _f(animal_origin=False, plant_origin=True))
_add(
    ["soybean oil", "soya oil", "soy oil"],
    "soybean oil",
    _f(animal_origin=False, plant_origin=True, soy_source=True),
)
_add(["almond oil"], "almond oil", _f(plant_origin=True, tree_nut_source=True))
_add(["walnut oil"], "walnut oil", _f(plant_origin=True, tree_nut_source=True))
_add(["sesame oil"], "sesame oil", _f(plant_origin=True, sesame_source=True))
_add(
    ["brown rice", "wholegrain brown rice", "cooked wholegrain brown rice"],
    "brown rice",
    _f(animal_origin=False, plant_origin=True),
)
_add(
    ["wheatberries", "wheat berries", "cooked wheatberries"],
    "wheat",
    _f(gluten_source=True),
)
_add(["glucose syrup", "corn syrup"], "glucose syrup", _f(plant_origin=True))
# Fortification vitamins — class-level staple clearance (not a hazard signal).
_add(
    ["vitamin b12", "cyanocobalamin", "cobalamin"],
    "vitamin b12",
    _f(synthetic=True, animal_origin=False, plant_origin=False),
)
_ORIGIN_AMBIGUOUS_DIET_CAPS = (
    "vegan",
    "jain",
    "halal",
    "hindu_vegetarian",
    "vegetarian",
    "kosher",
    "lacto_vegetarian",
    "ovo_vegetarian",
)
_add(
    ["vitamin b2", "riboflavin"],
    "vitamin b2",
    _f(
        synthetic=True,
        animal_origin=False,
        plant_origin=False,
        # Align with E101 catalog: whey-derived riboflavin is possible.
        verdict_cap="WARN",
        verdict_cap_restrictions=list(_ORIGIN_AMBIGUOUS_DIET_CAPS),
        uncertainty_flags=["may_be_animal_derived_if_from_whey"],
    ),
)
_add(
    [
        "thiamine",
        "thiamine mononitrate",
        "thiamin mononitrate",
        "vitamin b1",
        "thiamin",
    ],
    "thiamine",
    _f(synthetic=True, animal_origin=False, plant_origin=False),
)
_add(
    ["vitamin d2", "ergocalciferol"],
    "vitamin d2",
    _f(synthetic=True, animal_origin=False, plant_origin=False),
)
_add(
    ["vitamin a palmitate", "retinyl palmitate"],
    "vitamin a palmitate",
    _f(
        synthetic=True,
        animal_origin=False,
        plant_origin=False,
        # May be fish-oil derived — same WARN pattern as E101 / B2.
        verdict_cap="WARN",
        verdict_cap_restrictions=list(_ORIGIN_AMBIGUOUS_DIET_CAPS),
        uncertainty_flags=["may_be_animal_derived_if_from_fish_oil"],
    ),
)
_add(
    ["vitamin b6", "pyridoxine", "pyridoxine hydrochloride"],
    "vitamin b6",
    _f(synthetic=True, animal_origin=False, plant_origin=False),
)
_add(
    ["vitamin d", "vitamin d3", "cholecalciferol"],
    "vitamin d",
    _f(
        synthetic=True,
        animal_origin=False,
        plant_origin=False,
        # Commercial D3 is usually lanolin-derived.
        verdict_cap="WARN",
        verdict_cap_restrictions=list(_ORIGIN_AMBIGUOUS_DIET_CAPS),
        uncertainty_flags=["may_be_animal_derived_if_from_lanolin"],
    ),
)
_add(["invert sugar syrup", "invert sugar"], "invert sugar", _f(plant_origin=True))
# Yeast / yeast-culture: Jain fungal FAIL. Empty flags here previously shadowed
# richer L2 ontology rows (baker's yeast fungal=True) and left plain "yeast" SAFE.
_add(
    [
        "yeast",
        "baker's yeast",
        "bakers yeast",
        "brewer's yeast",
        "brewers yeast",
        "nutritional yeast",
        "active dry yeast",
        "instant yeast",
        "dry yeast",
        "torula yeast",
    ],
    "yeast",
    _f(fungal=True, plant_origin=True, animal_origin=False),
)
_add(
    ["yeast extract", "autolyzed yeast extract", "yeast extract spread"],
    "yeast extract",
    _f(fungal=True, plant_origin=True, animal_origin=False),
)
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
# Prepared / multi-ingredient dishes — composition unknown; never invent dairy/egg/meat.
_add_compound(["affogato"], "affogato")
_add_compound(["tempered spices", "tadka", "tarka"], "tempered spices")
_add_compound(["tiramisu"], "tiramisu")
_add_compound(["latte", "cafe latte", "caffè latte"], "latte")
_add_compound(["cappuccino"], "cappuccino")
_add_compound(["macchiato", "cafe macchiato"], "macchiato")
_add_compound(["mocha", "cafe mocha"], "mocha")
_add_compound(["frappe", "frappé"], "frappe")
_add_compound(["milkshake"], "milkshake")
_add_compound(["hot chocolate", "hot cocoa"], "hot chocolate")
_add_compound(["sundae"], "sundae")
_add_compound(["parfait"], "parfait")
_add_compound(["souffle", "soufflé", "spinach souffle"], "souffle")
_add_compound(["omelette", "omelet"], "omelette")
_add_compound(["quiche"], "quiche")
_add_compound(["ice cream sandwich"], "ice cream sandwich")
_add_compound(["ice cream"], "ice cream")
_add_compound(["gelato"], "gelato")
_add_compound(["custard"], "custard")
_add_compound(["mousse"], "mousse")
_add_compound(["cheesecake"], "cheesecake")
_add_compound(["veggie burger", "veggie burgers"], "veggie burger")
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


def is_compound_umbrella(name: str) -> bool:
    """True when name is a Tier-1 compound/umbrella registered via _add_compound.

    Uses ``_COMPOUND_CANONICALS`` + ``lookup`` — the same set that caps
    natural flavors / spices / dish shells to verdict_cap=WARN.
    """
    from core.normalization.normalizer import normalize_ingredient_key

    if not name or not str(name).strip():
        return False
    key = normalize_ingredient_key(str(name).strip())
    if key in _COMPOUND_CANONICALS:
        return True
    fact = lookup(key) or lookup(str(name).strip())
    if fact is None:
        return False
    return fact.canonical_name in _COMPOUND_CANONICALS


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
