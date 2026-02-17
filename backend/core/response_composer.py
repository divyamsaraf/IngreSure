"""
Human-like response composer for the grocery safety assistant.
Converts structured compliance verdicts + context into conversational text.
No robotic templates. No internal jargon unless explicitly requested.
"""
import logging
from typing import List, Optional, Dict, Any

from core.models.verdict import ComplianceVerdict, VerdictStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Restriction → human-readable diet label
# ---------------------------------------------------------------------------
_RESTRICTION_DISPLAY: Dict[str, str] = {
    "jain": "Jain",
    "vegan": "vegan",
    "vegetarian": "vegetarian",
    "halal": "Halal",
    "kosher": "Kosher",
    "hindu_vegetarian": "Hindu vegetarian",
    "hindu_non_vegetarian": "Hindu non-vegetarian",
    "lacto_vegetarian": "lacto-vegetarian",
    "ovo_vegetarian": "ovo-vegetarian",
    "pescatarian": "pescatarian",
    "dairy_free": "dairy-free",
    "egg_free": "egg-free",
    "gluten_free": "gluten-free",
    "peanut_allergy": "peanut allergy",
    "tree_nut_allergy": "tree-nut allergy",
    "soy_allergy": "soy allergy",
    "shellfish_allergy": "shellfish allergy",
    "fish_allergy": "fish allergy",
    "sesame_allergy": "sesame allergy",
    "no_alcohol": "no-alcohol",
    "no_onion": "no-onion",
    "no_garlic": "no-garlic",
}

# Ingredient → short reason why it fails a given restriction category
_INGREDIENT_REASONS: Dict[str, str] = {
    "egg": "animal-derived",
    "eggs": "animal-derived",
    "cheese": "dairy product",
    "milk": "dairy product",
    "butter": "dairy product",
    "cream": "dairy product",
    "yogurt": "dairy product",
    "ghee": "dairy product (clarified butter)",
    "gelatin": "derived from animal bones/skin",
    "honey": "produced by insects",
    "beef": "meat (cow)",
    "chicken": "meat (poultry)",
    "pork": "meat (pig)",
    "lamb": "meat",
    "fish": "seafood",
    "tuna": "fish (seafood)",
    "salmon": "fish (seafood)",
    "shrimp": "shellfish",
    "prawn": "shellfish",
    "onion": "root vegetable (restricted)",
    "garlic": "root vegetable (restricted)",
    "potato": "root vegetable (restricted)",
    "carrot": "root vegetable (restricted)",
    "beet": "root vegetable (restricted)",
    "beetroot": "root vegetable (restricted)",
    "radish": "root vegetable (restricted)",
    "turnip": "root vegetable (restricted)",
    "sweet potato": "root vegetable (restricted)",
    "yam": "root vegetable (restricted)",
    "shallot": "root vegetable, onion family (restricted)",
    "leek": "root vegetable, onion family (restricted)",
    "ginger": "root vegetable (restricted)",
    "mushroom": "fungal (restricted in strict Jain diet)",
    "alcohol": "contains alcohol",
    "wine": "contains alcohol",
    "beer": "contains alcohol",
    "vodka": "contains alcohol",
    "collagen": "derived from animal tissue",
    "lard": "animal fat (pig)",
    "rennet": "animal-derived",
    "isinglass": "derived from fish bladders",
    "castoreum": "animal secretion",
    "shellac": "insect-derived",
    "carmine": "insect-derived",
    "l-cysteine": "can be derived from animal hair/feathers",
    "bacon": "meat (pork-derived)",
    "ham": "meat (pork-derived)",
    "turkey": "meat (poultry)",
    "duck": "meat (poultry)",
    "veal": "meat (calf)",
    "mutton": "meat (sheep)",
    "goat": "meat",
    "venison": "meat (deer)",
    "anchovy": "fish (seafood)",
    "sardine": "fish (seafood)",
    "squid": "seafood",
    "octopus": "seafood",
    "crab": "shellfish",
    "lobster": "shellfish",
    "whey": "dairy-derived",
    "paneer": "dairy product (cheese)",
    "curd": "dairy product",
    "tofu": "soy-derived",
    "truffle": "fungal (restricted in strict Jain diet)",
    "peanut": "nut (common allergen)",
    "almond": "tree nut",
    "walnut": "tree nut",
    "cashew": "tree nut",
    "hazelnut": "tree nut",
    "pecan": "tree nut",
    "soy": "soy-derived (allergen)",
}

