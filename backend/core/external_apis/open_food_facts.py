"""
Open Food Facts API connector (no key required).
Search: https://world.openfoodfacts.org/cgi/search.pl?search_terms=...&json=1
"""
import logging
import re
from typing import Optional

import requests

from core.ontology.ingredient_schema import Ingredient
from core.external_apis.http_retry import get_with_retries
from core.external_apis.base import EnrichmentResult, ConfidenceLevel

logger = logging.getLogger(__name__)

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"


def _normalize_id(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower().strip())
    return s.strip("_") or "unknown"


"""
Plant-based items whose names contain misleading animal keywords.
Prevents false positives like 'peanut butter' → dairy or 'almond milk' → dairy.
"""
_PLANT_OVERRIDE_PATTERNS = [
    "peanut butter", "almond butter", "cashew butter", "sunflower butter",
    "cocoa butter", "shea butter", "apple butter",
    "almond milk", "oat milk", "soy milk", "rice milk", "coconut milk",
    "cashew milk", "hemp milk", "flax milk",
    "coconut cream", "coconut yogurt", "coconut cheese",
    "vegan cheese", "vegan butter", "vegan cream", "vegan egg",
    "tofu", "tempeh", "seitan", "jackfruit", "nutritional yeast",
    "plant-based", "plant based", "meatless", "dairy-free", "dairy free",
    "eggplant", "egg plant", "egusi",
    "butternut", "buttercup squash", "butterbean", "butter bean",
    "butterscotch", "cream of tartar", "creamed corn", "cream soda",
]


def _is_plant_override(text: str) -> bool:
    t = text.lower()
    return any(p in t for p in _PLANT_OVERRIDE_PATTERNS)


def _word_match(text: str, word: str) -> bool:
    """Word-boundary match with plural tolerance: 'onion' matches 'onion' and 'onions'."""
    return bool(re.search(r'\b' + re.escape(word) + r'(?:e?s)?\b', text))


def _infer_flags_from_product(product: dict, combined_text: str) -> dict:
    """
    Infer Ingredient flags from OFF product data.
    Uses structured tags (labels_tags, allergens_tags, categories_tags) as primary signal.
    Falls back to text keyword inference with plant-override protection.
    """
    t = (combined_text or "").lower()
    override = _is_plant_override(t)

    # Use OFF structured tags for reliable classification
    labels = [tag.lower() for tag in (product.get("labels_tags") or [])]
    allergen_tags = [tag.lower() for tag in (product.get("allergens_tags") or [])]
    cat_tags = [tag.lower() for tag in (product.get("categories_tags") or [])]

    is_vegan = any("vegan" in l for l in labels)
    is_vegetarian = any("vegetarian" in l for l in labels)
    has_milk_allergen = any("milk" in a for a in allergen_tags)
    has_egg_allergen = any("egg" in a for a in allergen_tags)
    has_gluten_allergen = any("gluten" in a for a in allergen_tags)
    has_soy_allergen = any("soy" in a or "soja" in a for a in allergen_tags)

    # Animal origin: tags override text
    if is_vegan or override:
        animal_origin = False
        plant_origin = True
        dairy_source = False
        egg_source = False
    elif is_vegetarian:
        # Vegetarian = no meat, but may have dairy/eggs
        animal_keywords = ["meat", "beef", "pork", "chicken", "fish", "gelatin", "lard", "tallow"]
        animal_origin = any(_word_match(t, w) for w in animal_keywords)
        plant_origin = not animal_origin
        dairy_source = has_milk_allergen or (any(_word_match(t, w) for w in ["milk", "cheese", "whey", "cream", "butter", "dairy", "casein", "ghee"]) and not override)
        egg_source = has_egg_allergen or (_word_match(t, "egg") and "eggplant" not in t)
    else:
        animal_keywords = ["meat", "beef", "pork", "chicken", "fish", "gelatin", "lard",
                           "tallow", "animal", "whey", "casein", "rennet"]
        animal_origin = not override and any(_word_match(t, w) for w in animal_keywords)
        plant_origin = not animal_origin
        dairy_keywords = ["milk", "cheese", "whey", "cream", "butter", "dairy",
                          "lactose", "casein", "ghee", "curd", "yogurt"]
        dairy_source = (has_milk_allergen or
                        (any(_word_match(t, w) for w in dairy_keywords) and not override))
        egg_source = (has_egg_allergen or
                      (_word_match(t, "egg") and "eggplant" not in t and not override))

    return {
        "animal_origin": animal_origin,
        "plant_origin": plant_origin,
        "dairy_source": dairy_source,
        "egg_source": egg_source,
        "gluten_source": has_gluten_allergen or any(_word_match(t, w) for w in ["wheat", "barley", "rye", "gluten"]),
        "soy_source": has_soy_allergen or _word_match(t, "soy") or _word_match(t, "soybean") or _word_match(t, "tofu"),
        "nut_source": ("peanut" if _word_match(t, "peanut") or any("peanut" in a for a in allergen_tags) else
                       "tree_nut" if any(_word_match(t, w) for w in ["almond", "walnut", "cashew", "pecan", "hazelnut", "macadamia", "pistachio"]) or any("nut" in a for a in allergen_tags) else
                       None),
        "sesame_source": _word_match(t, "sesame") or any("sesame" in a for a in allergen_tags),
        "alcohol_content": 1.0 if any(_word_match(t, w) for w in ["alcohol", "wine", "beer", "spirit"]) else None,
        "onion_source": _word_match(t, "onion") and not override,
        "garlic_source": _word_match(t, "garlic") and not override,
        "root_vegetable": any(_word_match(t, w) for w in ["potato", "carrot", "beet", "radish", "turnip", "yam", "onion", "garlic", "shallot", "leek"]),
    }


