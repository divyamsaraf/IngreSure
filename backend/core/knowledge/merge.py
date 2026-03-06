"""
Group-merge and alias consolidation for canonical identity.

When multiple sources report the same substance (e.g. chickpea, chana, garbanzo),
merge their groups into one and consolidate aliases so all names resolve to the
same canonical group.
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple

from core.normalization.normalizer import normalize_ingredient_key

logger = logging.getLogger(__name__)


def merge_groups(
    client: Any,
    keeper_group_id: str,
    mergee_group_ids: List[str],
) -> bool:
    """
    Merge mergee groups into the keeper group. All ingredients and aliases
    end up under the keeper; mergee groups are superseded.

    - For each ingredient I in a mergee group: if keeper already has an
      ingredient with the same normalized_name, reassign I's aliases to that
      ingredient and supersede I; else update I.group_id to keeper.
    - Then supersede each mergee group (set superseded_by = keeper_group_id).
    """
    if not client or not keeper_group_id or not mergee_group_ids:
        return False
    try:
        for mergee_id in mergee_group_ids:
            if mergee_id == keeper_group_id:
                continue
            # Load mergee ingredients (active only)
            ing_resp = (
                client.table("ingredients")
                .select("id, normalized_name, name")
                .eq("group_id", mergee_id)
                .is_("superseded_by", None)
                .execute()
            )
            mergee_ingredients = ing_resp.data or []
            # Load keeper ingredients (active only)
            keeper_resp = (
                client.table("ingredients")
                .select("id, normalized_name")
                .eq("group_id", keeper_group_id)
                .is_("superseded_by", None)
                .execute()
            )
            keeper_by_norm: dict[str, str] = {
                row["normalized_name"]: row["id"] for row in (keeper_resp.data or [])
            }
            for ing in mergee_ingredients:
                norm = ing.get("normalized_name") or ""
                ing_id = ing.get("id")
                if not norm or not ing_id:
                    continue
                keeper_ing_id = keeper_by_norm.get(norm)
                if keeper_ing_id:
                    # Reassign aliases from mergee ingredient to keeper ingredient
                    alias_resp = (
                        client.table("ingredient_aliases")
                        .select("id")
                        .eq("ingredient_id", ing_id)
                        .execute()
                    )
                    for alias_row in (alias_resp.data or []):
                        client.table("ingredient_aliases").update(
                            {"ingredient_id": keeper_ing_id}
                        ).eq("id", alias_row["id"]).execute()
                    # Supersede mergee ingredient
                    client.table("ingredients").update(
                        {"superseded_by": keeper_ing_id}
                    ).eq("id", ing_id).execute()
                else:
                    # Point ingredient to keeper group
                    client.table("ingredients").update(
                        {"group_id": keeper_group_id}
                    ).eq("id", ing_id).execute()
                    keeper_by_norm[norm] = ing_id
            # Supersede mergee group
            client.table("ingredient_groups").update(
                {"superseded_by": keeper_group_id}
            ).eq("id", mergee_id).execute()
        return True
    except Exception as e:
        logger.warning("merge_groups failed keeper=%s mergees=%s: %s", keeper_group_id, mergee_group_ids, e)
        return False


def add_aliases_to_group(
    client: Any,
    group_id: str,
    aliases: List[Tuple[str, str, str, Optional[str]]],
    *,
    alias_type: str = "synonym",
    language: str = "en",
    region: Optional[str] = None,
) -> int:
    """
    Add alias rows for a group. Each tuple is (raw_alias, alias_type, language, region).
    Uses first active ingredient in group for new alias rows. Skips if normalized_alias
    already exists. Returns count of aliases added.
    """
    if not client or not group_id or not aliases:
        return 0
    try:
        ing_resp = (
            client.table("ingredients")
            .select("id")
            .eq("group_id", group_id)
            .is_("superseded_by", None)
            .limit(1)
            .execute()
        )
        if not ing_resp.data:
            return 0
        ingredient_id = ing_resp.data[0]["id"]
        added = 0
        for item in aliases:
            raw = item[0] if len(item) > 0 else ""
            atype = item[1] if len(item) > 1 else alias_type
            lang = item[2] if len(item) > 2 else language
            reg = item[3] if len(item) > 3 else region
            if not raw:
                continue
            norm = normalize_ingredient_key(raw)
            if not norm:
                continue
            # Check if this normalized_alias already exists (anywhere)
            existing = (
                client.table("ingredient_aliases")
                .select("id")
                .eq("normalized_alias", norm)
                .limit(1)
                .execute()
            )
            if existing.data:
                continue
            payload: dict[str, Any] = {
                "alias": raw,
                "normalized_alias": norm,
                "ingredient_id": ingredient_id,
                "alias_type": atype,
                "language": lang,
            }
            if reg is not None:
                payload["region"] = reg
            client.table("ingredient_aliases").insert(payload).execute()
            added += 1
        return added
    except Exception as e:
        logger.warning("add_aliases_to_group failed group_id=%s: %s", group_id, e)
        return 0