# Product/container words that are not real ingredients — skip from safe lists
_PRODUCT_WORDS = {
    "burger", "bar", "protein bar", "protin bar", "energy bar",
    "cake", "bread", "sandwich", "wrap", "pizza", "pie",
    "cookie", "cookies", "biscuit", "biscuits", "cracker", "crackers",
    "chip", "chips", "crisp", "crisps",
    "noodle", "noodles", "pasta", "ramen",
    "soup", "salad", "stew", "curry",
    "juice", "drink", "smoothie", "shake", "milkshake",
    "cereal", "granola", "muesli",
    "muffin", "bagel", "pancake", "waffle", "toast", "roll", "bun",
    "doughnut", "donut", "pastry", "croissant",
    "ice cream", "gelato", "sorbet", "pudding", "custard",
    "candy", "chocolate bar", "snack", "snacks",
    "sausage", "hotdog", "hot dog", "kebab",
}

# Ingredients that are always plural in English
_ALWAYS_PLURAL = {"eggs", "oats", "lentils", "beans", "peas", "fries", "noodles", "nuts", "seeds"}

# Nouns that end in 's' but are singular
_SINGULAR_S_WORDS = {
    "asparagus", "hummus", "couscous", "molasses", "floss", "bass",
    "grass", "glass", "gas", "bus", "lens", "is",
}


def _is_plural(ingredient: str) -> bool:
    """Check if an ingredient name is likely plural (for grammar: is/are)."""
    w = ingredient.lower().strip()
    if w in _ALWAYS_PLURAL:
        return True
    if w in _SINGULAR_S_WORDS:
        return False
    return w.endswith("s") and not w.endswith("ss") and len(w) > 2


def _display_name(ingredient: str) -> str:
    """Format ingredient for bold display: capitalize first letter."""
    s = ingredient.strip()
    if not s:
        return s
    return s[0].upper() + s[1:]


def _is_product_word(ingredient: str) -> bool:
    """Check if this is a product/container word rather than a real ingredient."""
    return ingredient.lower().strip() in _PRODUCT_WORDS


def _diet_label(profile: Any) -> str:
    """Extract a human-readable diet label from profile."""
    if hasattr(profile, "dietary_preference"):
        dp = profile.dietary_preference
    elif isinstance(profile, dict):
        dp = profile.get("dietary_preference", "")
    else:
        dp = ""
    return dp if dp and dp != "No rules" else "your dietary preferences"


def _ingredient_reason(ingredient: str) -> str:
    """Return a short reason string for an ingredient, handling plurals."""
    key = ingredient.lower().strip()
    reason = _INGREDIENT_REASONS.get(key)
    if reason:
        return reason
    norm = _normalize_for_match(key)
    reason = _INGREDIENT_REASONS.get(norm)
    if reason:
        return reason
    return "may conflict with your dietary requirements"


def _restriction_label(restriction_id: str) -> str:
    return _RESTRICTION_DISPLAY.get(restriction_id, restriction_id.replace("_", " "))


def _normalize_for_match(s: str) -> str:
    """Normalize ingredient name for matching: lowercase, strip trailing s/es."""
    s = s.lower().strip()
    if s.endswith("es") and len(s) > 3:
        return s[:-2]
    if s.endswith("s") and len(s) > 2:
        return s[:-1]
    return s


# ---------------------------------------------------------------------------
# Greeting
# ---------------------------------------------------------------------------
def compose_greeting() -> str:
    return (
        "Hello! I'm your grocery safety assistant. "
        "Tell me your dietary preferences and ask about any ingredient — "
        "I'll let you know if it's suitable for you."
    )


