"""
Bridge: map profile/legacy diet names to restriction_ids; build legacy-shaped scorecard from verdict.
Used by scan and chat when USE_NEW_ENGINE is True.
"""
import logging
from typing import Dict, List, Any, Optional, Set, Tuple, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from core.models.user_profile import UserProfile

from core.evaluation.compliance_engine import ComplianceEngine
from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.parsing.ingredient_parser import preprocess_ingredients, get_trace_keys
from core.normalization.parser import flatten_ingredients

logger = logging.getLogger(__name__)

# Legacy scan scorecard diet labels -> restriction_ids
SCAN_DIET_LABELS = ["Vegan", "Jain", "Halal", "Hindu Veg"]
DIET_LABEL_TO_RESTRICTION_ID = {
    "Vegan": "vegan",
    "Jain": "jain",
    "Halal": "halal",
    "Hindu Veg": "hindu_vegetarian",
}
# Claimed diet types (verification, onboarding) -> restriction_id
CLAIMED_DIET_TO_RESTRICTION_ID = {
    "Vegan": "vegan",
    "Vegetarian": "vegetarian",
    "Jain": "jain",
    "Halal": "halal",
    "Kosher": "kosher",
    "Hindu Veg": "hindu_vegetarian",
    "Gluten-Free": "gluten_free",
    "Dairy-Free": "dairy_free",
    "Egg-Free": "egg_free",
}

# Dietary preference (single primary) -> restriction_id
DIETARY_PREFERENCE_TO_RESTRICTION_ID = {
    "no rules": "vegetarian",  # default evaluate against common diets
    "jain": "jain",
    "vegan": "vegan",
    "vegetarian": "vegetarian",
    "hindu veg": "hindu_vegetarian",
    "hindu vegetarian": "hindu_vegetarian",
    "hindu non vegetarian": "hindu_non_vegetarian",
    "hindu non veg": "hindu_non_vegetarian",
    "halal": "halal",
    "kosher": "kosher",
    "lacto vegetarian": "lacto_vegetarian",
    "ovo vegetarian": "ovo_vegetarian",
    "pescatarian": "pescatarian",
    "gluten-free": "gluten_free",
    "dairy-free": "dairy_free",
    "egg-free": "egg_free",
}

# Profile diet (from frontend) -> restriction_id
PROFILE_DIET_TO_RESTRICTION_ID = {
    "vegan": "vegan",
    "vegetarian": "vegetarian",
    "jain": "jain",
    "halal": "halal",
    "kosher": "kosher",
    "hindu_veg": "hindu_vegetarian",
    "hindu_vegetarian": "hindu_vegetarian",
    "hindu_non_veg": "hindu_non_vegetarian",
    "hindu_non_vegetarian": "hindu_non_vegetarian",
    "lacto_vegetarian": "lacto_vegetarian",
    "ovo_vegetarian": "ovo_vegetarian",
    "pescatarian": "pescatarian",
    "gluten_free": "gluten_free",
    "dairy_free": "dairy_free",
    "egg_free": "egg_free",
    "no_onion": "no_onion",
    "no_garlic": "no_garlic",
    "no_alcohol": "no_alcohol",
}
# Allergen profile key -> restriction_id
ALLERGEN_TO_RESTRICTION_ID = {
    "peanut": "peanut_allergy",
    "peanuts": "peanut_allergy",
    "nut": "tree_nut_allergy",
    "nuts": "tree_nut_allergy",
    "tree_nut": "tree_nut_allergy",
    "soy": "soy_allergy",
    "shellfish": "shellfish_allergy",
    "fish": "fish_allergy",
    "sesame": "sesame_allergy",
    "onion": "onion_allergy",
    "garlic": "garlic_allergy",
    "gluten": "gluten_free",
    "wheat": "gluten_free",
    "milk": "dairy_free",
    "dairy": "dairy_free",
    "egg": "egg_free",
    "eggs": "egg_free",
    "mustard": "mustard_allergy",
    "celery": "celery_allergy",
}

