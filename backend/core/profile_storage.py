"""
Persistent user profile storage keyed by user_id.
- Backend: JSON file (data/profiles.json) for persistence across sessions.
- Fields: dietary_preference, allergens, lifestyle.
  dietary_preference covers both dietary AND religious choices.
- Merge-on-update: only provided fields are written; existing fields never reset to None.
- In-memory read cache (size-bound, thread-safe) to avoid file read on every request.
- Optional DB backend (USE_PROFILE_DB): see docs/use-profile-db.md for what/how/why; not implemented yet.
"""
import json
import logging
import threading
from pathlib import Path
from typing import Any, Optional

from core.models.user_profile import UserProfile
from core.config import redact_pii

logger = logging.getLogger(__name__)

# data/profiles.json under repo root (backend/core -> parent.parent = backend, parent.parent.parent = repo)
_PROFILES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "profiles.json"

# In-memory profile cache ((path_key, user_id) -> UserProfile) so patching _PROFILES_PATH in tests gets fresh reads.
_PROFILE_CACHE_MAX = 500
_profile_cache: dict[tuple[str, str], UserProfile] = {}
_profile_cache_lock = threading.Lock()


def _cache_key(user_id: str) -> tuple[str, str]:
    return (str(_PROFILES_PATH), user_id)


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
    """Load profile by user_id. Returns None if not found. Uses in-memory cache when available."""
    key = _cache_key(user_id)
    with _profile_cache_lock:
        if key in _profile_cache:
            return _profile_cache[key]
    try:
        data = _load_all()
        raw = data.get(user_id)
        if raw is None:
            return None
        profile = UserProfile.from_dict({"user_id": user_id, **raw})
        with _profile_cache_lock:
            _profile_cache[key] = profile
            if len(_profile_cache) > _PROFILE_CACHE_MAX:
                _evict_oldest_cached()
        return profile
    except Exception as e:
        logger.warning("Failed to load profile for user_id=%s: %s", user_id, e)
        return None


def _evict_oldest_cached() -> None:
    """Remove one oldest entry from _profile_cache. Caller must hold _profile_cache_lock."""
    if not _profile_cache:
        return
    oldest = next(iter(_profile_cache))
    del _profile_cache[oldest]


def save_profile(profile: UserProfile) -> None:
    """Persist full profile. Overwrites only this user's record. Updates read cache."""
    data = _load_all()
    data[profile.user_id] = {
        "dietary_preference": profile.dietary_preference,
        "allergens": list(profile.allergens),
        "lifestyle": list(profile.lifestyle),
    }
    _save_all(data)
    with _profile_cache_lock:
        _profile_cache[_cache_key(profile.user_id)] = profile
        if len(_profile_cache) > _PROFILE_CACHE_MAX:
            _evict_oldest_cached()
    logger.info("PROFILE_SAVE user_id=%s dietary_preference=%s allergens=%s", redact_pii(profile.user_id), redact_pii(profile.dietary_preference), redact_pii(profile.allergens))


def update_profile_partial(user_id: str, **kwargs: Any) -> Optional[UserProfile]:
    """
    Load profile, update only provided fields (merge), save.
    Never sets existing fields to None. Returns updated profile or None if user_id not found and no create.
    """
    profile = get_profile(user_id)
    if profile is None:
        profile = UserProfile(user_id=user_id)
    # Only pass non-None kwargs so we don't overwrite with None
    updates = {k: v for k, v in kwargs.items() if v is not None and k in ("dietary_preference", "allergens", "lifestyle")}
    if not updates:
        return profile
    profile.update_merge(**updates)
    save_profile(profile)
    logger.info("PROFILE_UPDATE user_id=%s updated_fields=%s", redact_pii(user_id), list(updates.keys()))
    return profile


def get_or_create_profile(user_id: str) -> UserProfile:
    """Load profile or create empty one (not persisted until save_profile)."""
    p = get_profile(user_id)
    if p is not None:
        return p
    return UserProfile(user_id=user_id)
