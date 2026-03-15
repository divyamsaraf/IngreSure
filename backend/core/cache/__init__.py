"""
Optional cache layer. Redis resolution cache is used only when REDIS_URL is set.
"""
from core.cache.redis_resolution import (
    resolution_cache_get,
    resolution_cache_set,
    resolution_cache_available,
)

__all__ = [
    "resolution_cache_get",
    "resolution_cache_set",
    "resolution_cache_available",
]