# Dietary / religious / lifestyle: raw value (lower, underscores) -> restriction_id
DIETARY_RELIGIOUS_LIFESTYLE_TO_ID = {
    "vegan": "vegan",
    "vegetarian": "vegetarian",
    "jain": "jain",
    "halal": "halal",
    "kosher": "kosher",
    "hindu_veg": "hindu_vegetarian",
    "hindu_vegetarian": "hindu_vegetarian",
    "hindu_non_veg": "hindu_non_vegetarian",
    "hindu_non_vegetarian": "hindu_non_vegetarian",
    "lacto_vegetarian": "lacto_vegetarian",
    "ovo_vegetarian": "ovo_vegetarian",
    "pescatarian": "pescatarian",
    "gluten_free": "gluten_free",
    "dairy_free": "dairy_free",
    "egg_free": "egg_free",
    "no_onion": "no_onion",
    "no_garlic": "no_garlic",
    "no_alcohol": "no_alcohol",
    "no_insect_derived": "no_insect_derived",
    "no_palm_oil": "no_palm_oil",
    "no_artificial_colors": "no_artificial_colors",
    "no_gmos": "no_gmos",
    "no_seed_oils": "no_seed_oils",
    "keto": "keto",
    "paleo": "paleo",
}


def _normalize_key(s: str) -> str:
    return (s or "").lower().strip().replace(" ", "_").replace("-", "_")


def profile_to_restriction_ids(user_profile: Optional[Dict[str, Any]]) -> List[str]:
    """Build restriction_ids from userProfile dict (legacy or new shape: dietary_preference/diet + allergens + lifestyle + religious)."""
    ids = []
    if not user_profile:
        return ids
    # New shape: dietary_preference; legacy: diet
    pref = (user_profile.get("dietary_preference") or user_profile.get("diet") or "").lower().strip().replace(" ", "_")
    if pref and pref != "no_rules" and pref != "no rules":
        if pref in DIETARY_PREFERENCE_TO_RESTRICTION_ID:
            rid = DIETARY_PREFERENCE_TO_RESTRICTION_ID[pref]
            if rid not in ids:
                ids.append(rid)
        elif pref in PROFILE_DIET_TO_RESTRICTION_ID:
            rid = PROFILE_DIET_TO_RESTRICTION_ID[pref]
            if rid not in ids:
                ids.append(rid)
    if not user_profile.get("dairy_allowed", True):
        if "dairy_free" not in ids:
            ids.append("dairy_free")
    for a in user_profile.get("allergens", []) or user_profile.get("allergies", []):
        key = _normalize_key(str(a))
        if key in ALLERGEN_TO_RESTRICTION_ID:
            rid = ALLERGEN_TO_RESTRICTION_ID[key]
            if rid not in ids:
                ids.append(rid)
    for v in user_profile.get("lifestyle", []) or user_profile.get("lifestyle_flags", []):
        key = _normalize_key(str(v))
        if key in DIETARY_RELIGIOUS_LIFESTYLE_TO_ID and DIETARY_RELIGIOUS_LIFESTYLE_TO_ID[key] not in ids:
            ids.append(DIETARY_RELIGIOUS_LIFESTYLE_TO_ID[key])
    return ids


def user_profile_model_to_restriction_ids(profile: "UserProfile") -> List[str]:
    """Build restriction_ids from UserProfile (dietary_preference + allergens + lifestyle)."""
    ids: List[str] = []
    seen: set = set()

    def add(rid: str) -> None:
        if rid and rid not in seen:
            seen.add(rid)
            ids.append(rid)

    # Primary dietary preference (covers both dietary and religious diets)
    pref = (profile.dietary_preference or "no rules").lower().strip()
    if pref and pref != "no rules":
        if pref in DIETARY_PREFERENCE_TO_RESTRICTION_ID:
            add(DIETARY_PREFERENCE_TO_RESTRICTION_ID[pref])
        else:
            key = _normalize_key(pref)
            if key in DIETARY_RELIGIOUS_LIFESTYLE_TO_ID:
                add(DIETARY_RELIGIOUS_LIFESTYLE_TO_ID[key])

    # Allergens
    for a in profile.allergens or []:
        key = _normalize_key(str(a))
        if key in ALLERGEN_TO_RESTRICTION_ID:
            add(ALLERGEN_TO_RESTRICTION_ID[key])
        elif key in DIETARY_RELIGIOUS_LIFESTYLE_TO_ID:
            add(DIETARY_RELIGIOUS_LIFESTYLE_TO_ID[key])

    # Lifestyle
    for v in profile.lifestyle or []:
        key = _normalize_key(str(v))
        if key in DIETARY_RELIGIOUS_LIFESTYLE_TO_ID:
            add(DIETARY_RELIGIOUS_LIFESTYLE_TO_ID[key])
    return ids


