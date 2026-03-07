"""
Bridge: map profile/legacy diet names to restriction_ids; build legacy-shaped scorecard from verdict.
"""
import logging
from typing import Dict, List, Any, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.user_profile import UserProfile

from core.evaluation.compliance_engine import ComplianceEngine
from core.models.verdict import ComplianceVerdict, VerdictStatus
from core.parsing.ingredient_parser import preprocess_ingredients
from core.normalization.parser import flatten_ingredients

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping dictionaries (single source of truth)
# ---------------------------------------------------------------------------

# Scan scorecard diet labels -> restriction_ids
SCAN_DIET_LABELS = ["Vegan", "Jain", "Halal", "Hindu Veg"]
DIET_LABEL_TO_RESTRICTION_ID: Dict[str, str] = {
    "Vegan": "vegan",
    "Jain": "jain",
    "Halal": "halal",
    "Hindu Veg": "hindu_vegetarian",
}

# Claimed diet types (profile/tagging) -> restriction_id
CLAIMED_DIET_TO_RESTRICTION_ID: Dict[str, str] = {
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

# Dietary preference (display name, lowered) -> restriction_id
# Covers both dietary and religious diets. Used for user profiles.
DIETARY_PREFERENCE_TO_RESTRICTION_ID: Dict[str, str] = {
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
    # Underscore variants (from frontend/profile storage)
    "hindu_veg": "hindu_vegetarian",
    "hindu_vegetarian": "hindu_vegetarian",
    "hindu_non_veg": "hindu_non_vegetarian",
    "hindu_non_vegetarian": "hindu_non_vegetarian",
    "lacto_vegetarian": "lacto_vegetarian",
    "ovo_vegetarian": "ovo_vegetarian",
    "gluten_free": "gluten_free",
    "dairy_free": "dairy_free",
    "egg_free": "egg_free",
}

# Allergen profile key -> restriction_id
ALLERGEN_TO_RESTRICTION_ID: Dict[str, str] = {
    "peanut": "peanut_allergy",
    "peanuts": "peanut_allergy",
    "nut": "tree_nut_allergy",
    "nuts": "tree_nut_allergy",
    "tree_nut": "tree_nut_allergy",
    "tree_nuts": "tree_nut_allergy",
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
    "raisin": "raisin_allergy",
    "raisins": "raisin_allergy",
}

# Lifestyle flags -> restriction_id
LIFESTYLE_TO_RESTRICTION_ID: Dict[str, str] = {
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


# ---------------------------------------------------------------------------
# Profile -> restriction_ids
# ---------------------------------------------------------------------------

def profile_to_restriction_ids(user_profile: Optional[Dict[str, Any]]) -> List[str]:
    """Build restriction_ids from userProfile dict (supports both legacy and new field names)."""
    if not user_profile:
        return []
    ids: List[str] = []
    seen: Set[str] = set()

    def _add(rid: str) -> None:
        if rid and rid not in seen:
            seen.add(rid)
            ids.append(rid)

    # Dietary preference
    pref = _normalize_key(user_profile.get("dietary_preference") or user_profile.get("diet") or "")
    if pref and pref not in ("no_rules", "no rules"):
        rid = DIETARY_PREFERENCE_TO_RESTRICTION_ID.get(pref)
        if rid:
            _add(rid)

    if not user_profile.get("dairy_allowed", True):
        _add("dairy_free")

    # Allergens
    for a in user_profile.get("allergens", []) or user_profile.get("allergies", []):
        key = _normalize_key(str(a))
        rid = ALLERGEN_TO_RESTRICTION_ID.get(key)
        if rid:
            _add(rid)

    # Lifestyle
    for v in user_profile.get("lifestyle", []) or user_profile.get("lifestyle_flags", []):
        key = _normalize_key(str(v))
        rid = LIFESTYLE_TO_RESTRICTION_ID.get(key) or DIETARY_PREFERENCE_TO_RESTRICTION_ID.get(key)
        if rid:
            _add(rid)

    return ids


def user_profile_model_to_restriction_ids(profile: "UserProfile") -> List[str]:
    """Build restriction_ids from UserProfile model."""
    ids: List[str] = []
    seen: Set[str] = set()

    def _add(rid: str) -> None:
        if rid and rid not in seen:
            seen.add(rid)
            ids.append(rid)

    # Primary dietary preference
    pref = (profile.dietary_preference or "no rules").lower().strip()
    if pref and pref != "no rules":
        rid = DIETARY_PREFERENCE_TO_RESTRICTION_ID.get(pref)
        if not rid:
            key = _normalize_key(pref)
            rid = DIETARY_PREFERENCE_TO_RESTRICTION_ID.get(key) or LIFESTYLE_TO_RESTRICTION_ID.get(key)
        if rid:
            _add(rid)

    # Allergens
    for a in profile.allergens or []:
        key = _normalize_key(str(a))
        rid = ALLERGEN_TO_RESTRICTION_ID.get(key) or LIFESTYLE_TO_RESTRICTION_ID.get(key)
        if rid:
            _add(rid)

    # Lifestyle
    for v in profile.lifestyle or []:
        key = _normalize_key(str(v))
        rid = LIFESTYLE_TO_RESTRICTION_ID.get(key) or DIETARY_PREFERENCE_TO_RESTRICTION_ID.get(key)
        if rid:
            _add(rid)

    return ids


# ---------------------------------------------------------------------------
# Scorecard builders
# ---------------------------------------------------------------------------

def verdict_to_legacy_scorecard(verdict: ComplianceVerdict) -> Dict[str, Dict[str, str]]:
    """Build scan scorecard: { 'Vegan': { status: 'red'|'green', reason } }."""
    scorecard = {}
    for label in SCAN_DIET_LABELS:
        rid = DIET_LABEL_TO_RESTRICTION_ID.get(label)
        if rid and rid in verdict.triggered_restrictions:
            scorecard[label] = {"status": "red", "reason": f"Contains ingredients not suitable for {label}."}
        else:
            scorecard[label] = {"status": "green", "reason": "No forbidden ingredients detected."}
    return scorecard


# ---------------------------------------------------------------------------
# Ingredient preprocessing
# ---------------------------------------------------------------------------

def preprocess_ingredient_list(ingredients: List[str]) -> Tuple[List[str], Set[str]]:
    """Preprocess ingredient strings into atomic names and trace keys."""
    flattened: List[str] = []
    trace_keys: Set[str] = set()
    for s in ingredients:
        if not s or not str(s).strip():
            continue
        s = str(s).strip()
        items = preprocess_ingredients(s)
        for x in items:
            atoms = flatten_ingredients(x["name"])
            for a in atoms:
                flattened.append(a)
                if x.get("trace"):
                    trace_keys.add(a)
        if not items:
            atoms = flatten_ingredients(s)
            flattened.extend(atoms)
    return flattened, trace_keys


# ---------------------------------------------------------------------------
# Engine runners
# ---------------------------------------------------------------------------

def run_new_engine_scan(
    ingredients: List[str],
    user_profile: Optional[Dict[str, Any]] = None,
) -> Tuple[ComplianceVerdict, Dict[str, Dict[str, str]]]:
    """Run compliance engine for scan. Returns (verdict, scorecard)."""
    restriction_ids = [DIET_LABEL_TO_RESTRICTION_ID[l] for l in SCAN_DIET_LABELS]
    atomic_names, trace_keys = preprocess_ingredient_list(ingredients)
    engine = ComplianceEngine()
    verdict = engine.evaluate(
        atomic_names,
        restriction_ids=restriction_ids,
        trace_ingredient_keys=trace_keys or None,
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
    """Run compliance engine for chat."""
    if restriction_ids is not None:
        rids = restriction_ids
    elif hasattr(user_profile, "dietary_preference"):
        rids = user_profile_model_to_restriction_ids(user_profile)
    else:
        rids = profile_to_restriction_ids(user_profile if isinstance(user_profile, dict) else None)

    atomic_names, trace_keys = preprocess_ingredient_list(ingredients)
    logger.info(
        "COMPLIANCE preprocess normalized_count=%d trace_count=%d",
        len(atomic_names), len(trace_keys),
    )
    engine = ComplianceEngine()
    return engine.evaluate(
        atomic_names,
        restriction_ids=rids,
        trace_ingredient_keys=trace_keys or None,
        use_api_fallback=use_api_fallback,
        profile_context=profile_context,
    )

