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
  - It only runs when you execute it manually:
        python seed_ingredient_knowledge.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

# Load .env from backend/ then repo root so Supabase credentials are available
_backend_dir = Path(__file__).resolve().parent
_repo_root = _backend_dir.parent
load_dotenv(_backend_dir / ".env")
load_dotenv(_repo_root / ".env")

from supabase import create_client, Client

from core.config import get_ontology_path


def _env(key: str, *alt_keys: str) -> str:
    """Get env var by exact key or by stripped key (handles trailing/leading space in .env)."""
    for k in (key, *alt_keys):
        v = os.environ.get(k)
        if v and v.strip():
            return v.strip()
    # Match by stripped key (e.g. .env line "SUPABASE_SERVICE_ROLE_KEY = value" can leave key with spaces)
    key_upper = key.upper().strip()
    for k, v in os.environ.items():
        if k.strip().upper() == key_upper and (v or "").strip():
            return (v or "").strip()
    return ""


def get_supabase_client() -> Client:
    url = _env("SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_URL")
    # Support multiple common key names: prefer explicit service role, but
    # fall back to SUPABASE_KEY if that's what is configured.
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


def load_ontology() -> Dict[str, Any]:
    path = get_ontology_path()
    if not path.exists():
        raise FileNotFoundError(f"Ontology file not found at {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalize_key(text: str) -> str:
    """Detached copy of the normalization rules used for ontology IDs."""
    t = (text or "").strip().lower()
    for ch in ("*", ".", ",", ";", ":", "-", "\u2013", "\u2014"):
        t = t.replace(ch, " ")
    while "  " in t:
        t = t.replace("  ", " ")
    return t.strip()


def seed_from_ontology(supabase: Client, ontology: Dict[str, Any]) -> None:
    ingredients: List[Dict[str, Any]] = ontology.get("ingredients", [])
    total = len(ingredients)
    print(f"Seeding ingredient knowledge from ontology.json: {total} entries")

    for idx, item in enumerate(ingredients, start=1):
        canonical_name = item.get("canonical_name") or item.get("id")
        if not canonical_name:
            continue

        canon_norm = normalize_key(canonical_name)
        # 1) Upsert group (one group per ontology row; version=1, LOCKED)
        group_payload = {
            "canonical_name": canonical_name,
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
            "knowledge_state": "LOCKED",
            "version": 1,
            "uncertainty_flags": item.get("uncertainty_flags") or [],
            "derived_from": item.get("derived_from") or [],
            "contains": item.get("contains") or [],
            "may_contain": item.get("may_contain") or [],
            "regions": item.get("regions") or [],
        }

        # Upsert on canonical_name (active rows only). Supabase Python client
        # does not support partial index upsert directly, so we:
        #  - try select existing active group by canonical_name
        #  - insert if none found
        group_resp = supabase.table("ingredient_groups").select("id").eq("canonical_name", canonical_name).is_("superseded_by", None).limit(1).execute()
        if group_resp.data:
            group_id = group_resp.data[0]["id"]
        else:
            insert_resp = supabase.table("ingredient_groups").insert(group_payload).execute()
            group_id = insert_resp.data[0]["id"]

        # 2) Upsert ingredient row for this ontology entry
        ing_name = canonical_name
        ing_norm = canon_norm
        ing_payload = {
            "name": ing_name,
            "normalized_name": ing_norm,
            "group_id": group_id,
            "source": "ontology",
            "confidence": "high",
            "version": 1,
        }

        ing_resp = supabase.table("ingredients").select("id").eq("normalized_name", ing_norm).is_("superseded_by", None).limit(1).execute()
        if ing_resp.data:
            ingredient_id = ing_resp.data[0]["id"]
        else:
            ins = supabase.table("ingredients").insert(ing_payload).execute()
            ingredient_id = ins.data[0]["id"]

        # 3) Upsert aliases (including canonical name itself)
        alias_values = item.get("aliases") or []
        alias_values = list(alias_values)
        if canonical_name not in alias_values:
            alias_values.append(canonical_name)

        for alias in alias_values:
            norm_alias = normalize_key(alias)
            if not norm_alias:
                continue
            alias_resp = supabase.table("ingredient_aliases").select("id").eq("normalized_alias", norm_alias).limit(1).execute()
            if alias_resp.data:
                continue
            alias_payload = {
                "alias": alias,
                "normalized_alias": norm_alias,
                "ingredient_id": ingredient_id,
                "alias_type": "canonical" if alias == canonical_name else "synonym",
                "language": "en",
            }
            supabase.table("ingredient_aliases").insert(alias_payload).execute()

        if idx % 100 == 0:
            print(f"  seeded {idx}/{total} ontology entries...")

    print("Done seeding ingredient_groups, ingredients, and ingredient_aliases from ontology.json")


def main() -> None:
    supabase = get_supabase_client()
    ontology = load_ontology()
    seed_from_ontology(supabase, ontology)


if __name__ == "__main__":
    main()