def verdict_to_legacy_scorecard(verdict: ComplianceVerdict) -> Dict[str, Dict[str, str]]:
    """Build legacy scan scorecard shape: { 'Vegan': { status: 'red'|'yellow'|'green', reason } }."""
    scorecard = {}
    for label in SCAN_DIET_LABELS:
        rid = DIET_LABEL_TO_RESTRICTION_ID.get(label)
        if rid and rid in verdict.triggered_restrictions:
            scorecard[label] = {"status": "red", "reason": f"Contains ingredients not suitable for {label}."}
        else:
            scorecard[label] = {"status": "green", "reason": "No forbidden ingredients detected."}
    return scorecard


def preprocess_ingredient_list(ingredients: List[str]) -> Tuple[List[str], Set[str]]:
    """
    Preprocess a list of (possibly complex) ingredient strings into atomic names and trace keys.
    Uses flatten_ingredients (parser) for parentheses + processed-food expansion (e.g. potato chips -> potato, oil, salt).
    Uses ingredient_parser for <2% trace detection. Returns (normalized names for evaluation, trace keys).
    """
    flattened: List[str] = []
    trace_keys: Set[str] = set()
    for s in ingredients:
        if not s or not str(s).strip():
            continue
        s = str(s).strip()
        # Trace detection from raw string
        items = preprocess_ingredients(s)
        trace_set_this = get_trace_keys(items)
        # Flatten each segment (expands processed foods and parentheses)
        for x in items:
            atoms = flatten_ingredients(x["name"])
            for a in atoms:
                flattened.append(a)
                if x.get("trace"):
                    trace_keys.add(a)
        # If no items from preprocess (e.g. single "potato chips"), flatten whole string
        if not items:
            atoms = flatten_ingredients(s)
            for a in atoms:
                flattened.append(a)
    return (flattened, trace_keys)


def run_new_engine_scan(
    ingredients: List[str],
    user_profile: Optional[Dict[str, Any]] = None,
) -> tuple[ComplianceVerdict, Dict[str, Dict[str, str]]]:
    """Run compliance engine for scan. Flattens ingredients (parentheses, processed foods), trace detection, then evaluates."""
    restriction_ids = [DIET_LABEL_TO_RESTRICTION_ID[l] for l in SCAN_DIET_LABELS]
    atomic_names, trace_keys = preprocess_ingredient_list(ingredients)
    engine = ComplianceEngine()
    verdict = engine.evaluate(
        atomic_names,
        restriction_ids=restriction_ids,
        trace_ingredient_keys=trace_keys if trace_keys else None,
    )
    scorecard = verdict_to_legacy_scorecard(verdict)
    return verdict, scorecard


def run_new_engine_chat(
    ingredients: List[str],
    user_profile: Optional[Any] = None,
    restriction_ids: Optional[List[str]] = None,
    profile_context: Optional[Dict[str, Any]] = None,
    use_api_fallback: bool = True,
) -> ComplianceVerdict:
    """Run compliance engine for chat. Flattens ingredients (parser + trace), evaluates against profile."""
    if restriction_ids is not None:
        rids = restriction_ids
    elif hasattr(user_profile, "dietary_preference"):
        rids = user_profile_model_to_restriction_ids(user_profile)
    else:
        rids = profile_to_restriction_ids(user_profile if isinstance(user_profile, dict) else None)
    # Do NOT default to broad diets when user has no restrictions.
    # Empty rids = no restrictions = everything is SAFE for this user.
    # Only the scan path should evaluate against multiple diets unconditionally.
    atomic_names, trace_keys = preprocess_ingredient_list(ingredients)
    logger.info(
        "COMPLIANCE preprocess normalized_count=%d trace_count=%d profile_context=%s",
        len(atomic_names), len(trace_keys), bool(profile_context),
    )
    if trace_keys:
        logger.info("COMPLIANCE minor_ingredient_flags keys=%s", list(trace_keys)[:20])
    engine = ComplianceEngine()
    return engine.evaluate(
        atomic_names,
        restriction_ids=rids,
        trace_ingredient_keys=trace_keys if trace_keys else None,
        use_api_fallback=use_api_fallback,
        profile_context=profile_context,
    )


