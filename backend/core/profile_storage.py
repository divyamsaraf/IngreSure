"""
Persistent user profile storage keyed by user_id (optionally namespaced by org_id).

Backends:
  - JSON file (``data/profiles.json``) — default.
  - Supabase ``public.users`` when ``USE_PROFILE_DB`` is truthy (1/true/yes/supabase).

``public.users`` columns used: ``id``, ``allergies``, ``diet_type``, ``preferences``.
Mapping: dietary_preference↔diet_type, allergens↔allergies, lifestyle↔preferences.lifestyle.

Constraints of the existing table:
  - ``id`` is uuid PK referencing ``auth.users``, so only UUID ``user_id`` values can
    use the DB path. Non-UUID ids (anon chat, e2e) stay on the JSON file.
  - Org-namespaced profiles (``org_id`` set) stay on JSON — ``users`` has no org column.

Callers (``app.py`` GET/POST /profile) keep the same ``UserProfile`` contract.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from core.models.user_profile import UserProfile
from core.config import redact_pii

logger = logging.getLogger(__name__)

_PROFILES_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "profiles.json"

_PROFILE_CACHE_MAX = 500
_profile_cache: dict[tuple[str, str], UserProfile] = {}
_profile_cache_lock = threading.Lock()


def use_profile_db() -> bool:
    raw = (os.environ.get("USE_PROFILE_DB") or "").strip().lower()
    return raw in ("1", "true", "yes", "supabase", "db")


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False


def _storage_key(user_id: str, org_id: Optional[str] = None) -> str:
    if org_id:
        return f"org:{org_id}:user:{user_id}"
    return f"user:{user_id}"


def _cache_key(storage_key: str) -> tuple[str, str]:
    return (str(_PROFILES_PATH), storage_key)


def _use_db_for(user_id: str, org_id: Optional[str]) -> bool:
    return use_profile_db() and not org_id and _is_uuid(user_id)


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


def _evict_oldest_cached() -> None:
    if not _profile_cache:
        return
    oldest = next(iter(_profile_cache))
    del _profile_cache[oldest]


def _db_client():
    from core.knowledge.ingredient_db import get_supabase_config
    from supabase import create_client

    cfg = get_supabase_config()
    if not cfg:
        return None
    return create_client(cfg.url, cfg.key)


def _row_to_profile(user_id: str, row: dict) -> UserProfile:
    prefs = row.get("preferences") or {}
    if not isinstance(prefs, dict):
        prefs = {}
    lifestyle = prefs.get("lifestyle") or []
    if not isinstance(lifestyle, (list, tuple)):
        lifestyle = []
    allergies = row.get("allergies") or []
    if not isinstance(allergies, (list, tuple)):
        allergies = []
    diet = row.get("diet_type") or "No rules"
    if not isinstance(diet, str) or not diet.strip():
        diet = "No rules"
    return UserProfile(
        user_id=user_id,
        dietary_preference=diet.strip(),
        allergens=list(allergies),
        lifestyle=list(lifestyle),
    )


def _profile_to_row(profile: UserProfile) -> dict:
    return {
        "id": profile.user_id,
        "diet_type": profile.dietary_preference or "No rules",
        "allergies": list(profile.allergens or []),
        "preferences": {"lifestyle": list(profile.lifestyle or [])},
    }


def _db_get(user_id: str) -> Optional[UserProfile]:
    client = _db_client()
    if not client:
        logger.warning("USE_PROFILE_DB set but Supabase not configured")
        return None
    try:
        resp = (
            client.table("users")
            .select("id,diet_type,allergies,preferences")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if not resp.data:
            return None
        return _row_to_profile(user_id, resp.data[0])
    except Exception as e:
        logger.warning("DB get_profile failed user_id=%s: %s", redact_pii(user_id), e)
        return None


def _db_save(profile: UserProfile) -> bool:
    client = _db_client()
    if not client:
        logger.warning("USE_PROFILE_DB set but Supabase not configured; not saving")
        return False
    row = _profile_to_row(profile)
    try:
        # Prefer update-then-insert so we don't invent auth.users rows.
        existing = (
            client.table("users")
            .select("id,preferences")
            .eq("id", profile.user_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            prev_prefs = existing.data[0].get("preferences") or {}
            if not isinstance(prev_prefs, dict):
                prev_prefs = {}
            merged_prefs = dict(prev_prefs)
            merged_prefs["lifestyle"] = list(profile.lifestyle or [])
            client.table("users").update(
                {
                    "diet_type": row["diet_type"],
                    "allergies": row["allergies"],
                    "preferences": merged_prefs,
                }
            ).eq("id", profile.user_id).execute()
        else:
            client.table("users").insert(row).execute()
        return True
    except Exception as e:
        logger.warning("DB save_profile failed user_id=%s: %s", redact_pii(profile.user_id), e)
        return False


def get_profile(user_id: str, org_id: Optional[str] = None) -> Optional[UserProfile]:
    """
    Load profile by user_id (optionally within org_id's namespace). Returns None if not found.
    Uses in-memory cache when available. When org_id is None, falls back to the legacy
    bare user_id key if the namespaced `user:{user_id}` key isn't found (migrate-compatible).
    """
    storage_key = _storage_key(user_id, org_id)
    key = _cache_key(storage_key)
    with _profile_cache_lock:
        if key in _profile_cache:
            return _profile_cache[key]

    if _use_db_for(user_id, org_id):
        profile = _db_get(user_id)
        if profile is not None:
            with _profile_cache_lock:
                _profile_cache[key] = profile
                if len(_profile_cache) > _PROFILE_CACHE_MAX:
                    _evict_oldest_cached()
            return profile
        return None

    try:
        data = _load_all()
        raw = data.get(storage_key)
        if raw is None and not org_id:
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


def save_profile(profile: UserProfile, org_id: Optional[str] = None) -> None:
    """Persist full profile (optionally within org_id's namespace). Updates read cache."""
    storage_key = _storage_key(profile.user_id, org_id)

    if _use_db_for(profile.user_id, org_id):
        ok = _db_save(profile)
        if not ok:
            # Fall back to JSON so a FK miss doesn't silently drop profile edits.
            data = _load_all()
            data[storage_key] = {
                "dietary_preference": profile.dietary_preference,
                "allergens": list(profile.allergens),
                "lifestyle": list(profile.lifestyle),
            }
            _save_all(data)
            logger.warning(
                "PROFILE_SAVE_DB_FALLBACK_JSON user_id=%s (users row missing or auth FK)",
                redact_pii(profile.user_id),
            )
    else:
        data = _load_all()
        data[storage_key] = {
            "dietary_preference": profile.dietary_preference,
            "allergens": list(profile.allergens),
            "lifestyle": list(profile.lifestyle),
        }
        _save_all(data)

    with _profile_cache_lock:
        _profile_cache[_cache_key(storage_key)] = profile
        if len(_profile_cache) > _PROFILE_CACHE_MAX:
            _evict_oldest_cached()
    logger.info(
        "PROFILE_SAVE user_id=%s dietary_preference=%s allergens=%s db=%s",
        redact_pii(profile.user_id),
        redact_pii(profile.dietary_preference),
        redact_pii(profile.allergens),
        _use_db_for(profile.user_id, org_id),
    )


def update_profile_partial(
    user_id: str, org_id: Optional[str] = None, **kwargs: Any
) -> Optional[UserProfile]:
    """
    Load profile (optionally within org_id's namespace), update only provided fields (merge), save.
    Never sets existing fields to None. Returns updated profile or None if user_id not found and no create.
    """
    profile = get_profile(user_id, org_id=org_id)
    if profile is None:
        profile = UserProfile(user_id=user_id)
    updates = {
        k: v
        for k, v in kwargs.items()
        if v is not None and k in ("dietary_preference", "allergens", "lifestyle")
    }
    if not updates:
        return profile
    profile.update_merge(**updates)
    save_profile(profile, org_id=org_id)
    logger.info(
        "PROFILE_UPDATE user_id=%s updated_fields=%s",
        redact_pii(user_id),
        list(updates.keys()),
    )
    return profile


def get_or_create_profile(user_id: str, org_id: Optional[str] = None) -> UserProfile:
    """Load profile (optionally within org_id's namespace) or create empty one (not persisted until save_profile)."""
    p = get_profile(user_id, org_id=org_id)
    if p is not None:
        return p
    return UserProfile(user_id=user_id)


def migrate_profiles_json_to_db(path: Optional[Path] = None) -> dict[str, Any]:
    """One-shot: copy UUID-keyed profiles from profiles.json into ``public.users``.

    Skips org-namespaced keys and non-UUID ids. Rows that fail (e.g. missing
    ``auth.users`` FK) are reported, not deleted from JSON.
    """
    src = path or _PROFILES_PATH
    summary: dict[str, Any] = {
        "attempted": 0,
        "migrated": 0,
        "skipped_non_uuid": 0,
        "skipped_org": 0,
        "failed": [],
        "source": str(src),
    }
    if not use_profile_db():
        summary["error"] = "USE_PROFILE_DB not enabled"
        return summary
    if not src.exists():
        summary["error"] = "profiles.json missing"
        return summary
    data = json.loads(src.read_text(encoding="utf-8"))
    for key, raw in data.items():
        if key.startswith("org:"):
            summary["skipped_org"] += 1
            continue
        user_id = key.split("user:")[-1] if key.startswith("user:") else key
        if not _is_uuid(user_id):
            summary["skipped_non_uuid"] += 1
            continue
        summary["attempted"] += 1
        profile = UserProfile.from_dict({"user_id": user_id, **(raw or {})})
        if _db_save(profile):
            summary["migrated"] += 1
        else:
            summary["failed"].append(user_id)
    return summary
