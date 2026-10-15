#!/usr/bin/env python3
"""Minimal IKE-2 seed for CI live-DB tests (alias view + audits).

Inserts one USDA bulk group with alias ``bread and acesulfame`` so
``test_live_alias_view_exposes_source_and_bulk_uncapped`` can run without a
full layer1 inject. Idempotent.
"""
from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv

load_dotenv(_BACKEND.parent / ".env")
load_dotenv(_BACKEND / ".env")

from core.knowledge.ingredient_db import get_supabase_config
from supabase import create_client

_ALIAS = "bread and acesulfame"
_CANON = "ci_bread_and_acesulfame"


def main() -> int:
    cfg = get_supabase_config()
    if not cfg:
        print("SUPABASE_URL / service role not set", file=sys.stderr)
        return 1
    client = create_client(cfg.url, cfg.key)
    existing = (
        client.table("ike2_aliases")
        .select("id")
        .eq("normalized_alias", _ALIAS)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        print(f"alias already present: {_ALIAS}")
        return 0

    grp = (
        client.table("ike2_ingredient_groups")
        .insert(
            {
                "canonical_name": _CANON,
                "source": "usda",
                "knowledge_state": "AUTO_CLASSIFIED",
                "gluten_source": True,
                "classification_method": "bulk:usda",
            }
        )
        .execute()
        .data[0]
    )
    ing = (
        client.table("ike2_ingredients")
        .insert({"group_id": grp["id"], "normalized_name": _CANON})
        .execute()
        .data[0]
    )
    client.table("ike2_aliases").insert(
        {
            "normalized_alias": _ALIAS,
            "ingredient_id": ing["id"],
            "alias_type": "common",
        }
    ).execute()
    print(f"seeded group={_CANON} alias={_ALIAS} source=usda")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
