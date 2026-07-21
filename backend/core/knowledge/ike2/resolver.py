"""IKE-2 three-tier ingredient resolution (design §9).

Strict order: ResolutionCache -> Tier 1 (bundled truth anchor) -> Tier 2
(local ontology file) -> Tier 3 (Supabase) -> Unknown queue.

After an exact-tier miss, apply the synonymy ladder (§9.3.1):
  L2 curated variant aliases (longest exact key)
  L3 allowlisted facet reduction (only if residual resolves)
before L5 unknown. No runtime fuzzy / LLM.
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


def _uncertain(layer: str, source: str, *, miss_class: str | None = None) -> ResolvedIngredient:
    """Fail-closed: anything we cannot pin down is uncertain, never safe."""
    return ResolvedIngredient(
        group=None,
        source=source,
        confidence_band="none",
        trusted=False,
        resolution_layer=layer,
        status="uncertain",
        miss_class=miss_class,
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


def _alternate_keys(norm: str) -> list[str]:
    """L2 alias + L3 facet candidates (deduped, norm excluded)."""
    from core.knowledge.ike2.commodity_head import (
        facet_reduction_candidates,
        simple_commodity_head,
    )
    from core.knowledge.ike2.variant_aliases import lookup_variant_alias

    out: list[str] = []
    seen: set[str] = {norm}

    def _add(k: str | None) -> None:
        if not k or k in seen:
            return
        seen.add(k)
        out.append(k)

    alias = lookup_variant_alias(norm)
    _add(alias)
    for cand in facet_reduction_candidates(norm):
        _add(cand)
        _add(lookup_variant_alias(cand))
    _add(simple_commodity_head(norm))
    if alias:
        for cand in facet_reduction_candidates(alias):
            _add(cand)
    return out


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

    out = _resolve_uncached(norm, region, atom=atom)
    if out.status != "resolved":
        candidates = list(_alternate_keys(norm))
        # Remap invariant: if static regional remap pointed at a missing English
        # key, still try the pre-regional form (e.g. bajra) before L5.
        bare = normalize_ingredient_key(atom, apply_regional=False) or ""
        if bare and bare != norm and bare not in candidates:
            candidates.append(bare)
            candidates.extend(_alternate_keys(bare))
        for alt_norm in candidates:
            alt_key = cache.cache_key(alt_norm, region)
            alt_cached = cache.get(alt_key)
            if alt_cached is not None and alt_cached.status == "resolved":
                cache.put(key, alt_cached)
                return alt_cached
            alt = _resolve_uncached(alt_norm, region, atom=atom)
            if alt.status == "resolved":
                cache.put(alt_key, alt)
                cache.put(key, alt)
                return alt

    if out.status == "resolved":
        cache.put(key, out)
        return out

    # L5 — tag miss class for offline promote prioritization (never changes verdict).
    from core.knowledge.ike2.miss_class import classify_miss_class

    tagged = _uncertain(
        out.resolution_layer,
        out.source,
        miss_class=classify_miss_class(atom),
    )
    return tagged


def _resolve_uncached(norm: str, region: Optional[str], *, atom: str) -> ResolvedIngredient:
    """One-shot tier walk without reading/writing the caller's cache key."""
    # Tier 1 -- bundled core anchor; overrides everything else, zero network.
    fact = truth_anchor.lookup(norm)
    if fact is not None:
        return ResolvedIngredient(
            group=fact,
            source="truth_anchor",
            confidence_band="exact",
            trusted=is_trusted_for_compliance(fact, "static", "high"),
            resolution_layer="L1_truth_anchor",
            status="resolved",
        )

    # Tier 2 -- local ontology file; lazy write-through, zero network.
    local_fact = local_ontology.lookup(norm)
    if local_fact is not None:
        return ResolvedIngredient(
            group=local_fact,
            source="local_ontology",
            confidence_band="high",
            trusted=is_trusted_for_compliance(local_fact, "static", "high"),
            resolution_layer="L2_local_ontology",
            status="resolved",
        )

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
        return ResolvedIngredient(
            group=group,
            source="db",
            confidence_band="high",
            trusted=is_trusted_for_compliance(group, "db", "high"),
            resolution_layer="L3_db_alias",
            status="resolved",
        )

    # L5 -- unknown: enqueue for later enrichment and stay uncertain (fail-closed).
    return _uncertain("L5_unknown_queue", "unknown_queue")