def _legacy_profile_from_dict(data: Optional[Dict[str, Any]]) -> "Any":
    """Build legacy UserProfile (ingredient_ontology) from dict. Supports both legacy and core profile shape."""
    try:
        from ingredient_ontology import UserProfile
    except ImportError:
        return None
    if not data:
        return UserProfile("general", True, set())
    algs = set(data.get("allergens", []) or data.get("allergies", []))
    d = (data.get("diet") or "general").lower().replace(" ", "_")
    if d == "general" and (data.get("dietary_restrictions") or data.get("religious_preferences")):
        for lst in (data.get("dietary_restrictions") or [], data.get("religious_preferences") or []):
            for v in lst or []:
                vn = (v or "").lower().replace(" ", "_")
                if vn in ("vegan", "vegetarian", "jain", "halal", "kosher", "hindu_veg", "hindu_non_veg"):
                    d = vn
                    break
            if d != "general":
                break
    if d in ("no_specific_rules", "none"):
        d = "general"
    dairy_ok = data.get("dairy_allowed", True)
    if "dairy_free" in (data.get("dietary_restrictions") or []) or "dairy_free" in (data.get("lifestyle_flags") or []):
        dairy_ok = False
    return UserProfile(diet=d, dairy_allowed=dairy_ok, allergens=algs)


def run_legacy_chat(ingredients: List[str], user_profile: Optional[Dict[str, Any]] = None) -> str:
    """
    Run legacy ingredient_ontology.evaluate_ingredient_risk per ingredient and aggregate.
    Returns "SAFE" | "NOT_SAFE" | "UNCERTAIN" for shadow comparison.
    """
    try:
        from ingredient_ontology import evaluate_ingredient_risk
    except ImportError:
        return "UNCERTAIN"
    profile = _legacy_profile_from_dict(user_profile)
    if profile is None:
        return "UNCERTAIN"
    statuses = []
    for ing in ingredients:
        if not (ing or "").strip():
            continue
        r = evaluate_ingredient_risk(ing.strip(), profile)
        statuses.append(r.get("status", "UNCLEAR"))
    if not statuses:
        return "UNCERTAIN"
    if any(s == "NOT_SAFE" for s in statuses):
        return "NOT_SAFE"
    if any(s == "UNCLEAR" or s == "UNCERTAIN" for s in statuses):
        return "UNCERTAIN"
    return "SAFE"


def run_new_engine_for_claimed_diets(
    ingredients: List[str], claimed_diet_types: List[str]
) -> tuple[ComplianceVerdict, Dict[str, Dict[str, str]]]:
    """Run compliance engine for verification. Preprocesses ingredients then evaluates."""
    restriction_ids = []
    for label in claimed_diet_types:
        rid = CLAIMED_DIET_TO_RESTRICTION_ID.get((label or "").strip())
        if rid and rid not in restriction_ids:
            restriction_ids.append(rid)
    if not restriction_ids:
        restriction_ids = list(CLAIMED_DIET_TO_RESTRICTION_ID.values())[:4]
    atomic_names, trace_keys = preprocess_ingredient_list(ingredients)
    engine = ComplianceEngine()
    verdict = engine.evaluate(
        atomic_names,
        restriction_ids=restriction_ids,
        trace_ingredient_keys=trace_keys if trace_keys else None,
    )
    scorecard = {}
    for label in claimed_diet_types:
        rid = CLAIMED_DIET_TO_RESTRICTION_ID.get((label or "").strip())
        if rid:
            scorecard[label] = (
                {"status": "red", "reason": f"Contains ingredients not suitable for {label}."}
                if rid in verdict.triggered_restrictions
                else {"status": "green", "reason": "No forbidden ingredients detected."}
            )
    return verdict, scorecard


