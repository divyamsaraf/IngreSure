"""In-process resolution cache: boot-seeded Tier 1, lazy Tier-2/3 write-through
(design §9.5).

Locked seeding behavior:
- Boot: the entire Tier-1 curated core is loaded with zero network calls.
- First miss: resolver.py resolves against Tier 2 / Tier 3 and writes the hit
  through to this cache.
- Repeat lookup: served from here only. A key already satisfied by Tier 1 or
  Tier 2 must never re-enter Supabase.

Invalidation is process-restart only -- no TTL, no distributed cache (§9.5
invariant 4).
"""
from dataclasses import dataclass
from typing import Literal, Optional

from core.normalization.normalizer import normalize_ingredient_key

Status = Literal["resolved", "uncertain"]


@dataclass
class ResolvedIngredient:
    group: object
    source: str
    confidence_band: str
    trusted: bool
    resolution_layer: str
    status: Status
    # L5 observability only (design §9.3.1); never affects verdict.
    miss_class: Optional[str] = None


_CACHE: dict[str, ResolvedIngredient] = {}
_SEEDED = False


def cache_key(atom: str, region: Optional[str]) -> str:
    key = normalize_ingredient_key(atom)
    return f"{key}::{region}" if region else key


def get(key: str) -> Optional[ResolvedIngredient]:
    return _CACHE.get(key)


def put(key: str, resolved: ResolvedIngredient) -> None:
    _CACHE[key] = resolved


def clear() -> None:
    """Test-only: drop all cached entries and force a reseed on next resolve()."""
    global _SEEDED
    _CACHE.clear()
    _SEEDED = False


def seed_tier1() -> None:
    """Boot-seed: load every Tier-1 curated anchor into the cache, zero network
    (design §9.5). Idempotent; safe to call on every ``resolve()``."""
    global _SEEDED
    if _SEEDED:
        return
    _SEEDED = True

    from core.evaluation.resolution_trust import is_trusted_for_compliance
    from core.knowledge.ike2 import truth_anchor

    for alias, fact in truth_anchor.all_anchors().items():
        key = cache_key(alias, None)
        _CACHE.setdefault(
            key,
            ResolvedIngredient(
                group=fact,
                source="truth_anchor",
                confidence_band="exact",
                trusted=is_trusted_for_compliance(fact, "static", "high"),
                resolution_layer="L1_truth_anchor",
                status="resolved",
            ),
        )
