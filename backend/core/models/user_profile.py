"""
Single persistent user profile for grocery safety.
dietary_preference, allergens, lifestyle, religious_preferences.
Updates merge without overwriting existing fields (partial updates).
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional

# Canonical display values for dietary preference
DIETARY_PREFERENCE_CHOICES = [
    "No rules",
    "Jain",
    "Vegan",
    "Vegetarian",
    "Hindu Veg",
    "Hindu Non Vegetarian",
    "Halal",
    "Kosher",
    "Lacto Vegetarian",
    "Ovo Vegetarian",
    "Pescatarian",
    "Gluten-Free",
    "Dairy-Free",
    "Egg-Free",
]

# Allergen options (display names)
ALLERGEN_CHOICES = [
    "Milk",
    "Egg",
    "Nuts",
    "Peanuts",
    "Tree Nuts",
    "Soy",
    "Wheat/Gluten",
    "Fish",
    "Shellfish",
    "Sesame",
    "Mustard",
    "Celery",
    "Other",
]

# Lifestyle flags
LIFESTYLE_CHOICES = ["no alcohol", "no insect derived", "no palm oil", "no onion", "no garlic"]

# Religious preference options
RELIGIOUS_PREFERENCE_CHOICES = ["halal", "kosher", "jain", "hindu vegetarian", "hindu non vegetarian"]


@dataclass
class UserProfile:
    """
    Single persistent profile per user.
    dietary_preference: primary diet (e.g. Jain, Vegan, No rules).
    allergens, lifestyle, religious_preferences: lists.
    """
    user_id: str
    dietary_preference: str = "No rules"
    allergens: List[str] = field(default_factory=list)
    lifestyle: List[str] = field(default_factory=list)
    religious_preferences: List[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        """True if profile has no meaningful constraints (first-time user)."""
        return (
            (not self.dietary_preference or self.dietary_preference == "No rules")
            and not self.allergens
            and not self.lifestyle
            and not self.religious_preferences
        )

    def update_merge(
        self,
        dietary_preference: Optional[str] = None,
        allergens: Optional[List[str]] = None,
        lifestyle: Optional[List[str]] = None,
        religious_preferences: Optional[List[str]] = None,
    ) -> None:
        """
        Update only provided fields; never set existing fields to None.
        Merges lists: provided list replaces that field; omit to leave unchanged.
        """
        if dietary_preference is not None:
            self.dietary_preference = dietary_preference
        if allergens is not None:
            self.allergens = list(allergens)
        if lifestyle is not None:
            self.lifestyle = list(lifestyle)
        if religious_preferences is not None:
            self.religious_preferences = list(religious_preferences)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """Load from dict; supports both new and legacy keys (dietary_restrictions, lifestyle_flags)."""
        user_id = str(data.get("user_id", ""))
        # New shape
        dietary = data.get("dietary_preference")
        if dietary is None:
            # Legacy: infer from dietary_restrictions or religious_preferences
            dr = data.get("dietary_restrictions") or []
            rp = data.get("religious_preferences") or []
            combined = (dr or []) + (rp or [])
            if combined:
                dietary = combined[0] if isinstance(combined[0], str) else "No rules"
            else:
                dietary = "No rules"
        if isinstance(dietary, str):
            dietary = dietary.strip() or "No rules"
        allergens = data.get("allergens")
        if allergens is None:
            allergens = data.get("allergies") or []
        lifestyle = data.get("lifestyle")
        if lifestyle is None:
            lifestyle = data.get("lifestyle_flags") or []
        religious = data.get("religious_preferences") or []
        return cls(
            user_id=user_id,
            dietary_preference=dietary,
            allergens=allergens or [],
            lifestyle=lifestyle or [],
            religious_preferences=religious or [],
        )
