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


_KNOWN_FIELDS = {
    "user_id",
    "dietary_preference",
    "allergens",
    "lifestyle",
    "unsupported_restrictions",
    "legacy_fields",
}

# restriction_id → canonical allergen label (legacy JSON / chat payloads).
_RESTRICTION_TO_ALLERGEN = {
    "peanut_allergy": "Peanuts",
    "tree_nut_allergy": "Tree Nuts",
    "milk_allergy": "Milk",
    "egg_allergy": "Eggs",
    "soy_allergy": "Soy",
    "wheat_allergy": "Wheat/Gluten",
    "fish_allergy": "Fish",
    "shellfish_allergy": "Shellfish",
    "sesame_allergy": "Sesame",
    "mustard_allergy": "Mustard",
    "celery_allergy": "Celery",
}


def _as_str_list(value) -> List[str]:
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v is not None and str(v).strip()]
    if value is None or value == "":
        return []
    return [str(value)]


def _choice_lookup(choices: List[str]) -> dict[str, str]:
    return {c.casefold(): c for c in choices}


@dataclass
class UserProfile:
    """
    Single persistent profile per user.
    dietary_preference: primary diet / religious diet (e.g. Jain, Halal, Vegan, No rules).
    allergens, lifestyle: lists.
    Unknown keys are kept and surfaced as unsupported_notices — never dropped.
    """
    user_id: str
    dietary_preference: str = "No rules"
    allergens: List[str] = field(default_factory=list)
    lifestyle: List[str] = field(default_factory=list)
    unsupported_restrictions: List[str] = field(default_factory=list)
    legacy_fields: dict = field(default_factory=dict)

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

    def unsupported_notices(self) -> List[str]:
        notices: List[str] = []
        diets = set(get_dietary_preference_choices())
        allergens = set(get_allergen_choices())
        lifestyle = set(get_lifestyle_choices())
        if self.dietary_preference and self.dietary_preference not in diets:
            notices.append(
                f"Unsupported restriction: dietary_preference={self.dietary_preference!r}"
            )
        for a in self.allergens:
            if a not in allergens:
                notices.append(f"Unsupported restriction: allergen={a!r}")
        for item in self.lifestyle:
            if item not in lifestyle:
                notices.append(f"Unsupported restriction: lifestyle={item!r}")
        for raw in self.unsupported_restrictions:
            notices.append(f"Unsupported restriction: {raw}")
        return notices

    def to_dict(self) -> dict:
        body = asdict(self)
        body["unsupported_notices"] = self.unsupported_notices()
        return body

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """Load from dict. Unknown / legacy keys become notices; nothing is dropped."""
        data = dict(data or {})
        user_id = str(data.get("user_id", ""))
        dietary = data.get("dietary_preference")
        if dietary is None:
            dietary = data.get("diet") or data.get("diet_type")
        if not isinstance(dietary, str):
            dietary = "No rules"
        else:
            dietary = dietary.strip() or "No rules"

        allergens = _as_str_list(data.get("allergens"))
        if not allergens:
            allergens = _as_str_list(data.get("allergies"))
        lifestyle = _as_str_list(data.get("lifestyle"))

        diet_lookup = _choice_lookup(get_dietary_preference_choices())
        allergen_lookup = _choice_lookup(get_allergen_choices())
        lifestyle_lookup = _choice_lookup(get_lifestyle_choices())
        unsupported: List[str] = list(data.get("unsupported_restrictions") or [])
        legacy_fields: dict = dict(data.get("legacy_fields") or {})

        extra_lists = []
        for key in ("restrictions", "restriction_ids"):
            if key in data:
                extra_lists.extend(_as_str_list(data.get(key)))
                legacy_fields.setdefault(key, data.get(key))
        for raw in extra_lists:
            mapped = _RESTRICTION_TO_ALLERGEN.get(raw.strip().lower().replace(" ", "_"), "")
            folded = raw.casefold()
            if mapped:
                if mapped not in allergens:
                    allergens.append(mapped)
            elif folded in diet_lookup:
                if dietary in ("No rules", ""):
                    dietary = diet_lookup[folded]
            elif folded in allergen_lookup:
                canon = allergen_lookup[folded]
                if canon not in allergens:
                    allergens.append(canon)
            elif folded in lifestyle_lookup:
                canon = lifestyle_lookup[folded]
                if canon not in lifestyle:
                    lifestyle.append(canon)
            else:
                unsupported.append(raw)

        for key, value in data.items():
            if key in _KNOWN_FIELDS:
                continue
            if key in ("diet", "diet_type", "allergies", "restrictions", "restriction_ids"):
                continue
            legacy_fields[key] = value
            unsupported.append(f"{key}={value!r}")

        return cls(
            user_id=user_id,
            dietary_preference=dietary,
            allergens=list(allergens),
            lifestyle=list(lifestyle),
            unsupported_restrictions=unsupported,
            legacy_fields=legacy_fields,
        )