# ---------------------------------------------------------------------------
# Profile-update acknowledgment
# ---------------------------------------------------------------------------
def compose_profile_update(
    profile: Any,
    updated_fields: Dict[str, Any],
    has_ingredients: bool = False,
) -> str:
    """Acknowledge a profile update, optionally hinting the user can now ask about ingredients."""
    parts: List[str] = []

    if "dietary_preference" in updated_fields:
        parts.append(f"Got it — I've updated your profile to **{updated_fields['dietary_preference']}**.")
    if "allergens" in updated_fields:
        als = updated_fields["allergens"]
        parts.append(f"Noted your allergen{'s' if len(als) != 1 else ''}: **{', '.join(als)}**.")
    if "remove_allergens" in updated_fields:
        als = updated_fields["remove_allergens"]
        parts.append(f"Removed allergen{'s' if len(als) != 1 else ''}: **{', '.join(als)}**.")
    if "lifestyle" in updated_fields:
        parts.append(f"Lifestyle preference{'s' if len(updated_fields['lifestyle']) != 1 else ''} saved: **{', '.join(updated_fields['lifestyle'])}**.")

    if not has_ingredients:
        parts.append("What would you like me to check for you?")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Compliance verdict → conversational answer
# ---------------------------------------------------------------------------
def compose_verdict(
    verdict: ComplianceVerdict,
    profile: Any,
    ingredients: List[str],
    profile_was_updated: bool = False,
    updated_fields: Optional[Dict[str, Any]] = None,
    display_names: Optional[Dict[str, str]] = None,
) -> str:
    """
    Convert a compliance verdict into a human-friendly response.

    Args:
        display_names: Optional map of {ingredient_lower: compound_display_name}
                       e.g. {"chicken": "burger with chicken"}
                       Used to show the full product name in the response.
    """
    parts: List[str] = []
    diet = _diet_label(profile)
    dn = display_names or {}

    def _show(ing: str) -> str:
        """Get the display name for an ingredient (compound or plain).
        Also checks normalized (singular) form for display_map lookup so
        that 'eggs' correctly maps to a compound keyed by 'egg', etc."""
        key = ing.lower().strip()
        compound = dn.get(key)
        if compound:
            return _display_name(compound)
        # Try normalized (singular) form
        norm = _normalize_for_match(ing)
        compound = dn.get(norm)
        if compound:
            return _display_name(compound)
        return _display_name(ing)

    # Lead with profile acknowledgment if updated in this turn
    if profile_was_updated and updated_fields:
        ack = compose_profile_update(profile, updated_fields, has_ingredients=True)
        parts.append(ack)
        parts.append("")  # blank line

    # Compute safe ingredients (not triggered, not uncertain)
    triggered = verdict.triggered_ingredients or []
    uncertain = verdict.uncertain_ingredients or []
    triggered_norm = {_normalize_for_match(i) for i in triggered}
    uncertain_norm = {_normalize_for_match(i) for i in uncertain}
    safe_ingredients = [
        i for i in ingredients
        if _normalize_for_match(i) not in triggered_norm
        and _normalize_for_match(i) not in uncertain_norm
    ]

    # Filter out product/container words from safe list (not real ingredients)
    meaningful_safe = [i for i in safe_ingredients if not _is_product_word(i)]

    # Suppress safe ingredients whose compound display is already used by a
    # triggered ingredient (e.g. "butter chicken" has butter=safe, chicken=triggered
    # → don't show "butter chicken" as both safe AND not-safe).
    if dn:
        def _dn_lookup(ingredient: str) -> Optional[str]:
            key = ingredient.lower().strip()
            return dn.get(key) or dn.get(_normalize_for_match(ingredient))

        triggered_display = {
            _dn_lookup(i) for i in triggered if _dn_lookup(i)
        }
        meaningful_safe = [
            s for s in meaningful_safe
            if _dn_lookup(s) not in triggered_display
        ]

    # ------ NOT_SAFE ------
    if verdict.status == VerdictStatus.NOT_SAFE:
        restrictions = verdict.triggered_restrictions or []

        if len(triggered) == 1 and not meaningful_safe and not uncertain:
            ing = triggered[0]
            reason = _ingredient_reason(ing)
            name = _show(ing)
            verb = "are" if _is_plural(ing) else "is"
            parts.append(
                f"Based on your **{diet}** diet, **{name}** {verb} **not suitable** — {reason}."
            )
        elif triggered:
            parts.append(f"Based on your **{diet}** diet, the following {'are' if len(triggered) > 1 else 'is'} **not suitable**:\n")
            for ing in triggered:
                reason = _ingredient_reason(ing)
                parts.append(f"- **{_show(ing)}** — {reason}")
        else:
            restriction_names = ", ".join(_restriction_label(r) for r in restrictions[:3])
            parts.append(
                f"This doesn't appear to be compatible with your **{diet}** diet "
                f"(conflicts with: {restriction_names})."
            )

        # Show meaningful SAFE ingredients (with compound names if applicable)
        if meaningful_safe:
            if len(meaningful_safe) == 1:
                s = meaningful_safe[0]
                verb = "are" if _is_plural(s) else "is"
                parts.append(f"\n**{_show(s)}** {verb} fine for your diet.")
            else:
                safe_str = ", ".join(f"**{_show(s)}**" for s in meaningful_safe)
                parts.append(f"\nThe rest — {safe_str} — are fine for your diet.")

        # Show UNCERTAIN ingredients
        if uncertain:
            items = ", ".join(f"**{_show(u)}**" for u in uncertain)
            parts.append(f"\nCouldn't verify {items} — may need manual checking.")

        # Minor/informational note
        if verdict.informational_ingredients and verdict.confidence_score < 1.0:
            minors = ", ".join(verdict.informational_ingredients)
            parts.append(f"\n_Note: {minors} — present in trace amounts, flagged at low confidence._")

    # ------ SAFE ------
    elif verdict.status == VerdictStatus.SAFE:
        meaningful_ings = [i for i in ingredients if not _is_product_word(i)]
        if not meaningful_ings:
            meaningful_ings = ingredients

        if len(meaningful_ings) == 1:
            ing = meaningful_ings[0]
            verb = "are" if _is_plural(ing) else "is"
            parts.append(f"**{_show(ing)}** {verb} perfectly fine for your **{diet}** diet.")
        else:
            ing_str = ", ".join(f"**{_show(i)}**" for i in meaningful_ings)
            parts.append(
                f"All good — {ing_str} are compatible with your **{diet}** diet."
            )
        if verdict.informational_ingredients and verdict.confidence_score < 1.0:
            minors = ", ".join(verdict.informational_ingredients)
            parts.append(f"\n_Note: {minors} — present in trace amounts._")

    # ------ UNCERTAIN ------
    elif verdict.status == VerdictStatus.UNCERTAIN:
        if uncertain:
            items = ", ".join(f"**{_show(u)}**" for u in uncertain)
            parts.append(
                f"Couldn't find reliable information about {items} — "
                f"may require manual verification before consumption."
            )
            if meaningful_safe:
                safe_str = ", ".join(f"**{_show(s)}**" for s in meaningful_safe)
                parts.append(f"\nThe rest — {safe_str} — are fine for your diet.")
        else:
            ingredient_str = ", ".join(f"**{_show(i)}**" for i in ingredients)
            parts.append(
                f"Wasn't able to determine the safety of {ingredient_str} with certainty. "
                f"Please double-check the packaging or consult a specialist."
            )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# General / fallback
# ---------------------------------------------------------------------------
def compose_general_question() -> str:
    return (
        "I'm best at checking whether specific ingredients are safe for your dietary profile. "
        "Try asking something like: **\"Can I eat eggs?\"** or paste an ingredient list and I'll analyze it."
    )


def compose_no_ingredients() -> str:
    return (
        "It looks like you didn't mention any specific ingredients. "
        "Try something like **\"Can I eat eggs?\"** or paste an ingredient list from a product label."
    )
