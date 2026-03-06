"""
Supabase/PostgreSQL knowledge DB access layer (scaffold).

Phase 3 goal:
  - Provide a typed, centralized access layer for canonical knowledge tables
    (ingredient_groups, ingredients, ingredient_aliases, unknown_ingredients).
  - Keep current runtime behavior unchanged until we explicitly switch the
    CanonicalResolver internals to use this DB.

This module is intentionally small and non-invasive for now.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List, Optional

from supabase import create_client, Client
from core.config import get_supabase_url
from core.external_apis.base import EnrichmentResult
from core.ontology.ingredient_schema import Ingredient

# Allowed values for ingredients.source (must match DB check constraint)
ALLOWED_INGREDIENT_SOURCES = (
    "ontology",
    "usda_fdc",
    "open_food_facts",
    "fao",
    "ifct",
    "indb",
    "pubchem",
    "chebi",
    "wikidata",
    "dbpedia",
    "foodb",
    "uniprot",
    "admin",
    "system",
)


def _origin_type_from_ingredient(ing: Ingredient) -> Optional[str]:
    """Derive origin_type for ingredient_groups from Ingredient flags."""
    if ing.animal_origin:
        return "animal"
    if ing.plant_origin:
        return "plant"
    if ing.synthetic:
        return "synthetic"
    if ing.fungal:
        return "fungal"
    if ing.insect_derived:
        return "insect"
    return "unknown"


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    key: str


def get_supabase_config() -> Optional[SupabaseConfig]:
    """
    Resolve Supabase credentials from environment.
    Uses Docker-safe URL (localhost/127.0.0.1 -> host.docker.internal) when RUNNING_IN_DOCKER=1.
    """
    url = get_supabase_url()
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_KEY")
        or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or ""
    ).strip()
    if not url or not key:
        return None
    return SupabaseConfig(url=url, key=key)


# One-time log when Supabase is unreachable so we don't spam per unknown ingredient
_supabase_unreachable_logged = False


class IngredientKnowledgeDB:
    """
    Minimal Supabase client wrapper.

    Future phases will add:
      - group/alias resolution queries
      - versioning helpers
      - unknown ingredient upserts
      - metrics updates
    """

    def __init__(self, client: Optional[Client] = None) -> None:
        global _supabase_unreachable_logged
        if client is not None:
            self._client = client
            return
        cfg = get_supabase_config()
        if not cfg:
            self._client = None
            return
        try:
            self._client = create_client(cfg.url, cfg.key)
        except OSError as e:
            # DNS (gaierror -2 "Name or service not known") or connection errors
            self._client = None
            if not _supabase_unreachable_logged:
                _supabase_unreachable_logged = True
                logging.getLogger(__name__).warning(
                    "IngredientKnowledgeDB: Supabase unreachable (url=%s): %s. "
                    "Set RUNNING_IN_DOCKER=1 and SUPABASE_URL to host (e.g. http://127.0.0.1:54321) "
                    "so URL is rewritten to host.docker.internal. Knowledge DB disabled for this process.",
                    cfg.url[:60], e,
                )
        except Exception as e:
            self._client = None
            if not _supabase_unreachable_logged:
                _supabase_unreachable_logged = True
                logging.getLogger(__name__).warning(
                    "IngredientKnowledgeDB: failed to create client: %s. Knowledge DB disabled.", e
                )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def ping(self) -> bool:
        """
        Lightweight connectivity check.
        Uses a trivial select on a system table if possible; otherwise returns False.
        """
        if not self._client:
            return False
        try:
            # A simple query against an always-present table can fail if RLS blocks,
            # but this is good enough as a health indicator for now.
            self._client.table("ingredient_groups").select("id").limit(1).execute()
            return True
        except Exception:
            return False

    def resolve_group_by_alias(self, normalized_alias: str) -> Optional[dict[str, Any]]:
        """
        Resolve a canonical group row by normalized alias.

        This performs three lightweight queries:
          alias -> ingredient_id -> group_id -> group row

        Callers are expected to enforce their own normalization convention
        for `normalized_alias`.
        """
        if not self._client or not normalized_alias:
            return None

        try:
            alias_resp = (
                self._client.table("ingredient_aliases")
                .select("ingredient_id")
                .eq("normalized_alias", normalized_alias)
                .limit(1)
                .execute()
            )
            if not alias_resp.data:
                return None
            ingredient_id = alias_resp.data[0]["ingredient_id"]

            ing_resp = (
                self._client.table("ingredients")
                .select("group_id")
                .eq("id", ingredient_id)
                .is_("superseded_by", None)
                .limit(1)
                .execute()
            )
            if not ing_resp.data:
                return None
            group_id = ing_resp.data[0]["group_id"]

            group_resp = (
                self._client.table("ingredient_groups")
                .select("*")
                .eq("id", group_id)
                .is_("superseded_by", None)
                .limit(1)
                .execute()
            )
            if not group_resp.data:
                return None
            return group_resp.data[0]
        except Exception:
            return None

    # --- Enrichment persistence (used by background worker) ---

    def upsert_from_enrichment(
        self,
        result: EnrichmentResult,
        normalized_key: str,
    ) -> Optional[str]:
        """
        Persist an EnrichmentResult into ingredient_groups/ingredients/aliases.

        Returns the group_id if successful, or None on failure.
        """
        if not self._client or not result.ingredient or not normalized_key:
            return None

        ing: Ingredient = result.ingredient
        client = self._client

        # Normalize list/optional fields for DB (avoid None for jsonb)
        def _list(v):
            return list(v) if v is not None else []

        # Map API source to allowed DB enum
        source = (result.source or "system").strip().lower()
        if source not in ALLOWED_INGREDIENT_SOURCES:
            source = "system"

        try:
            # 1) Upsert group by canonical_name (active only)
            canon_name = (ing.canonical_name or "").strip() or normalized_key
            group_sel = (
                client.table("ingredient_groups")
                .select("id")
                .eq("canonical_name", canon_name)
                .is_("superseded_by", None)
                .limit(1)
                .execute()
            )
            if group_sel.data:
                group_id = group_sel.data[0]["id"]
            else:
                origin_type = _origin_type_from_ingredient(ing)
                group_payload = {
                    "canonical_name": canon_name,
                    "origin_type": origin_type,
                    "animal_origin": ing.animal_origin,
                    "plant_origin": ing.plant_origin,
                    "synthetic": ing.synthetic,
                    "fungal": ing.fungal,
                    "insect_derived": ing.insect_derived,
                    "animal_species": ing.animal_species,
                    "egg_source": ing.egg_source,
                    "dairy_source": ing.dairy_source,
                    "gluten_source": ing.gluten_source,
                    "nut_source": ing.nut_source,
                    "soy_source": ing.soy_source,
                    "sesame_source": ing.sesame_source,
                    "alcohol_content": ing.alcohol_content,
                    "root_vegetable": ing.root_vegetable,
                    "onion_source": ing.onion_source,
                    "garlic_source": ing.garlic_source,
                    "fermented": ing.fermented,
                    "knowledge_state": "DISCOVERED" if result.confidence == "medium" else "AUTO_CLASSIFIED",
                    "version": 1,
                    "uncertainty_flags": _list(ing.uncertainty_flags),
                    "derived_from": _list(ing.derived_from),
                    "contains": _list(ing.contains),
                    "may_contain": _list(ing.may_contain),
                    "regions": _list(ing.regions),
                }
                ins_group = client.table("ingredient_groups").insert(group_payload).execute()
                group_id = ins_group.data[0]["id"]

            # 2) Upsert ingredient row for this enrichment
            norm_name = normalized_key
            ing_sel = (
                client.table("ingredients")
                .select("id")
                .eq("normalized_name", norm_name)
                .is_("superseded_by", None)
                .limit(1)
                .execute()
            )
            if ing_sel.data:
                ingredient_id = ing_sel.data[0]["id"]
            else:
                ing_payload = {
                    "name": canon_name,
                    "normalized_name": norm_name,
                    "group_id": group_id,
                    "source": source,
                    "confidence": result.confidence if result.confidence in ("high", "medium", "low") else "medium",
                    "version": 1,
                }
                ins_ing = client.table("ingredients").insert(ing_payload).execute()
                ingredient_id = ins_ing.data[0]["id"]

            # 3) Upsert alias mapping normalized_key -> ingredient_id
            alias_sel = (
                client.table("ingredient_aliases")
                .select("id")
                .eq("normalized_alias", norm_name)
                .limit(1)
                .execute()
            )
            if not alias_sel.data:
                alias_payload = {
                    "alias": canon_name,
                    "normalized_alias": norm_name,
                    "ingredient_id": ingredient_id,
                    "alias_type": "synonym",
                    "language": "en",
                }
                client.table("ingredient_aliases").insert(alias_payload).execute()

            return group_id
        except Exception as e:
            logging.getLogger(__name__).warning("upsert_from_enrichment failed key=%s: %s", normalized_key[:80], e)
            return None

    def upsert_unknown_ingredient(
        self,
        normalized_key: str,
        raw_input: str,
        restriction_ids: Optional[List[str]] = None,
        profile_context: Optional[dict] = None,
    ) -> bool:
        """
        Record an unknown ingredient for discovery (worker will enrich later).
        If row exists: increment frequency, append raw_input to raw_inputs, update last_seen.
        """
        if not self._client or not normalized_key:
            return False
        client = self._client
        try:
            resp = (
                client.table("unknown_ingredients")
                .select("id, raw_inputs, frequency, restriction_ids_sample, profile_context_sample")
                .eq("normalized_key", normalized_key)
                .limit(1)
                .execute()
            )
            now = datetime.now(timezone.utc).isoformat()
            if resp.data and len(resp.data) > 0:
                row = resp.data[0]
                raw_inputs = list(row.get("raw_inputs") or [])
                if raw_input and raw_input not in raw_inputs:
                    raw_inputs = (raw_inputs + [raw_input])[:20]
                freq = (row.get("frequency") or 0) + 1
                restr = row.get("restriction_ids_sample") or []
                if restriction_ids:
                    for r in restriction_ids[:5]:
                        if r not in restr:
                            restr.append(r)
                    restr = restr[:10]
                prof = row.get("profile_context_sample") or profile_context
                client.table("unknown_ingredients").update({
                    "raw_inputs": raw_inputs,
                    "frequency": freq,
                    "last_seen": now,
                    "restriction_ids_sample": restr,
                    "profile_context_sample": prof,
                }).eq("id", row["id"]).execute()
            else:
                raw_inputs = [raw_input] if raw_input else []
                restr = list(restriction_ids)[:10] if restriction_ids else []
                client.table("unknown_ingredients").insert({
                    "normalized_key": normalized_key,
                    "raw_inputs": raw_inputs,
                    "frequency": 1,
                    "last_seen": now,
                    "restriction_ids_sample": restr,
                    "profile_context_sample": profile_context,
                }).execute()
            return True
        except (OSError, ConnectionError) as e:
            # Network/DNS unreachable (e.g. Docker without Supabase); don't spam logs
            logging.getLogger(__name__).debug(
                "upsert_unknown_ingredient skipped (unreachable) key=%s: %s", normalized_key[:80], e
            )
            return False
        except Exception as e:
            err_str = str(e)
            # Supabase/httpx often wrap gaierror; treat as network and log at DEBUG
            if "Name or service not known" in err_str or "Errno -2" in err_str or "getaddrinfo" in err_str:
                logging.getLogger(__name__).debug(
                    "upsert_unknown_ingredient skipped (unreachable) key=%s: %s", normalized_key[:80], e
                )
                return False
            logging.getLogger(__name__).warning(
                "upsert_unknown_ingredient failed key=%s: %s", normalized_key[:80], e
            )
            return False

