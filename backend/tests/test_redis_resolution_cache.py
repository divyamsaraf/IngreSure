"""
Unit tests for optional Redis resolution cache.

Behavior: when REDIS_URL is unset or Redis is unavailable, resolution is unchanged
(in-memory + DB + static/dynamic/APIs). When Redis is available, get/set round-trip
and resolver uses Redis as L2 cache.
"""
import pytest


def test_resolution_cache_unavailable_when_no_redis_url(monkeypatch):
    """When REDIS_URL is not set, cache is unavailable and get/set are no-ops."""
    monkeypatch.setattr("core.cache.redis_resolution.REDIS_URL", "")
    monkeypatch.setattr("core.cache.redis_resolution._redis_client", None)
    monkeypatch.setattr("core.cache.redis_resolution._redis_available", None)

    from core.cache.redis_resolution import (
        resolution_cache_available,
        resolution_cache_get,
        resolution_cache_set,
    )

    assert resolution_cache_available() is False
    assert resolution_cache_get("milk", True) is None
    assert resolution_cache_get("milk", False) is None
    resolution_cache_set("milk", True, None)  # no-op, no raise


def test_resolver_unchanged_without_redis(monkeypatch):
    """CanonicalResolver works as before when Redis is disabled (no REDIS_URL)."""
    monkeypatch.setattr("core.cache.redis_resolution.REDIS_URL", "")
    monkeypatch.setattr("core.cache.redis_resolution._redis_client", None)
    monkeypatch.setattr("core.cache.redis_resolution._redis_available", None)

    from core.config import get_ontology_path
    from core.knowledge.canonicalizer import CanonicalResolver

    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")

    resolver = CanonicalResolver()
    res = resolver.resolve_with_fallback("milk", try_api=False, log_unknown=False)
    assert res.ingredient is not None
    assert res.ingredient.canonical_name.lower() == "milk"
    assert res.source_layer in ("static", "dynamic")


def test_redis_cache_round_trip_with_mock(monkeypatch):
    """With a mock Redis client, set then get returns the same resolution."""
    import redis
    from core.config import get_ontology_path
    from core.ontology.ingredient_registry import IngredientRegistry
    from core.knowledge.lifecycle import KnowledgeMetadata, KnowledgeState
    from core.knowledge.canonicalizer import CanonicalResolution

    if not get_ontology_path().exists():
        pytest.skip("ontology.json not found")

    store = {}

    class MockRedis:
        def ping(self):
            pass

        def get(self, key):
            return store.get(key)

        def setex(self, key, ttl, value):
            store[key] = value

    def mock_from_url(*args, **kwargs):
        return MockRedis()

    monkeypatch.setattr("core.cache.redis_resolution.REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setattr("core.cache.redis_resolution._redis_client", None)
    monkeypatch.setattr("core.cache.redis_resolution._redis_available", None)
    monkeypatch.setattr(redis, "from_url", mock_from_url)

    import core.cache.redis_resolution as mod
    mod._redis_client = None
    mod._redis_available = None

    from core.cache.redis_resolution import (
        resolution_cache_get,
        resolution_cache_set,
        resolution_cache_available,
    )

    assert resolution_cache_available() is True

    # Build a resolution like static milk
    reg = IngredientRegistry(load_dynamic=False)
    ing = reg.resolve("milk")
    assert ing is not None
    meta = KnowledgeMetadata(state=KnowledgeState.LOCKED, source="static_ontology")
    resolution = CanonicalResolution(
        ingredient=ing,
        knowledge=meta,
        confidence_band="high",
        source_layer="static",
    )

    resolution_cache_set("milk", True, resolution)
    got = resolution_cache_get("milk", True)
    assert got is not None
    assert got.ingredient is not None
    assert got.ingredient.canonical_name == resolution.ingredient.canonical_name
    assert got.source_layer == resolution.source_layer
    assert got.confidence_band == resolution.confidence_band
