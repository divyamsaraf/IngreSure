#!/usr/bin/env python3
"""
Example: merge duplicate ingredient groups into one (e.g. chana → chickpea).

Finds groups by canonical_name, then merges mergees into keeper.
Use when the same substance exists under multiple names from different sources.

Requires: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY in .env

Usage:
  # Dry run (print what would be merged):
  python scripts/merge_groups_example.py --dry-run chickpea chana "garbanzo bean"

  # Actually merge (chana and garbanzo bean groups into chickpea):
  python scripts/merge_groups_example.py chickpea chana "garbanzo bean"
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend))
os.chdir(_backend)

from dotenv import load_dotenv
load_dotenv(_backend / ".env")
load_dotenv(_backend.parent / ".env")


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge ingredient groups into one canonical group")
    parser.add_argument("keeper", help="Canonical name of the group to keep (e.g. chickpea)")
    parser.add_argument("mergees", nargs="+", help="Canonical names of groups to merge into keeper")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be done")
    args = parser.parse_args()

    from core.knowledge.ingredient_db import IngredientKnowledgeDB
    from core.knowledge.merge import merge_groups

    db = IngredientKnowledgeDB()
    if not db.enabled:
        print("Supabase not configured; set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return 1

    client = db._client

    def find_group_id(canonical_name: str):
        r = (
            client.table("ingredient_groups")
            .select("id, canonical_name")
            .eq("canonical_name", canonical_name)
            .is_("superseded_by", None)
            .limit(1)
            .execute()
        )
        if r.data:
            return r.data[0]["id"], r.data[0]["canonical_name"]
        return None, None

    keeper_id, keeper_name = find_group_id(args.keeper)
    if not keeper_id:
        print(f"Keeper group not found: {args.keeper}")
        return 1
    mergee_ids = []
    for name in args.mergees:
        gid, gname = find_group_id(name)
        if gid and gid != keeper_id:
            mergee_ids.append(gid)
            print(f"  Mergee: {gname!r} -> {gid}")
        elif gid == keeper_id:
            print(f"  Skip (same as keeper): {name}")
        else:
            print(f"  Not found: {name}")

    if not mergee_ids:
        print("No mergees to merge.")
        return 0

    if args.dry_run:
        print(f"Dry run: would merge {len(mergee_ids)} group(s) into keeper {keeper_name!r} ({keeper_id})")
        return 0

    ok = merge_groups(client, keeper_id, mergee_ids)
    if ok:
        print(f"Merged {len(mergee_ids)} group(s) into {keeper_name!r}.")
    else:
        print("Merge failed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
