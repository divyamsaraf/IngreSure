# backend/core/knowledge/ike2/decay.py
"""Temporal confidence decay policy (Item 4.1).

Scope
-----
Decay applies **only** to IKE-2 DB groups (``ike2_ingredient_groups``), i.e.
bulk-injected / DB-native knowledge that carries ``knowledge_state`` and
``trust_refreshed_at``.

**L2 / Coverage OS promotions are intentionally out of scope.** Coverage OS
writes ``ontology.json`` / ``variant_aliases.json`` only — it never touches
``ike2_ingredient_groups``. Those promotions are always human-approved at
commit time (``auto=False`` + ``reviewer_id``; see Item 4 / Item 5), so they
are not the \"unverified knowledge sitting around\" problem this module exists
to solve. Do not invent a parallel decay clock for L2 files.

``updated_at`` is **not** the decay clock (no reliable bump on reconcile).
Use ``trust_refreshed_at`` (migration ``20260918000000_ike2_trust_refreshed_at``).
"""
from __future__ import annotations

from typing import Final, Mapping, Optional

# Days since trust_refreshed_at before a one-step demotion is eligible.
# LOCKED never decays (enforced by next_decay_state).
TTL_VERIFIED_DAYS: Final[int] = 180
TTL_AUTO_CLASSIFIED_DAYS: Final[int] = 90

# Optional P2 (DISCOVERED → UNCLASSIFIED): kept as constant only until enabled.
TTL_DISCOVERED_DAYS: Final[int] = 365

DECAY_POLICY: Final[dict[str, int]] = {
    "VERIFIED": TTL_VERIFIED_DAYS,
    "AUTO_CLASSIFIED": TTL_AUTO_CLASSIFIED_DAYS,
}

# One-step demotions only (never skip ranks; never increase trust).
_NEXT_STATE: Final[dict[str, str]] = {
    "VERIFIED": "AUTO_CLASSIFIED",
    "AUTO_CLASSIFIED": "DISCOVERED",
}


def age_days_since(trust_refreshed_at, as_of) -> float:
    """Elapsed days from ``trust_refreshed_at`` to ``as_of`` (both aware or naive UTC)."""
    from datetime import datetime, timezone

    def _aware(dt):
        if isinstance(dt, str):
            raw = dt.replace("Z", "+00:00")
            dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    delta = _aware(as_of) - _aware(trust_refreshed_at)
    return delta.total_seconds() / 86400.0


def plan_decay_row(
    *,
    knowledge_state: str,
    trust_refreshed_at,
    as_of,
    policy: Mapping[str, int] | None = None,
) -> Optional[str]:
    """Return next state for one row at ``as_of``, or None if not eligible."""
    age = age_days_since(trust_refreshed_at, as_of)
    return next_decay_state(knowledge_state, age, policy=policy)


def next_decay_state(
    state: str,
    age_days: float,
    policy: Mapping[str, int] | None = None,
) -> Optional[str]:
    """Return the one-step demoted state if ``age_days`` exceeds the TTL, else None.

    - ``LOCKED`` / ``DEPRECATED`` / ``UNCLASSIFIED`` / unknown → never decay.
    - ``DISCOVERED`` → not demoted in v1 (TTL_DISCOVERED_DAYS reserved for P2).
    - Decay never increases rank.
    """
    pol = dict(policy) if policy is not None else dict(DECAY_POLICY)
    if state not in _NEXT_STATE:
        return None
    ttl = pol.get(state)
    if ttl is None:
        return None
    if age_days < 0:
        return None
    if age_days < ttl:
        return None
    return _NEXT_STATE[state]
