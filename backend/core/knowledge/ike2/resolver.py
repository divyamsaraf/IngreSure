"""IKE-2 three-tier ingredient resolution (design §9).

Strict order: ResolutionCache -> Tier 1 (bundled truth anchor) -> Tier 2
(local ontology file) -> Tier 3 (Supabase) -> Unknown queue.

Tier 3 is attempted only after a Tier 1 + Tier 2 miss, and any Tier-3 failure
(timeout, missing config, malformed row, unexpected exception) degrades
silently to a miss -- it must never raise into chat, and a Tier-1/2 hit is
always authoritative (Supabase is never consulted once one has fired).
"""
import logging
from typing import Optional

from core.evaluation.resolution_trust import is_trusted_for_compliance
from core.knowledge.ike2 import resolution_cache as cache
from core.knowledge.ike2 import truth_anchor
from core.knowledge.ike2.stores import db, local_ontology
from core.normalization.normalizer import normalize_ingredient_key

logger = logging.getLogger(__name__)

# Re-exported so existing call sites (``from core.knowledge.ike2.resolver
# import ResolvedIngredient``) keep working; the cache owns the definition
# because it must be able to construct instances while boot-seeding Tier 1.
ResolvedIngredient = cache.ResolvedIngredient


def _uncertain(layer: str, source: str) -> ResolvedIngredient:
    """Fail-closed: anything we cannot pin down is uncertain, never safe."""
    return ResolvedIngredient(
        group=None,
        source=source,
        confidence_band="none",
        trusted=False,
        resolution_layer=layer,
        status="uncertain",
    )


# A Tier-3 row missing its canonical name or its base origin flag can't
# safely drive a verdict: a silently-absent flag column reads back as
# ``None``/falsy, which would let a malformed row sail through compliance as
# a false SAFE. Same incomplete-flags policy as Tier 2 (design §9.4 note).
_REQUIRED_DB_FIELDS = ("canonical_name", "animal_origin")


def _is_well_formed_db_row(group) -> bool:
    if not getattr(group, "canonical_name", None):
        return False
    return all(hasattr(group, field) for field in _REQUIRED_DB_FIELDS)


def resolve(atom: str, region: Optional[str]) -> ResolvedIngredient:
    cache.seed_tier1()
    # Normalize once: chat lists often arrive Title-Cased ("Beets"), while
    # Tier-3 aliases are stored as normalized keys ("beets"). Passing the raw
    # atom into db.* made Title Case miss rows that lowercase would hit.
    norm = normalize_ingredient_key(atom) or (atom or "").strip()
    key = cache.cache_key(norm, region)

    cached = cache.get(key)
    if cached is not None:
        return cached

    # Tier 1 -- bundled core anchor; overrides everything else, zero network.
    fact = truth_anchor.lookup(norm)
    if fact is not None:
        out = ResolvedIngredient(
            group=fact,
            source="truth_anchor",
            confidence_band="exact",
            trusted=is_trusted_for_compliance(fact, "static", "high"),
            resolution_layer="L1_truth_anchor",
            status="resolved",
        )
        cache.put(key, out)
        return out

    # Tier 2 -- local ontology file; lazy write-through, zero network.
    local_fact = local_ontology.lookup(norm)
    if local_fact is not None:
        out = ResolvedIngredient(
            group=local_fact,
            source="local_ontology",
            confidence_band="high",
            trusted=is_trusted_for_compliance(local_fact, "static", "high"),
            resolution_layer="L2_local_ontology",
            status="resolved",
        )
        cache.put(key, out)
        return out

    # Tier 3 -- Supabase, only after Tier 1 + Tier 2 both missed. Any failure
    # (timeout, missing config, unexpected exception) degrades to a silent
    # miss and must never raise into chat (design §9.6).
    try:
        if db.disambiguate(norm, region) == "ambiguous":
            return _uncertain("L3_db_alias", "db")
        group = db.resolve_alias(norm, region)
    except Exception as exc:
        logger.warning("IKE2 Tier-3 resolution error for %r: %s", atom, exc)
        return _uncertain("L3_db_error", "db")

    if group is not None:
        if not _is_well_formed_db_row(group):
            logger.warning("IKE2 Tier-3 row malformed for %r", atom)
            return _uncertain("L3_db_malformed", "db")
        out = ResolvedIngredient(
            group=group,
            source="db",
            confidence_band="high",
            trusted=is_trusted_for_compliance(group, "db", "high"),
            resolution_layer="L3_db_alias",
            status="resolved",
        )
        cache.put(key, out)
        return out

    # L5 -- unknown: enqueue for later enrichment and stay uncertain (fail-closed).
    return _uncertain("L5_unknown_queue", "unknown_queue")
