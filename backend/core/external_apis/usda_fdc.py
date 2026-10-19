"""
USDA FoodData Central API connector.
Free API key: https://fdc.nal.usda.gov/api-key-signup
Search: GET https://api.nal.usda.gov/fdc/v1/foods/search?api_key=KEY&query=...
"""
import json
import logging
import re
from functools import lru_cache
from pathlib import Path

import requests

from core.ontology.ingredient_schema import Ingredient
from core.external_apis.enrichment_relevance import (
    is_enrichment_relevant,
    score_enrichment_candidate,
)
from core.external_apis.http_retry import get_with_retries
from core.external_apis.base import EnrichmentResult, ConfidenceLevel
from core.normalization.normalizer import normalize_ingredient_key

logger = logging.getLogger(__name__)

_REVIEWED_CLEARS_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "usda_reviewed_asserted_clears.json"
)

USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"


def _normalize_id(name: str) -> str:
    """Slug for ingredient id (alphanumeric + underscore)."""
    s = re.sub(r"[^a-z0-9]+", "_", name.lower().strip())
    return s.strip("_") or "unknown"


"""
USDA FDC food categories → origin flags mapping.
Category-based classification is far more reliable than keyword substring matching.
"""
_ANIMAL_MEAT_CATEGORIES = {
    "beef products", "pork products", "poultry products",
    "lamb, veal, and game products", "sausages and luncheon meats",
    "finfish and shellfish products",
}
_DAIRY_EGG_CATEGORIES = {"dairy and egg products"}
_PLANT_CATEGORIES = {
    "vegetables and vegetable products", "fruits and fruit juices",
    "legumes and legume products", "nut and seed products",
    "cereal grains and pasta", "spices and herbs",
    "baby foods", "baked products",
}

# Plant-based items whose names contain misleading animal keywords
_PLANT_OVERRIDE_PATTERNS = [
    "peanut butter", "almond butter", "cashew butter", "sunflower butter",
    "sunflower seed butter",
    "cocoa butter", "shea butter", "apple butter", "body butter",
    "almond milk", "oat milk", "soy milk", "rice milk", "coconut milk",
    "cashew milk", "hemp milk", "flax milk",
    "coconut cream", "coconut yogurt", "coconut cheese",
    "soy yogurt", "soya yogurt", "tofu yogurt",
    "vegan cheese", "vegan butter", "vegan cream", "vegan egg",
    "tofu", "tempeh", "seitan", "jackfruit", "nutritional yeast",
    "plant-based", "plant based", "meatless", "dairy-free", "dairy free",
    "eggplant", "egg plant", "egusi",
    "butternut", "buttercup squash", "butterbean", "butter bean",
    "butterscotch",  # flavoring, not dairy
    "cream of tartar", "creamed corn", "cream soda", "ice cream bean",
    "custard-apple", "custard apple",  # Annona fruit, not dairy custard
]


def _is_plant_override(text: str) -> bool:
    """Return True if the text matches a known plant-based item despite containing animal keywords."""
    t = text.lower()
    return any(p in t for p in _PLANT_OVERRIDE_PATTERNS)


def _word_match(text: str, word: str) -> bool:
    """Word-boundary match with plural tolerance: 'onion' matches 'onion' and 'onions'."""
    return bool(re.search(r'\b' + re.escape(word) + r'(?:e?s)?\b', text))


def _infer_flags_from_category(category: str) -> dict:
    """Primary classification using USDA FDC foodCategory — high reliability.

    ``Dairy and Egg Products`` is a joint bucket: do **not** set dairy_source /
    egg_source from the category alone (\"egg\" is a substring of the category
    name, which previously flagged every dairy row as egg and every egg as dairy).
    """
    cat = (category or "").lower().strip()
    is_animal_meat = any(c in cat for c in _ANIMAL_MEAT_CATEGORIES)
    is_dairy_egg = any(c in cat for c in _DAIRY_EGG_CATEGORIES)
    is_plant = any(c in cat for c in _PLANT_CATEGORIES)
    is_finfish_shellfish = "finfish" in cat or "shellfish" in cat
    return {
        "animal_origin": is_animal_meat or is_dairy_egg,
        "plant_origin": is_plant and not is_animal_meat and not is_dairy_egg,
        "dairy_egg_category": is_dairy_egg,
        "dairy_source": False,
        "egg_source": False,
        "meat_or_fish": is_animal_meat,
        "finfish_shellfish_category": is_finfish_shellfish,
    }


