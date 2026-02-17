"""
USDA FoodData Central API connector.
Free API key: https://fdc.nal.usda.gov/api-key-signup
Search: GET https://api.nal.usda.gov/fdc/v1/foods/search?api_key=KEY&query=...
"""
import json
import logging
import re
import urllib.parse
from typing import Optional

import requests

from core.ontology.ingredient_schema import Ingredient
from core.external_apis.http_retry import get_with_retries
from core.external_apis.base import EnrichmentResult, ConfidenceLevel

logger = logging.getLogger(__name__)

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
    "cocoa butter", "shea butter", "apple butter", "body butter",
    "almond milk", "oat milk", "soy milk", "rice milk", "coconut milk",
    "cashew milk", "hemp milk", "flax milk",
    "coconut cream", "coconut yogurt", "coconut cheese",
    "vegan cheese", "vegan butter", "vegan cream", "vegan egg",
    "tofu", "tempeh", "seitan", "jackfruit", "nutritional yeast",
    "plant-based", "plant based", "meatless", "dairy-free", "dairy free",
    "eggplant", "egg plant", "egusi",
    "butternut", "buttercup squash", "butterbean", "butter bean",
    "butterscotch",  # flavoring, not dairy
    "cream of tartar", "creamed corn", "cream soda", "ice cream bean",
]


def _is_plant_override(text: str) -> bool:
    """Return True if the text matches a known plant-based item despite containing animal keywords."""
    t = text.lower()
    return any(p in t for p in _PLANT_OVERRIDE_PATTERNS)


def _word_match(text: str, word: str) -> bool:
    """Word-boundary match: 'butter' matches 'butter' but not 'peanut butter'."""
    return bool(re.search(r'\b' + re.escape(word) + r'\b', text))


def _infer_flags_from_category(category: str) -> dict:
    """Primary classification using USDA FDC foodCategory — high reliability."""
    cat = (category or "").lower().strip()
    is_animal_meat = any(c in cat for c in _ANIMAL_MEAT_CATEGORIES)
    is_dairy_egg = any(c in cat for c in _DAIRY_EGG_CATEGORIES)
    is_plant = any(c in cat for c in _PLANT_CATEGORIES)
    return {
        "animal_origin": is_animal_meat or is_dairy_egg,
        "plant_origin": is_plant and not is_animal_meat and not is_dairy_egg,
        "dairy_source": is_dairy_egg,
        "egg_source": is_dairy_egg and "egg" in cat,
        "meat_or_fish": is_animal_meat,
    }


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

    # Dairy: only if category says so OR explicit dairy keywords (not overridden)
    if cat_flags["dairy_source"] and not override:
        dairy_source = True
    elif override:
        dairy_source = False
    else:
        dairy_keywords = ["milk", "cheese", "whey", "cream", "butter", "dairy",
                          "lactose", "casein", "ghee", "curd", "yogurt"]
        dairy_source = any(_word_match(t, w) for w in dairy_keywords) and not override

    # Egg: only from category or explicit 'egg' keyword (excluding 'eggplant')
    if cat_flags["egg_source"]:
        egg_source = True
    elif override:
        egg_source = False
    else:
        egg_source = _word_match(t, "egg") and "eggplant" not in t and "egg plant" not in t

    return {
        "animal_origin": animal_origin,
        "plant_origin": plant_origin,
        "dairy_source": dairy_source,
        "egg_source": egg_source,
        "gluten_source": any(_word_match(t, w) for w in ["wheat", "barley", "rye", "gluten"]),
        "soy_source": _word_match(t, "soy") or _word_match(t, "soybean") or _word_match(t, "tofu") or _word_match(t, "tempeh"),
        "nut_source": ("peanut" if _word_match(t, "peanut") else
                       "tree_nut" if _word_match(t, "almond") or _word_match(t, "walnut") or _word_match(t, "cashew") or _word_match(t, "pecan") or _word_match(t, "hazelnut") or _word_match(t, "macadamia") or _word_match(t, "pistachio") else
                       None),
        "sesame_source": _word_match(t, "sesame"),
        "alcohol_content": 1.0 if any(_word_match(t, w) for w in ["alcohol", "wine", "beer", "spirit", "rum", "vodka", "whiskey"]) else None,
        "onion_source": _word_match(t, "onion") and not override,
        "garlic_source": _word_match(t, "garlic") and not override,
        "root_vegetable": any(_word_match(t, w) for w in ["potato", "carrot", "beet", "radish", "turnip", "yam"]),
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
        elif "finfish" in cat_low or "shellfish" in cat_low:
            if any(_word_match(combined_low, w) for w in ["shrimp", "crab", "lobster", "prawn", "clam", "mussel", "oyster", "scallop"]):
                animal_species = "shellfish"
            else:
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

    best = foods[0]
    desc = (best.get("description") or "").strip().lower()
    q_lower = query.lower()
    # High: exact or very close match in description
    if q_lower in desc or desc in q_lower or q_lower.split()[0] in desc:
        confidence: ConfidenceLevel = "high"
    else:
        confidence = "medium"

    ing = _food_to_ingredient(best, query)
    summary = f"description={best.get('description', '')[:80]}"
    logger.info(
        "ENRICHMENT USDA_FDC success query=%s confidence=%s fdcId=%s",
        query, confidence, best.get("fdcId"),
    )
    return EnrichmentResult(ing, confidence, "usda_fdc", summary)
