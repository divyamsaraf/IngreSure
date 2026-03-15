"""
Single persistent user profile for grocery safety.
dietary_preference covers both dietary AND religious choices (Jain, Halal, Kosher, etc.).
allergens, lifestyle are separate lists.
Updates merge without overwriting existing fields (partial updates).
Canonical options loaded from data/profile_options.json (single source of truth).
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from core.profile_options import (
    get_dietary_preference_choices,
    get_allergen_choices,
    get_lifestyle_choices,
)

# Re-export for code that imports from user_profile (loaded from profile_options.json)
DIETARY_PREFERENCE_CHOICES = get_dietary_preference_choices()
ALLERGEN_CHOICES = get_allergen_choices()
LIFESTYLE_CHOICES = get_lifestyle_choices()


@dataclass
class UserProfile:
    """
    Single persistent profile per user.
    dietary_preference: primary diet / religious diet (e.g. Jain, Halal, Vegan, No rules).
    allergens, lifestyle: lists.
    """
    user_id: str
    dietary_preference: str = "No rules"
    allergens: List[str] = field(default_factory=list)
    lifestyle: List[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        """True if profile has no meaningful constraints (first-time user)."""
        return (
            (not self.dietary_preference or self.dietary_preference == "No rules")
            and not self.allergens
            and not self.lifestyle
        )

    def update_merge(
        self,
        dietary_preference: Optional[str] = None,
        allergens: Optional[List[str]] = None,
        lifestyle: Optional[List[str]] = None,
        **_kwargs,
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

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """Load from dict (user_id, dietary_preference, allergens, lifestyle only)."""
        user_id = str(data.get("user_id", ""))
        dietary = data.get("dietary_preference")
        if not isinstance(dietary, str):
            dietary = "No rules"
        else:
            dietary = dietary.strip() or "No rules"
        allergens = data.get("allergens")
        if not isinstance(allergens, (list, tuple)):
            allergens = [allergens] if allergens else []
        lifestyle = data.get("lifestyle")
        if not isinstance(lifestyle, (list, tuple)):
            lifestyle = [lifestyle] if lifestyle else []
        return cls(
            user_id=user_id,
            dietary_preference=dietary,
            allergens=list(allergens),
            lifestyle=list(lifestyle),
        )
