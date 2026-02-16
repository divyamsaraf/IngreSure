"""
Bridge: map profile/legacy diet names to restriction_ids; build legacy-shaped scorecard from verdict.
Used by scan and chat when USE_NEW_ENGINE is True.
"""
import logging
from typing import Dict, List, Any, Optional

from core.evaluation.compliance_engine import ComplianceEngine
from core.models.verdict import ComplianceVerdict, VerdictStatus

logger = logging.getLogger(__name__)

# Legacy scan scorecard diet labels -> restriction_ids
SCAN_DIET_LABELS = ["Vegan", "Jain", "Halal", "Hindu Veg"]
DIET_LABEL_TO_RESTRICTION_ID = {
    "Vegan": "vegan",
    "Jain": "jain",
    "Halal": "halal",
    "Hindu Veg": "hindu_vegetarian",
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
}


def profile_to_restriction_ids(user_profile: Optional[Dict[str, Any]]) -> List[str]:
    """Build restriction_ids from userProfile (diet + allergens)."""
    ids = []
    if not user_profile:
        return ids
    diet = (user_profile.get("diet") or "").lower().replace(" ", "_")
    if diet and diet in PROFILE_DIET_TO_RESTRICTION_ID:
        rid = PROFILE_DIET_TO_RESTRICTION_ID[diet]
        if rid not in ids:
            ids.append(rid)
    if not user_profile.get("dairy_allowed", True):
        if "dairy_free" not in ids:
            ids.append("dairy_free")
    for a in user_profile.get("allergens", []) or user_profile.get("allergies", []):
        key = (a or "").lower().strip()
        if key in ALLERGEN_TO_RESTRICTION_ID:
            rid = ALLERGEN_TO_RESTRICTION_ID[key]
            if rid not in ids:
                ids.append(rid)
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


def run_new_engine_scan(ingredients: List[str]) -> tuple[ComplianceVerdict, Dict[str, Dict[str, str]]]:
    """Run compliance engine for scan (all scan diets). Returns (verdict, legacy_scorecard)."""
    restriction_ids = [DIET_LABEL_TO_RESTRICTION_ID[l] for l in SCAN_DIET_LABELS]
    engine = ComplianceEngine()
    verdict = engine.evaluate(ingredients, restriction_ids=restriction_ids)
    scorecard = verdict_to_legacy_scorecard(verdict)
    return verdict, scorecard


def run_new_engine_chat(ingredients: List[str], user_profile: Optional[Dict[str, Any]]) -> ComplianceVerdict:
    """Run compliance engine for chat (profile-driven restrictions)."""
    restriction_ids = profile_to_restriction_ids(user_profile)
    if not restriction_ids:
        restriction_ids = ["vegan", "vegetarian", "jain", "halal", "hindu_vegetarian"]
    engine = ComplianceEngine()
    return engine.evaluate(ingredients, restriction_ids=restriction_ids)