_SHELLFISH_NAME = re.compile(
    r"\b(prawns?|shrimps?|crabs?|lobsters?|crawfish|crayfish|crawdads?|"
    r"langoustines?|krill|yabb(?:y|ies)|mussels?|oysters?|"
    r"clams?|scallops?|squids?|octopuses?|octopus|cuttlefish|shellfish|"
    r"molluscs?|mollusks?|crustaceans?)\b",
    re.I,
)
_FISH_NAME = re.compile(
    r"\b(fish|finfish|salmon|tuna|cod|haddock|halibut|mackerel|sardine|anchovy|"
    r"trout|bass|perch|pike|carp|eel|herring|swordfish|tilapia|catfish|grouper|"
    r"pollock|whiting|sole|flounder|sturgeon|snapper|roe|caviar|surimi)\b",
    re.I,
)

# Tree nut: name lexicon only (never "Nut and Seed Products" alone).
# Coconut / nutmeg / water chestnut / butternut are explicit non-triggers.
# Seeds (sunflower, pumpkin, sesame, flax, chia, hemp, poppy) are excluded.
_TREE_NUT_NAME = re.compile(
    r"\b("
    r"almonds?|walnuts?|pecans?|cashews?|pistachios?|hazelnuts?|filberts?|"
    r"macadamias?|brazil\s*nuts?|pine\s*nuts?|pinyons?|pinenuts?|chestnuts?|"
    r"pralines?|marzipan|nougat|gianduja|frangipane|amaretto|pesto"
    r")\b",
    re.I,
)
_TREE_NUT_NON_TRIGGER = re.compile(
    r"\b(coconut|nutmeg|water\s*chestnuts?|butternut)\b",
    re.I,
)


def _tree_nut_from_name(text: str) -> tuple[bool, str | None]:
    """Return (tree_nut_source, nut_source_token). Category is never consulted."""
    t = (text or "").lower()
    if _TREE_NUT_NON_TRIGGER.search(t):
        return False, None
    if not _TREE_NUT_NAME.search(t):
        return False, None
    return True, "tree_nut"

# Genuine dairy+egg products — never clear either flag via disambiguation.
# ``custard`` must not match the fruit ``custard-apple`` / ``custard apple``.
_DAIRY_EGG_BOTH = re.compile(
    r"\b(eggnog|egg\s*nog|(?<![\w-])custard(?!\s*-?\s*apples?)|quiche|"
    r"souffl[eé]|egg\s*wash|"
    r"french\s*toast|bread\s*pudding|creme\s*brulee|crème\s*brûlée)\b",
    re.I,
)
_CUSTARD_APPLE = re.compile(r"\bcustard[\s-]*apples?\b", re.I)

# Positive-family lexicons for asserted-clear guard (name implies the flag).
_POSITIVE_LEXICON = {
    "shellfish_source": _SHELLFISH_NAME,
    "fish_source": _FISH_NAME,
    "egg_source": re.compile(
        r"\b(egg|eggs|eggnog|mayonnaise|meringue|anda)\b", re.I
    ),
    "dairy_source": re.compile(
        r"\b(milk|cheese|whey|cream|butter|dairy|lactose|casein|ghee|"
        r"yogurt|yoghurt|buttermilk|paneer|dahi|curd|khoa|mawa|lassi|"
        r"chaas|malai)\b",
        re.I,
    ),
}


@lru_cache(maxsize=1)
def _load_reviewed_clears() -> tuple[frozenset[str], frozenset[tuple[str, str]]]:
    if not _REVIEWED_CLEARS_PATH.exists():
        return frozenset(), frozenset()
    data = json.loads(_REVIEWED_CLEARS_PATH.read_text(encoding="utf-8"))
    friends = frozenset(data.get("shellfish_false_friends") or [])
    clears = frozenset(
        (str(row["name"]), str(row["flag"]))
        for row in (data.get("asserted_clears") or [])
        if row.get("name") and row.get("flag")
    )
    return friends, clears


def _reviewed_shellfish_false_friends() -> frozenset[str]:
    return _load_reviewed_clears()[0]


