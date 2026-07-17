from types import SimpleNamespace
from typing import Literal, Optional

from core.knowledge.ingredient_db import get_supabase_config

# A resolved group row from the ike2_v_alias_resolution view, exposed via
# attribute access (e.g. group.canonical_name).
GroupRow = SimpleNamespace

_VIEW = "ike2_v_alias_resolution"
_DISAMBIG = "ike2_alias_disambiguation"

_client = None


def _supabase():
    global _client
    if _client is None:
        cfg = get_supabase_config()
        if not cfg:
            raise RuntimeError("Supabase not configured (SUPABASE_URL + service key)")
        from supabase import create_client

        _client = create_client(cfg.url, cfg.key)
    return _client


def _alias_rows(normalized_alias: str):
    return (
        _supabase()
        .from_(_VIEW)
        .select("*")
        .eq("normalized_alias", normalized_alias)
        .execute()
        .data
    )


def _scope_to_region(rows, region: Optional[str]):
    if not region:
        return rows
    scoped = [r for r in rows if r.get("region") == region]
    if scoped:
        return scoped
    # fall back to GLOBAL (region-less) aliases
    return [r for r in rows if r.get("region") is None]


def resolve_alias(normalized_alias: str, region: Optional[str]) -> Optional[GroupRow]:
    rows = _scope_to_region(_alias_rows(normalized_alias), region)
    distinct = {r["ingredient_id"] for r in rows}
    if len(distinct) == 1:
        return GroupRow(**rows[0])
    return None


def disambiguate(
    normalized_alias: str, region: Optional[str]
) -> Literal["unique", "ambiguous", "none"]:
    rows = _alias_rows(normalized_alias)
    if not rows:
        return "none"
    rows = _scope_to_region(rows, region)
    distinct = {r["ingredient_id"] for r in rows}
    if len(distinct) == 0:
        return "none"
    if len(distinct) == 1:
        return "unique"
    if region:
        winners = (
            _supabase()
            .table(_DISAMBIG)
            .select("ingredient_id")
            .eq("normalized_alias", normalized_alias)
            .eq("context_region", region)
            .execute()
            .data
        )
        if winners:
            return "unique"
    return "ambiguous"
