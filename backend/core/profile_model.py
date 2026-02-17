"""
User profile model: dietary_preference, allergens, lifestyle.
dietary_preference covers both dietary AND religious choices (Jain, Halal, Kosher, etc.).
Persisted by user_id; used to build restriction_ids for ComplianceEngine.

Field mapping (frontend <-> backend):
  - dietary_preference <-> dietary_preference (primary diet: "Hindu Veg", "Vegan", "Halal", etc.)
  - allergens <-> allergens (list: ["milk", "peanut", ...])
  - lifestyle <-> lifestyle (list: ["no alcohol", "no onion", ...])

Legacy aliases (kept for backward compatibility):
  - dietary_restrictions -> read as dietary_preference fallback
  - lifestyle_flags -> read as lifestyle fallback
  - allergies -> read as allergens fallback
  - religious_preferences -> migrated into dietary_preference on read
"""
from typing import Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class UserProfile:
    user_id: str = ""
    dietary_preference: str = "No rules"
    allergens: List[str] = field(default_factory=list)
    lifestyle: List[str] = field(default_factory=list)

    def update_merge(self, **kwargs: Any) -> None:
        """
        Merge-update: only provided non-None fields are overwritten.
        Existing fields that are NOT in kwargs remain unchanged.
        """
        for key, value in kwargs.items():
            if value is None:
                continue
            if key == "dietary_preference":
                self.dietary_preference = str(value) if value else "No rules"
            elif key == "allergens":
                self.allergens = list(value) if value else []
            elif key in ("lifestyle", "lifestyle_flags"):
                self.lifestyle = list(value) if value else []
            elif key == "dietary_restrictions":
                # Legacy: treat first entry as dietary_preference if not already set
                if not self.dietary_preference or self.dietary_preference == "No rules":
                    vals = list(value) if value else []
                    if vals:
                        self.dietary_preference = vals[0]

    def is_empty(self) -> bool:
        """True when profile has no meaningful restrictions set."""
        return (
            (not self.dietary_preference or self.dietary_preference == "No rules")
            and not self.allergens
            and not self.lifestyle
        )

    def to_dict(self) -> dict:
        d = {
            "user_id": self.user_id,
            "dietary_preference": self.dietary_preference,
            "allergens": list(self.allergens),
            "lifestyle": list(self.lifestyle),
        }
        # Include religious_preferences=[] for backward compat with frontend
        d["religious_preferences"] = []
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        dietary_pref = (
            data.get("dietary_preference")
            or (data.get("dietary_restrictions") or ["No rules"])[0]
            if isinstance(data.get("dietary_restrictions"), list) and data.get("dietary_restrictions")
            else data.get("dietary_preference") or "No rules"
        )
        # Legacy migration: if religious_preferences had a value, use it as dietary_preference
        if (not dietary_pref or dietary_pref == "No rules") and data.get("religious_preferences"):
            rp = data["religious_preferences"]
            if isinstance(rp, list) and rp:
                dietary_pref = rp[0]
        lifestyle = (
            data.get("lifestyle")
            or data.get("lifestyle_flags")
            or []
        )
        allergens = (
            data.get("allergens")
            or data.get("allergies")
            or []
        )
        return cls(
            user_id=str(data.get("user_id", "")),
            dietary_preference=dietary_pref or "No rules",
            allergens=list(allergens),
            lifestyle=list(lifestyle),
        )
