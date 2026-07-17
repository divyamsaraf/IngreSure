"""
Seed script: populate Supabase ingredient knowledge tables from ontology.json.

Phase 3: conservative 1:1 seeding
----------------------------------
For each entry in data/ontology.json:
  - create a canonical group with the same canonical_name and flags
  - create a single ingredient row pointing to that group
  - create aliases (including the canonical name itself)

This is intentionally conservative: every ontology ingredient becomes its own
group. Later, you can merge groups manually (or via admin tooling) once you
define canonical identities like "egg" that multiple entries should map to.

IMPORTANT:
  - This script is NOT imported by the FastAPI app.
  - Run from backend/:
        python seed_ingredient_knowledge.py [--incremental] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parent
_repo_root = _backend_dir.parent
sys.path.insert(0, str(_backend_dir))

load_dotenv(_backend_dir / ".env")
load_dotenv(_repo_root / ".env")

from supabase import Client, create_client

from core.config import get_ontology_path
from core.normalization.normalizer import normalize_ingredient_key

_KNOWLEDGE_STATE_MAP = {
    "LOCKED": "LOCKED",
    "VERIFIED": "VERIFIED",
    "DISCOVERED": "DISCOVERED",
    "UNKNOWN": "UNKNOWN",
}


def _env(key: str, *alt_keys: str) -> str:
    """Get env var by exact key or by stripped key (handles trailing/leading space in .env)."""
    for k in (key, *alt_keys):
        v = os.environ.get(k)
        if v and v.strip():
            return v.strip()
    key_upper = key.upper().strip()
    for k, v in os.environ.items():
        if k.strip().upper() == key_upper and (v or "").strip():
            return (v or "").strip()
    return ""


def get_supabase_client() -> Client:
    url = _env("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    key = _env(
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_KEY",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        "SERVICE_ROLE_KEY",
    )
    if not url or not key:
        u1 = "set" if _env("SUPABASE_URL") else "not set"
        u2 = "set" if _env("NEXT_PUBLIC_SUPABASE_URL") else "not set"
        k1 = "set" if _env("SUPABASE_SERVICE_ROLE_KEY") else "not set"
        k2 = "set" if _env("NEXT_PUBLIC_SUPABASE_ANON_KEY") else "not set"
        tried = f"Tried .env from: {_backend_dir / '.env'!s}, {_repo_root / '.env'!s}"
        hint = (
            f"SUPABASE_URL={u1}, NEXT_PUBLIC_SUPABASE_URL={u2}, "
            f"SUPABASE_SERVICE_ROLE_KEY={k1}, NEXT_PUBLIC_SUPABASE_ANON_KEY={k2}. "
            "In backend/.env use exactly: SUPABASE_SERVICE_ROLE_KEY=eyJ... (one line, no spaces around =)."
        )
        raise RuntimeError(f"Supabase credentials not set. {hint} {tried}")
    return create_client(url, key)


def load_ontology() -> dict[str, Any]:
    path = get_ontology_path()
    if not path.exists():
        raise FileNotFoundError(f"Ontology file not found at {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def map_knowledge_state(json_state: str | None) -> str:
    if not json_state:
        return "DISCOVERED"
    return _KNOWLEDGE_STATE_MAP.get(str(json_state).upper(), "DISCOVERED")


def build_group_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical_name": item.get("canonical_name") or item.get("id"),
        "origin_type": None,
        "animal_origin": bool(item.get("animal_origin", False)),
        "plant_origin": bool(item.get("plant_origin", False)),
        "synthetic": bool(item.get("synthetic", False)),
        "fungal": bool(item.get("fungal", False)),
        "insect_derived": bool(item.get("insect_derived", False)),
        "animal_species": item.get("animal_species"),
        "egg_source": bool(item.get("egg_source", False)),
        "dairy_source": bool(item.get("dairy_source", False)),
        "gluten_source": bool(item.get("gluten_source", False)),
        "nut_source": item.get("nut_source"),
        "soy_source": bool(item.get("soy_source", False)),
        "sesame_source": bool(item.get("sesame_source", False)),
        "alcohol_content": item.get("alcohol_content"),
        "root_vegetable": bool(item.get("root_vegetable", False)),
        "onion_source": bool(item.get("onion_source", False)),
        "garlic_source": bool(item.get("garlic_source", False)),
        "fermented": bool(item.get("fermented", False)),
        "knowledge_state": map_knowledge_state(item.get("knowledge_state")),
        "version": 1,
        "uncertainty_flags": item.get("uncertainty_flags") or [],
        "derived_from": item.get("derived_from") or [],
        "contains": item.get("contains") or [],
        "may_contain": item.get("may_contain") or [],
        "regions": item.get("regions") or [],
    }


def collect_alias_values(item: dict[str, Any], canonical_name: str) -> list[str]:
    alias_values = list(item.get("aliases") or [])
    if canonical_name not in alias_values:
        alias_values.append(canonical_name)
    return alias_values


def fetch_existing_groups(supabase: Client) -> set[str]:
    resp = supabase.table("ingredient_groups").select("canonical_name").execute()
    return {row["canonical_name"] for row in (resp.data or []) if row.get("canonical_name")}


def fetch_existing_normalized_aliases(supabase: Client) -> set[str]:
    resp = supabase.table("ingredient_aliases").select("normalized_alias").execute()
    return {row["normalized_alias"] for row in (resp.data or []) if row.get("normalized_alias")}


def fetch_group_id_by_canonical(supabase: Client, canonical_name: str) -> str | None:
    resp = (
        supabase.table("ingredient_groups")
        .select("id")
        .eq("canonical_name", canonical_name)
        .is_("superseded_by", None)
        .limit(1)
        .execute()
    )
    if resp.data:
        return resp.data[0]["id"]
    return None


def fetch_ingredient_id_by_normalized(supabase: Client, normalized_name: str) -> str | None:
    resp = (
        supabase.table("ingredients")
        .select("id")
        .eq("normalized_name", normalized_name)
        .is_("superseded_by", None)
        .limit(1)
        .execute()
    )
    if resp.data:
        return resp.data[0]["id"]
    return None


def force_reseed_delete_all(supabase: Client) -> None:
    print("Force reseed: deleting ingredient_aliases, ingredients, ingredient_groups...")
    supabase.table("ingredient_aliases").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    supabase.table("ingredients").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    supabase.table("ingredient_groups").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    print("Existing seed data deleted.")


def seed_from_ontology(
    supabase: Client,
    ontology: dict[str, Any],
    *,
    incremental: bool = False,
    dry_run: bool = False,
    batch_size: int = 100,
) -> dict[str, Any]:
    ingredients: list[dict[str, Any]] = ontology.get("ingredients", [])
    total = len(ingredients)
    print(f"Seeding ingredient knowledge from ontology.json: {total} entries")
    print(f"  incremental={incremental}  dry_run={dry_run}  batch_size={batch_size}")

    existing_names: set[str] = set()
    existing_aliases: set[str] = set()
    if incremental:
        existing_names = fetch_existing_groups(supabase)
        existing_aliases = fetch_existing_normalized_aliases(supabase)
        print(f"  Found {len(existing_names)} existing groups, {len(existing_aliases)} existing aliases")

    groups_inserted = 0
    groups_skipped = 0
    aliases_inserted = 0
    errors: list[str] = []
    would_insert_groups: list[str] = []
    would_insert_aliases = 0

    for batch_start in range(0, total, batch_size):
        batch = ingredients[batch_start : batch_start + batch_size]
        batch_end = min(batch_start + batch_size, total)

        for item in batch:
            canonical_name = item.get("canonical_name") or item.get("id")
            if not canonical_name:
                continue

            canon_norm = normalize_ingredient_key(canonical_name)
            alias_values = collect_alias_values(item, canonical_name)
            group_exists = canonical_name in existing_names

            if dry_run:
                if not group_exists:
                    would_insert_groups.append(canonical_name)
                for alias in alias_values:
                    norm_alias = normalize_ingredient_key(alias)
                    if norm_alias and norm_alias not in existing_aliases:
                        would_insert_aliases += 1
                continue

            try:
                if incremental and group_exists:
                    groups_skipped += 1
                    group_id = fetch_group_id_by_canonical(supabase, canonical_name)
                    if not group_id:
                        errors.append(f"{canonical_name}: marked existing but group id not found")
                        continue
                    ingredient_id = fetch_ingredient_id_by_normalized(supabase, canon_norm)
                    if not ingredient_id:
                        ing_payload = {
                            "name": canonical_name,
                            "normalized_name": canon_norm,
                            "group_id": group_id,
                            "source": "ontology",
                            "confidence": "high",
                            "version": 1,
                        }
                        ins = supabase.table("ingredients").insert(ing_payload).execute()
                        ingredient_id = ins.data[0]["id"]
                else:
                    if group_exists:
                        groups_skipped += 1
                        group_id = fetch_group_id_by_canonical(supabase, canonical_name)
                    else:
                        insert_resp = (
                            supabase.table("ingredient_groups")
                            .insert(build_group_payload(item))
                            .execute()
                        )
                        group_id = insert_resp.data[0]["id"]
                        existing_names.add(canonical_name)
                        groups_inserted += 1

                    if not group_id:
                        errors.append(f"{canonical_name}: failed to resolve group_id")
                        continue

                    ingredient_id = fetch_ingredient_id_by_normalized(supabase, canon_norm)
                    if not ingredient_id:
                        ing_payload = {
                            "name": canonical_name,
                            "normalized_name": canon_norm,
                            "group_id": group_id,
                            "source": "ontology",
                            "confidence": "high",
                            "version": 1,
                        }
                        ins = supabase.table("ingredients").insert(ing_payload).execute()
                        ingredient_id = ins.data[0]["id"]

                for alias in alias_values:
                    norm_alias = normalize_ingredient_key(alias)
                    if not norm_alias:
                        continue
                    if norm_alias in existing_aliases:
                        continue
                    alias_payload = {
                        "alias": alias,
                        "normalized_alias": norm_alias,
                        "ingredient_id": ingredient_id,
                        "alias_type": "canonical" if alias == canonical_name else "synonym",
                        "language": "en",
                    }
                    supabase.table("ingredient_aliases").insert(alias_payload).execute()
                    existing_aliases.add(norm_alias)
                    aliases_inserted += 1

            except Exception as exc:  # noqa: BLE001 — collect and continue batch seeding
                errors.append(f"{canonical_name}: {exc}")

        done = batch_end
        if dry_run:
            print(f"Batch complete: {done}/{total} ({done / total * 100:.1f}%)")
        else:
            print(f"Batch complete: {done}/{total} ({done / total * 100:.1f}%)")
            time.sleep(0.5)

    if dry_run:
        print(f"Would insert: {len(would_insert_groups)} new groups, {would_insert_aliases} new aliases")
        print("First 10 entries that would be inserted as new groups:")
        for name in would_insert_groups[:10]:
            print(f"  - {name}")
        if len(would_insert_groups) > 10:
            print(f"  ... and {len(would_insert_groups) - 10} more")
    else:
        print(f"Done: {groups_inserted} groups inserted, {groups_skipped} skipped")
        print(f"      {aliases_inserted} aliases inserted")
        if errors:
            print(f"Errors ({len(errors)}):")
            for err in errors[:10]:
                print(f"  {err}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more")

    return {
        "groups_inserted": groups_inserted,
        "groups_skipped": groups_skipped,
        "aliases_inserted": aliases_inserted,
        "errors": errors,
        "would_insert_groups": len(would_insert_groups) if dry_run else 0,
        "would_insert_aliases": would_insert_aliases if dry_run else 0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Supabase ingredient knowledge from ontology.json")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only insert entries not already in Supabase",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be inserted without writing",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Entries per Supabase batch (default 100)",
    )
    parser.add_argument(
        "--force-reseed",
        action="store_true",
        help="Delete all existing data and reseed from scratch",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.force_reseed and args.incremental:
        raise SystemExit("Cannot use --force-reseed with --incremental")

    supabase = get_supabase_client()
    ontology = load_ontology()

    if args.force_reseed:
        if args.dry_run:
            print("Dry run: would delete all seed data and reinsert from ontology")
        else:
            force_reseed_delete_all(supabase)

    seed_from_ontology(
        supabase,
        ontology,
        incremental=args.incremental,
        dry_run=args.dry_run,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
