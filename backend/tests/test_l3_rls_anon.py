"""Anon key must not read ike2_* tables on local Supabase (RLS, no policies)."""
from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(_BACKEND, ".env"))

_IKE2_RELATIONS = (
    "ike2_ingredient_groups",
    "ike2_ingredients",
    "ike2_aliases",
    "ike2_alias_disambiguation",
    "ike2_restriction_rules",
    "ike2_resolution_cache",
    "ike2_unknown_queue",
    "ike2_shadow_diffs",
    "ike2_group_merges",
    "ike2_v_alias_resolution",
)


def _local_url() -> str:
    return (os.getenv("SUPABASE_URL") or "").strip()


def _anon_key() -> str:
    return (
        os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        or ""
    ).strip()


def _has_local_anon() -> bool:
    url = _local_url()
    key = _anon_key()
    if not url or not key:
        return False
    return "127.0.0.1" in url or "localhost" in url


pytestmark = pytest.mark.skipif(
    not _has_local_anon(),
    reason="needs local supabase + SUPABASE_ANON_KEY from supabase start",
)


def test_anon_key_cannot_read_ike2_tables():
    """Expected policy: RLS on, no GRANT/policies for anon → empty or error.

    Never invent keys. Uses SUPABASE_ANON_KEY / NEXT_PUBLIC_SUPABASE_ANON_KEY
    from the environment after `supabase start`.
    """
    from supabase import create_client

    url = _local_url()
    key = _anon_key()
    assert "supabase.co" not in url
    client = create_client(url, key)
    leaked = []
    for name in _IKE2_RELATIONS:
        try:
            resp = client.table(name).select("*").limit(5).execute()
            rows = getattr(resp, "data", None) or []
            if rows:
                leaked.append((name, len(rows)))
        except Exception:
            # Permission / RLS / missing GRANT is the intended deny path.
            continue
    assert leaked == [], (
        "anon key read ike2_* rows (expected RLS deny / empty): "
        f"{leaked}. See deploy/l3_local_suites.md."
    )