def _product_to_ingredient(product: dict, query: str) -> Ingredient:
    """Map one OFF product to Ingredient. Uses product_name, ingredients_text, and structured tags."""
    name = (product.get("product_name") or product.get("product_name_en") or query or "unknown").strip()
    ingredients_text = (product.get("ingredients_text") or product.get("ingredients_text_en") or "").strip()
    allergens = (product.get("allergens") or product.get("allergens_from_ingredients") or "").strip().lower()
    combined = f"{name} {ingredients_text} {allergens}"
    flags = _infer_flags_from_product(product, combined)
    ing_id = _normalize_id(name)[:64]
    return Ingredient(
        id=f"off_{ing_id}",
        canonical_name=name,
        aliases=[query] if query and query != name else [],
        derived_from=[],
        contains=[],
        may_contain=[],
        animal_origin=flags.get("animal_origin", False),
        plant_origin=flags.get("plant_origin", False),
        synthetic=False,
        fungal=False,
        insect_derived=False,
        animal_species=None,
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
        uncertainty_flags=["open_food_facts_inferred"],
        regions=[],
    )


def fetch_open_food_facts(
    ingredient_query: str,
    timeout: int = 10,
) -> EnrichmentResult:
    """
    Search Open Food Facts. Returns EnrichmentResult.
    High confidence when product name closely matches query; medium otherwise.
    """
    if not ingredient_query or not ingredient_query.strip():
        return EnrichmentResult(None, "low", "open_food_facts", "empty_query")

    query = ingredient_query.strip()[:200]
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 5,
    }
    resp, err = get_with_retries(OFF_SEARCH_URL, params=params, timeout=timeout, max_retries=3)
    if err is not None:
        logger.warning("OPEN_FOOD_FACTS API fetch failed after retries query=%s error=%s", query, err)
        return EnrichmentResult(None, "low", "open_food_facts", f"error:{err[:80]}")
    try:
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.warning("OPEN_FOOD_FACTS API response error query=%s error=%s", query, e)
        return EnrichmentResult(None, "low", "open_food_facts", f"error:{type(e).__name__}")

    products = data.get("products") or []
    if not products:
        logger.info("OPEN_FOOD_FACTS no results query=%s", query)
        return EnrichmentResult(None, "low", "open_food_facts", "no_results")

    best = products[0]
    name = (best.get("product_name") or best.get("product_name_en") or "").strip().lower()
    q_lower = query.lower()
    if name and (q_lower in name or name in q_lower or q_lower.split()[0] in name):
        confidence: ConfidenceLevel = "high"
    else:
        confidence = "medium"

    ing = _product_to_ingredient(best, query)
    summary = f"product_name={(best.get('product_name') or '')[:80]}"
    logger.info(
        "ENRICHMENT OPEN_FOOD_FACTS success query=%s confidence=%s",
        query, confidence,
    )
    return EnrichmentResult(ing, confidence, "open_food_facts", summary)
