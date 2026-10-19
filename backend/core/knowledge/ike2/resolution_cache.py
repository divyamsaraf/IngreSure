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

# Higher knowledge_state replaces an earlier lower-trust row on the same
# normalized key. Equal rank keeps the first writer.
_KS_RANK = {
    "LOCKED": 5,
    "VERIFIED": 4,
    "CLASSIFIED": 3,
    "AUTO_CLASSIFIED": 2,
    "DISCOVERED": 1,
    "UNCLASSIFIED": 0,
    "UNKNOWN": 0,
}


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


def _rank(fact) -> int:
    return _KS_RANK.get(getattr(fact, "knowledge_state", "") or "", 0)


def _keep_lower_trust_caution(winner, loser):
    """Higher-trust row wins identity and positive flags. Catalog uncertainty
    and a WARN cap the winner does not already have stay on the cached fact.
    """
    loser_flags = getattr(loser, "flags", None) or {}
    winner_flags = dict(getattr(winner, "flags", None) or {})
    merged = list(winner_flags.get("uncertainty_flags") or [])
    for flag in loser_flags.get("uncertainty_flags") or []:
        if flag not in merged:
            merged.append(flag)
    if merged:
        winner_flags["uncertainty_flags"] = merged
    if not winner_flags.get("verdict_cap") and loser_flags.get("verdict_cap"):
        winner_flags["verdict_cap"] = loser_flags["verdict_cap"]
    if winner_flags == (getattr(winner, "flags", None) or {}):
        return winner
    from core.knowledge.ike2.truth_anchor import TruthAnchorFact

    return TruthAnchorFact(
        canonical_name=winner.canonical_name,
        flags=winner_flags,
        knowledge_state=winner.knowledge_state,
    )


def _prefer_fact(current, incoming):
    if current is None:
        return incoming
    if _rank(incoming) > _rank(current):
        return _keep_lower_trust_caution(incoming, current)
    if _rank(current) > _rank(incoming):
        return _keep_lower_trust_caution(current, incoming)
    return current


def seed_tier1() -> None:
    """Boot-seed: load every Tier-1 curated anchor into the cache, zero network
    (design §9.5). Idempotent; safe to call on every ``resolve()``.

    When two aliases normalize to one key, the higher ``knowledge_state`` wins.
    Uncertainty flags and a missing ``verdict_cap`` from the lower-trust row
    are kept, so a catalog caution is not dropped just because the hand anchor
    omitted it.
    """
    global _SEEDED
    if _SEEDED:
        return
    _SEEDED = True

    from core.evaluation.resolution_trust import is_trusted_for_compliance
    from core.knowledge.ike2 import truth_anchor

    chosen: dict[str, object] = {}
    for alias, fact in truth_anchor.all_anchors().items():
        key = cache_key(alias, None)
        chosen[key] = _prefer_fact(chosen.get(key), fact)

    for key, fact in chosen.items():
        _CACHE[key] = ResolvedIngredient(
            group=fact,
            source="truth_anchor",
            confidence_band="exact",
            trusted=is_trusted_for_compliance(fact, "static", "high"),
            resolution_layer="L1_truth_anchor",
            status="resolved",
        )
