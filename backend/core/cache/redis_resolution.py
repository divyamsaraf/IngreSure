"""
Optional Redis-backed cache for ingredient resolution.

Used only when REDIS_URL is set. On missing REDIS_URL or any Redis error,
calls return None / no-op so resolution falls back to in-memory + DB + ontology + APIs.
Does not change behavior or response quality.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from core.config import REDIS_URL

logger = logging.getLogger(__name__)

KEY_PREFIX = "ingresure:resolve:"
TTL_SECONDS = 86400  # 24 hours

_redis_client = None
_redis_available: Optional[bool] = None


def _get_client():
    """Return Redis client if REDIS_URL is set and connection works; else None."""
    global _redis_client, _redis_available
    if REDIS_URL == "":
        return None
    if _redis_available is False:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        _redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        _redis_client.ping()
        _redis_available = True
        logger.info("Redis resolution cache: connected (REDIS_URL set)")
        return _redis_client
    except Exception as e:
        logger.warning("Redis resolution cache: disabled (%s)", e)
        _redis_available = False
        return None


def resolution_cache_available() -> bool:
    """True if Redis is configured and reachable."""
    return _get_client() is not None


def _resolution_key(norm_key: str, try_api: bool) -> str:
    return f"{KEY_PREFIX}{norm_key}:{'1' if try_api else '0'}"


def _serialize_resolution(resolution) -> str:
    """Serialize CanonicalResolution to JSON string. Caller must pass resolution object."""
    from core.ontology.ingredient_schema import Ingredient
    from core.knowledge.lifecycle import KnowledgeState

    ing = resolution.ingredient
    payload = {
        "ingredient": ing.to_dict() if ing is not None else None,
        "knowledge": {
            "state": resolution.knowledge.state.value,
            "source": resolution.knowledge.source,
        },
        "confidence_band": resolution.confidence_band,
        "source_layer": resolution.source_layer,
    }
    return json.dumps(payload)


def _deserialize_resolution(data: str):
    """Deserialize JSON string to CanonicalResolution. Returns None on error."""
    from core.ontology.ingredient_schema import Ingredient
    from core.knowledge.lifecycle import KnowledgeMetadata, KnowledgeState
    from core.knowledge.canonicalizer import CanonicalResolution

    try:
        payload = json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    knowledge = payload.get("knowledge")
    if not knowledge or "state" not in knowledge or "source" not in knowledge:
        return None
    try:
        state = KnowledgeState(knowledge["state"])
    except (ValueError, TypeError):
        return None
    meta = KnowledgeMetadata(state=state, source=knowledge["source"])
    ing_data = payload.get("ingredient")
    if ing_data is not None:
        if not isinstance(ing_data, dict) or "id" not in ing_data or "canonical_name" not in ing_data:
            return None
        try:
            ing = Ingredient.from_dict(ing_data)
        except (KeyError, TypeError):
            return None
    else:
        ing = None
    confidence_band = payload.get("confidence_band")
    source_layer = payload.get("source_layer")
    if source_layer not in ("static", "dynamic", "api", "unknown"):
        return None
    return CanonicalResolution(
        ingredient=ing,
        knowledge=meta,
        confidence_band=confidence_band,
        source_layer=source_layer,
    )


def resolution_cache_get(norm_key: str, try_api: bool):
    """
    Get cached CanonicalResolution from Redis, if available.
    Returns resolution object or None (cache miss or Redis disabled/error).
    """
    client = _get_client()
    if client is None:
        return None
    key = _resolution_key(norm_key, try_api)
    try:
        data = client.get(key)
    except Exception as e:
        logger.debug("Redis resolution cache get error: %s", e)
        return None
    if data is None:
        return None
    resolution = _deserialize_resolution(data)
    if resolution is None:
        logger.debug("Redis resolution cache: invalid entry for key=%s, ignoring", norm_key[:50])
        try:
            client.delete(key)
        except Exception:
            pass
        return None
    return resolution


def resolution_cache_set(norm_key: str, try_api: bool, resolution) -> None:
    """
    Store CanonicalResolution in Redis with TTL, if available.
    No-op if Redis is disabled or on error.
    """
    client = _get_client()
    if client is None:
        return
    key = _resolution_key(norm_key, try_api)
    try:
        data = _serialize_resolution(resolution)
        client.setex(key, TTL_SECONDS, data)
    except Exception as e:
        logger.debug("Redis resolution cache set error: %s", e)