def _reviewed_asserted_clears() -> frozenset[tuple[str, str]]:
    return _load_reviewed_clears()[1]


def __getattr__(name: str):
    """Lazy public sets so tests can import without re-reading JSON each edit."""
    if name == "REVIEWED_SHELLFISH_FALSE_FRIENDS":
        return _reviewed_shellfish_false_friends()
    if name == "REVIEWED_ASSERTED_CLEARS":
        return _reviewed_asserted_clears()
    raise AttributeError(name)


def is_shellfish_false_friend(name: str) -> bool:
    """True when normalized name is on the reviewed shellfish false-friend list."""
    return normalize_ingredient_key(name) in _reviewed_shellfish_false_friends()


def asserted_clear_allowed(name: str, flag: str) -> bool:
    """Asserted false may clear a sticky true only for reviewed (name, flag).

    Belt-and-suspenders: a positive-lexicon hit that is not a listed exception
    is always refused (blocks oyster sauce / eggnog class mistakes).
    """
    norm = normalize_ingredient_key(name)
    listed = (norm, flag) in _reviewed_asserted_clears()
    lex = _POSITIVE_LEXICON.get(flag)
    lexicon_hit = bool(lex and lex.search(norm))
    if lexicon_hit and not listed:
        return False
    return listed


class _ShellfishFalseFriendProxy:
    """Historic ``_SHELLFISH_FALSE_FRIEND.search(t)`` API → reviewed list."""

    def search(self, t: str):
        return is_shellfish_false_friend(t or "")


_SHELLFISH_FALSE_FRIEND = _ShellfishFalseFriendProxy()


def _fish_shellfish_from_name_and_category(text: str, category: str = "") -> dict:
    """Split USDA 'Finfish and Shellfish Products' (and name tokens) into kind flags.

    True-only intent: callers should omit false keys when emitting Layer-1 dumps.
    Generic 'seafood' gets both kinds (umbrella label).
    """
    t = (text or "").lower()
    cat = (category or "").lower()
    in_fs_cat = "finfish" in cat or "shellfish" in cat
    if re.search(r"\bseafood\b", t):
        return {"fish_source": True, "shellfish_source": True}
    if is_shellfish_false_friend(t):
        return {"fish_source": False, "shellfish_source": False}
    if _SHELLFISH_NAME.search(t):
        return {"fish_source": False, "shellfish_source": True}
    if _FISH_NAME.search(t) or in_fs_cat:
        return {"fish_source": True, "shellfish_source": False}
    return {"fish_source": False, "shellfish_source": False}