def get_diet_tags_from_verdict_scan(verdict: ComplianceVerdict) -> List[str]:
    """From run_new_engine_scan verdict, return ['Vegan'] or ['Vegetarian'] or [] (Omnivore)."""
    if "vegan" not in verdict.triggered_restrictions:
        return ["Vegan"]
    if "hindu_vegetarian" not in verdict.triggered_restrictions:
        return ["Vegetarian"]
    return []


def extract_query_filters(query: str) -> Dict[str, List[str]]:
    """Extract dietary and allergen filters from natural language query. Returns {dietary: [...], allergens: [...]} for RAG."""
    q = query.lower()
    dietary = []
    allergens = []
    if "vegan" in q:
        dietary.append("Vegan")
    if "vegetarian" in q:
        dietary.append("Vegetarian")
    if "jain" in q:
        dietary.append("Jain")
    if "halal" in q:
        dietary.append("Halal")
    if "gluten" in q and ("free" in q or "allerg" in q or "no " in q):
        allergens.append("Wheat/Gluten")
    trigger = "allerg" in q or "free" in q or "no " in q or "without" in q
    if "peanut" in q and trigger and "Peanuts" not in allergens:
        allergens.append("Peanuts")
    if "nut" in q and trigger:
        if "Tree Nuts" not in allergens:
            allergens.append("Tree Nuts")
        if "Peanuts" not in allergens and "peanut" not in q:
            allergens.append("Peanuts")
    for term, rids in [("dairy", "Dairy"), ("milk", "Dairy"), ("egg", "Eggs"), ("soy", "Soy"), ("fish", "Fish"), ("shellfish", "Shellfish")]:
        if term in q and trigger and rids not in allergens:
            allergens.append(rids)
    return {"dietary": dietary, "allergens": list(dict.fromkeys(allergens))}


# Simple cuisine detection (keyword-based, no dependency on dietary_rules)
CUISINE_KEYWORDS = {
    "Italian": ["pasta", "pizza", "risotto", "spaghetti", "lasagna", "mozzarella", "basil", "oregano"],
    "Mexican": ["taco", "burrito", "quesadilla", "salsa", "tortilla", "jalapeno", "cilantro"],
    "Indian": ["curry", "masala", "tikka", "naan", "paneer", "biryani", "tandoori", "samosa", "chutney", "dal"],
    "Chinese": ["noodle", "fried rice", "dim sum", "soy sauce", "tofu", "wok", "dumpling"],
    "American": ["burger", "fries", "steak", "bbq", "sandwich", "wings"],
    "Japanese": ["sushi", "ramen", "tempura", "miso", "teriyaki", "sashimi", "udon", "wasabi"],
    "Mediterranean": ["hummus", "falafel", "pita", "olive", "feta", "gyro", "tzatziki", "kebab"],
    "Thai": ["pad thai", "curry", "lemongrass", "coconut milk", "satay", "tom yum"],
}


def detect_cuisine(text: str) -> str:
    """Detect cuisine from name + description. Returns cuisine name or 'Global'."""
    t = text.lower()
    best = "Global"
    best_count = 0
    for cuisine, keywords in CUISINE_KEYWORDS.items():
        n = sum(1 for k in keywords if k in t)
        if n > best_count:
            best_count = n
            best = cuisine
    return best


def get_allergens_from_ingredients(ingredients: List[str]) -> List[str]:
    """Run compliance engine with allergy restrictions; return list of allergen labels that triggered."""
    allergy_rids = ["peanut_allergy", "tree_nut_allergy", "soy_allergy", "shellfish_allergy", "fish_allergy", "sesame_allergy", "onion_allergy", "garlic_allergy"]
    engine = ComplianceEngine()
    verdict = engine.evaluate(ingredients, restriction_ids=allergy_rids)
    rid_to_label = {
        "peanut_allergy": "Peanuts", "tree_nut_allergy": "Tree Nuts", "soy_allergy": "Soy",
        "shellfish_allergy": "Shellfish", "fish_allergy": "Fish", "sesame_allergy": "Sesame",
        "onion_allergy": "Onion", "garlic_allergy": "Garlic",
    }
    return [rid_to_label[r] for r in verdict.triggered_restrictions if r in rid_to_label]
