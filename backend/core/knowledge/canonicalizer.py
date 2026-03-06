"""
Canonical ingredient resolution scaffolding.

Phase 1 goal:
    - Provide a single abstraction for resolving raw ingredient strings
      into canonical Ingredient objects, without changing existing behavior.
    - Internally delegate to the current IngredientRegistry implementation
      (static ontology + dynamic ontology + external enrichment).

Future phases will:
    - Introduce PostgreSQL-backed ingredient groups and aliases.
    - Add multi-layer caching (process, Redis, DB).
    - Enforce canonical identity semantics (many aliases -> one group).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from core.ontology.ingredient_schema import Ingredient
from core.ontology.ingredient_registry import IngredientRegistry
from core.knowledge.lifecycle import KnowledgeMetadata, KnowledgeState, ResolutionLevel
from core.knowledge.ingredient_db import IngredientKnowledgeDB
from core.normalization.normalizer import normalize_ingredient_key
from core.config import USE_KNOWLEDGE_DB


@dataclass(frozen=True)
class CanonicalResolution:
    """
    Result of resolving a raw ingredient string.

    In Phase 1 this is a thin wrapper around the existing resolution output
    from IngredientRegistry. The shape is forward-compatible with the
    future group-based implementation.
    """

    ingredient: Optional[Ingredient]
    knowledge: KnowledgeMetadata
    # Raw confidence band returned from the underlying registry when using
    # resolve_with_fallback: "high" | "medium" | "low". For static-only
    # resolution we treat resolved entries as "high" by default.
    confidence_band: Optional[ResolutionLevel]
    # Where this was ultimately found in the current system.
    # "static" | "dynamic" | "api" for now; later will include "database", "redis_cache", etc.
    source_layer: Literal["static", "dynamic", "api", "unknown"]

    def to_resolution_level(self) -> ResolutionLevel:
        return self.knowledge.to_resolution_level()


class CanonicalResolver:
    """
    Single entry point for resolving ingredient strings.

    Phase 1:
        - Wraps IngredientRegistry.resolve/resolve_with_fallback.
        - Preserves exact semantics and confidence behavior.

    Later phases will replace the internals with:
        - alias/group lookup in PostgreSQL
        - cache hierarchy
        - explicit lifecycle transitions
    while keeping this public interface stable so that the compliance
    engine and bridge code do not need to change.
    """

    def __init__(self, registry: Optional[IngredientRegistry] = None) -> None:
        self._registry = registry or IngredientRegistry()
        # Optional knowledge DB; used only when USE_KNOWLEDGE_DB is enabled.
        self._db = IngredientKnowledgeDB() if USE_KNOWLEDGE_DB else None

    def _resolve_via_db(self, raw: str) -> Optional[CanonicalResolution]:
        """
        Optional DB-backed resolution path.

        Currently:
          - Only used when USE_KNOWLEDGE_DB is true and DB is configured.
          - Falls back silently to the legacy registry-based path on any miss.
        """
        if not self._db or not self._db.enabled:
            return None
        norm = normalize_ingredient_key(raw)
        if not norm:
            return None
        group_row = self._db.resolve_group_by_alias(norm)
        if not group_row:
            return None

        # Map group_row to an Ingredient dataclass. We treat the group itself
        # as the canonical Ingredient identity here.
        ing = Ingredient(
            id=str(group_row.get("id")),
            canonical_name=group_row.get("canonical_name") or raw,
            aliases=[],
            derived_from=group_row.get("derived_from") or [],
            contains=group_row.get("contains") or [],
            may_contain=group_row.get("may_contain") or [],
            animal_origin=bool(group_row.get("animal_origin", False)),
            plant_origin=bool(group_row.get("plant_origin", False)),
            synthetic=bool(group_row.get("synthetic", False)),
            fungal=bool(group_row.get("fungal", False)),
            insect_derived=bool(group_row.get("insect_derived", False)),
            animal_species=group_row.get("animal_species"),
            egg_source=bool(group_row.get("egg_source", False)),
            dairy_source=bool(group_row.get("dairy_source", False)),
            gluten_source=bool(group_row.get("gluten_source", False)),
            nut_source=group_row.get("nut_source"),
            soy_source=bool(group_row.get("soy_source", False)),
            sesame_source=bool(group_row.get("sesame_source", False)),
            alcohol_content=group_row.get("alcohol_content"),
            root_vegetable=bool(group_row.get("root_vegetable", False)),
            onion_source=bool(group_row.get("onion_source", False)),
            garlic_source=bool(group_row.get("garlic_source", False)),
            fermented=bool(group_row.get("fermented", False)),
            uncertainty_flags=group_row.get("uncertainty_flags") or [],
            regions=group_row.get("regions") or [],
        )

        state_str = group_row.get("knowledge_state") or "UNKNOWN"
        try:
            state = KnowledgeState(state_str)
        except ValueError:
            state = KnowledgeState.UNKNOWN

        meta = KnowledgeMetadata(state=state, source="knowledge_db")
        return CanonicalResolution(
            ingredient=ing,
            knowledge=meta,
            confidence_band="high",
            source_layer="dynamic",
        )

    def resolve_static(self, raw: str) -> CanonicalResolution:
        """
        Static-only resolution (no external APIs, no logging side-effects).
        Mirrors IngredientRegistry.resolve.
        """
        ing = self._registry.resolve(raw)
        if ing is None:
            meta = KnowledgeMetadata(
                state=KnowledgeState.UNKNOWN,
                source="static_ontology",
            )
            return CanonicalResolution(
                ingredient=None,
                knowledge=meta,
                confidence_band=None,
                source_layer="unknown",
            )

        # Static ontology is curated and treated as fully trusted.
        meta = KnowledgeMetadata(
            state=KnowledgeState.LOCKED,
            source="static_ontology",
        )
        return CanonicalResolution(
            ingredient=ing,
            knowledge=meta,
            confidence_band="high",
            source_layer="static",
        )

    def resolve_with_fallback(
        self,
        raw: str,
        try_api: bool = True,
        log_unknown: bool = True,
        restriction_ids: Optional[list] = None,
        profile_context: Optional[dict] = None,
    ) -> CanonicalResolution:
        """
        Full resolution pipeline: static -> dynamic -> external APIs.

        This is a direct wrapper over IngredientRegistry.resolve_with_fallback
        so that behavior and confidence characteristics remain identical
        to the existing implementation.
        """
        # Optional DB-first resolution when enabled.
        db_res = self._resolve_via_db(raw)
        if db_res is not None:
            return db_res

        if not hasattr(self._registry, "resolve_with_fallback"):
            # Fallback to static-only behavior if the registry does not
            # support external enrichment (e.g. in tests).
            return self.resolve_static(raw)

        ing, source, level = self._registry.resolve_with_fallback(
            raw,
            try_api=try_api,
            log_unknown=log_unknown,
            restriction_ids=restriction_ids,
            profile_context=profile_context,
        )

        if ing is None:
            meta = KnowledgeMetadata(
                state=KnowledgeState.UNKNOWN,
                source="static_ontology" if source == "static" else "external_api",
            )
            return CanonicalResolution(
                ingredient=None,
                knowledge=meta,
                confidence_band=level,
                source_layer="unknown" if source == "static" else "api",
            )

        # Map existing confidence bands to lifecycle states. For now this is
        # a heuristic mapping that does NOT alter the numerical confidence
        # calculations in the compliance engine.
        if source == "static":
            state = KnowledgeState.LOCKED
            meta_source = "static_ontology"
        elif source == "dynamic":
            # Dynamic ontology entries are high-confidence API results that
            # have been materialized; treat them as VERIFIED by default.
            state = KnowledgeState.VERIFIED if level == "high" else KnowledgeState.DISCOVERED
            meta_source = "dynamic_ontology"
        else:  # source == "api"
            if level == "high":
                state = KnowledgeState.AUTO_CLASSIFIED
            elif level == "medium":
                state = KnowledgeState.DISCOVERED
            else:
                state = KnowledgeState.UNKNOWN
            meta_source = "external_api"

        meta = KnowledgeMetadata(
            state=state,
            source=meta_source,
        )
        return CanonicalResolution(
            ingredient=ing,
            knowledge=meta,
            confidence_band=level,
            source_layer=source,
        )

