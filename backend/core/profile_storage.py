"""
Persistent user profile storage keyed by user_id.
- Backend: JSON file (data/profiles.json) for persistence across sessions.
- Fields: dietary_preference, allergens, religious_preferences, lifestyle (maps to task's
  dietary_restrictions, religious_preferences, lifestyle_flags, allergies).
- Merge-on-update: only provided fields are written; existing fields never reset to None.
- Optional: set USE_PROFILE_DB=supabase and configure Supabase to use DB table user_profiles.
"""
import json
import logging
from pathlib import Path
from typing import Any, Optional

from core.models.user_profile import UserProfile

logger = logging.getLogger(__name__)

# data/profiles.json under repo root (backend/core -> parent.parent = backend, parent.parent.parent = repo)
_PROFILES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "profiles.json"


def _load_all() -> dict:
    if not _PROFILES_PATH.exists():
        return {}
    try:
        with open(_PROFILES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load profiles: %s", e)
        return {}


def _save_all(data: dict) -> None:
    _PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_profile(user_id: str) -> Optional[UserProfile]:
    """Load profile by user_id. Returns None if not found."""
    data = _load_all()
    raw = data.get(user_id)
    if raw is None:
        return None
    return UserProfile.from_dict({"user_id": user_id, **raw})


def save_profile(profile: UserProfile) -> None:
    """Persist full profile. Overwrites only this user's record."""
    data = _load_all()
    data[profile.user_id] = {
        "dietary_preference": profile.dietary_preference,
        "allergens": list(profile.allergens),
        "lifestyle": list(profile.lifestyle),
        "religious_preferences": list(profile.religious_preferences),
    }
    _save_all(data)
    logger.info("PROFILE_SAVE user_id=%s dietary_preference=%s allergens=%s", profile.user_id, profile.dietary_preference, profile.allergens)


def update_profile_partial(user_id: str, **kwargs: Any) -> Optional[UserProfile]:
    """
    Load profile, update only provided fields (merge), save.
    Never sets existing fields to None. Returns updated profile or None if user_id not found and no create.
    """
    profile = get_profile(user_id)
    if profile is None:
        profile = UserProfile(user_id=user_id)
    # Only pass non-None kwargs so we don't overwrite with None
    updates = {k: v for k, v in kwargs.items() if v is not None and k in ("dietary_preference", "allergens", "lifestyle", "religious_preferences")}
    if not updates:
        return profile
    profile.update_merge(**updates)
    save_profile(profile)
    logger.info("PROFILE_UPDATE user_id=%s updated_fields=%s", user_id, list(updates.keys()))
    return profile


def get_or_create_profile(user_id: str) -> UserProfile:
    """Load profile or create empty one (not persisted until save_profile)."""
    p = get_profile(user_id)
    if p is not None:
        return p
    return UserProfile(user_id=user_id)