def _infer_flags_from_text(text: str, category: str = "") -> dict:
    """
    Infer Ingredient flags from description/category text.
    Uses category-based mapping as primary signal, text keywords as secondary.
    Plant-based overrides prevent false positives from compound names
    (e.g. 'peanut butter', 'almond milk').
    """
    t = (text or "").lower()
    cat_flags = _infer_flags_from_category(category)
    override = _is_plant_override(t)

    # Animal/plant origin: prefer category; fall back to text keywords only if category is ambiguous
    if cat_flags["animal_origin"] and not override:
        animal_origin = True
        plant_origin = cat_flags["plant_origin"]
    elif cat_flags["plant_origin"] or override:
        animal_origin = False
        plant_origin = True
    else:
        # Category ambiguous (e.g. "Snacks", "Meals"): use careful text inference
        animal_keywords = ["meat", "beef", "pork", "chicken", "fish", "gelatin",
                           "lard", "tallow", "animal", "whey", "casein", "rennet"]
        animal_origin = not override and any(_word_match(t, w) for w in animal_keywords)
        plant_origin = not animal_origin

    # Name lexicon only — never set dairy/egg from "Dairy and Egg Products"
    # alone (category bleed put egg on kefir / whipped topping).
    dairy_keywords = [
        "milk", "cheese", "whey", "cream", "butter", "dairy",
        "lactose", "casein", "ghee", "curd", "yogurt", "yoghurt",
        "buttermilk", "paneer", "kefir", "ice cream", "icecream",
        "dahi", "khoa", "mawa", "lassi", "chaas", "malai",
    ]
    looks_dairy = (not override) and any(_word_match(t, w) for w in dairy_keywords)
    looks_egg = (
        not override
        and _word_match(t, "egg")
        and "eggplant" not in t
        and "egg plant" not in t
        and "without egg" not in t
        and "no egg" not in t
        and "egg free" not in t
        and "egg-free" not in t
    )
    if override or _CUSTARD_APPLE.search(t):
        dairy_source, egg_source = False, False
    elif _DAIRY_EGG_BOTH.search(t):
        dairy_source, egg_source = True, True
    else:
        dairy_source = looks_dairy
        egg_source = looks_egg

    kind = _fish_shellfish_from_name_and_category(t, category)
    if kind["fish_source"] or kind["shellfish_source"]:
        animal_origin = True
        if not override:
            plant_origin = False
    # CHECK dairy_implies_animal / egg_implies_animal: a true dairy/egg bit
    # without animal_origin is quarantined at inject.
    if (dairy_source or egg_source) and not override:
        animal_origin = True

    return {
        "animal_origin": animal_origin,
        "plant_origin": plant_origin,
        "dairy_source": dairy_source,
        "egg_source": egg_source,
        "fish_source": kind["fish_source"],
        "shellfish_source": kind["shellfish_source"],
        "gluten_source": (
            (
                any(
                    _word_match(t, w)
                    for w in (
                        "wheat", "barley", "rye", "gluten", "chapatti", "chapati",
                        "atta", "maida", "semolina", "sooji", "suji", "rava",
                        "dalia", "roti", "paratha", "naan", "puri",
                    )
                )
                or (_word_match(t, "bread") and "breadfruit" not in t)
            )
            # Idli rava / rice rava are rice grits, not wheat semolina.
            and "idli rava" not in t
            and "rice rava" not in t
            and "rice sooji" not in t
            and "rice suji" not in t
        ),
        "soy_source": _word_match(t, "soy") or _word_match(t, "soybean") or _word_match(t, "tofu") or _word_match(t, "tempeh"),
        "nut_source": (
            "peanut" if _word_match(t, "peanut")
            else (_tree_nut_from_name(t)[1])
        ),
        "tree_nut_source": (
            False if _word_match(t, "peanut") else _tree_nut_from_name(t)[0]
        ),
        "sesame_source": _word_match(t, "sesame") or _word_match(t, "til"),
        "alcohol_content": 1.0 if any(_word_match(t, w) for w in ["alcohol", "wine", "beer", "spirit", "rum", "vodka", "whiskey"]) else None,
        "onion_source": _word_match(t, "onion") and not override,
        "garlic_source": _word_match(t, "garlic") and not override,
        "root_vegetable": any(_word_match(t, w) for w in ["potato", "carrot", "beet", "radish", "turnip", "yam", "onion", "garlic", "shallot", "leek"]),
    }


def _food_to_ingredient(food: dict, query: str) -> Ingredient:
    """Map one USDA FDC food item to our Ingredient schema."""
    desc = (food.get("description") or "").strip()
    category = (food.get("foodCategory") or "").strip()
    if isinstance(food.get("foodCategory"), dict):
        category = (food.get("foodCategory").get("description") or "").strip()
    combined = f"{desc} {category}"
    flags = _infer_flags_from_text(combined, category=category)
    canonical = desc or query or "unknown"
    ing_id = _normalize_id(canonical)[:64]

    # Infer animal_species from category/description for proper restriction matching
    animal_species = None
    if flags.get("animal_origin", False):
        cat_low = (category or "").lower()
        combined_low = combined.lower()
        if "pork" in cat_low or _word_match(combined_low, "pork") or _word_match(combined_low, "bacon") or _word_match(combined_low, "ham"):
            animal_species = "pig"
        elif "beef" in cat_low or _word_match(combined_low, "beef") or _word_match(combined_low, "veal"):
            animal_species = "cow"
        elif "poultry" in cat_low or _word_match(combined_low, "chicken") or _word_match(combined_low, "turkey") or _word_match(combined_low, "duck"):
            animal_species = "chicken"
        elif "lamb" in cat_low or _word_match(combined_low, "lamb") or _word_match(combined_low, "mutton") or _word_match(combined_low, "goat"):
            animal_species = "lamb"
        elif flags.get("shellfish_source"):
            animal_species = "shellfish"
        elif flags.get("fish_source") or "finfish" in cat_low or "shellfish" in cat_low:
            animal_species = "fish"
        elif _word_match(combined_low, "fish") or _word_match(combined_low, "salmon") or _word_match(combined_low, "tuna") or _word_match(combined_low, "cod"):
            animal_species = "fish"

    return Ingredient(
        id=f"usda_{ing_id}",
        canonical_name=canonical,
        aliases=[query] if query and query != canonical else [],
        derived_from=[],
        contains=[],
        may_contain=[],
        animal_origin=flags.get("animal_origin", False),
        plant_origin=flags.get("plant_origin", False),
        # FSSAI-inferred synthetic on additives is unreliable and read by no rule;
        # USDA path never sets it. Keep False as unset default, not a verified negative.
        synthetic=False,
        fungal=False,
        insect_derived=False,
        animal_species=animal_species,
        egg_source=flags.get("egg_source", False),
        dairy_source=flags.get("dairy_source", False),
        gluten_source=flags.get("gluten_source", False),
        nut_source=flags.get("nut_source"),
        soy_source=flags.get("soy_source", False),
        sesame_source=flags.get("sesame_source", False),
        alcohol_content=flags.get("alcohol_content"),
        root_vegetable=flags.get("root_vegetable", False),
        onion_source=flags.get("onion_source", False),
        garlic_source=flags.get("garlic_source", False),
        fermented=False,
        uncertainty_flags=["usda_fdc_inferred"] if not desc else [],
        regions=[],
    )


def fetch_usda_fdc(
    ingredient_query: str,
    api_key: str,
    timeout: int = 10,
) -> EnrichmentResult:
    """
    Search USDA FDC for an ingredient. Returns EnrichmentResult with ingredient and confidence.
    High confidence when we get a clear description match; medium when partial; low when API fail or empty.
    """
    if not api_key or not ingredient_query or not ingredient_query.strip():
        logger.debug("USDA_FDC: skip empty query or no api_key")
        return EnrichmentResult(None, "low", "usda_fdc", "no_key_or_query")

    query = ingredient_query.strip()[:200]
    params = {"api_key": api_key, "query": query, "pageSize": 5}
    resp, err = get_with_retries(USDA_SEARCH_URL, params=params, timeout=timeout, max_retries=3)
    if err is not None:
        logger.warning("USDA_FDC API fetch failed after retries query=%s error=%s", query, err)
        return EnrichmentResult(None, "low", "usda_fdc", f"error:{err[:80]}")
    try:
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.warning("USDA_FDC API response error query=%s error=%s", query, e)
        return EnrichmentResult(None, "low", "usda_fdc", f"error:{type(e).__name__}")

    foods = data.get("foods") or []
    if not foods:
        logger.info("USDA_FDC no results query=%s", query)
        return EnrichmentResult(None, "low", "usda_fdc", "no_results")

    scored = []
    for food in foods:
        desc = (food.get("description") or "").strip()
        if not desc:
            continue
        score = score_enrichment_candidate(query, desc)
        if score < 0:
            logger.info(
                "USDA_FDC skip species mismatch query=%s description=%s",
                query, desc[:80],
            )
            continue
        scored.append((score, food))

    if not scored:
        logger.info("USDA_FDC no relevant results (species filter) query=%s", query)
        return EnrichmentResult(None, "low", "usda_fdc", "species_mismatch")

    scored.sort(key=lambda pair: pair[0], reverse=True)
    best_score, best = scored[0]
    desc = (best.get("description") or "").strip().lower()
    q_lower = query.lower()
    if q_lower in desc or desc in q_lower or best_score >= 30:
        confidence: ConfidenceLevel = "high"
    elif best_score >= 10:
        confidence = "medium"
    else:
        confidence = "low"
        if not is_enrichment_relevant(query, best.get("description") or ""):
            return EnrichmentResult(None, "low", "usda_fdc", "species_mismatch")

    ing = _food_to_ingredient(best, query)
    summary = f"description={best.get('description', '')[:80]}"
    logger.info(
        "ENRICHMENT USDA_FDC success query=%s confidence=%s fdcId=%s score=%s",
        query, confidence, best.get("fdcId"), best_score,
    )
    return EnrichmentResult(ing, confidence, "usda_fdc", summary)
