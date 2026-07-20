#!/usr/bin/env python3
"""
Promote commodity whole foods into data/ontology.json for chat coverage.

Problem: live ontology is a small curated set (~500), while usda_staging /
layer1 dumps hold thousands of plant foods under long USDA names
("Broccoli, raw"). Tier-2 lookup needs short canonicals ("broccoli").

This script:
  1. Extracts clean commodity heads from USDA staging (plant + simple seafood)
  2. Seeds an explicit grocery / produce list with correct diet flags
  3. Merges into ontology.json without downgrading VERIFIED/LOCKED rows

Run from repo root:
  python backend/scripts/promote_commodity_coverage.py --dry-run
  python backend/scripts/promote_commodity_coverage.py
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_ONTOLOGY = _REPO / "data" / "ontology.json"
_BACKUP = _REPO / "data" / "ontology.json.bak"
_USDA_STAGING = _REPO / "data" / "usda_staging.json"
_REPORT = _REPO / "data" / "promote_commodity_report.json"

_PROTECTED = frozenset({"VERIFIED", "LOCKED"})

_PLANT_CATEGORIES = (
    "vegetables and vegetable products",
    "fruits and fruit juices",
    "legumes and legume products",
    "spices and herbs",
    "cereal grains and pasta",
    "nut and seed products",
    "fats and oils",
)

_SEAFOOD_CATEGORIES = (
    "finfish and shellfish products",
)

_SKIP_NAME = re.compile(
    r"babyfood|baby food|applebee|restaurant|fast food|infant|toddler|"
    r"junior|strained|from concentrate|industrial|separable|trimmed to|"
    r"broilers or fryers|ground turkey|with skin|without skin|"
    r"and chicken|and beef|and cheese|mixed|dessert|juice drink|"
    r"nectar|smoothie|pie filling|flavou?r\b",
    re.I,
)

_PREP_TAIL = re.compile(
    r",\s*(raw|dried|dry|fresh|cooked|boiled|drained|frozen|canned|"
    r"unprepared|with salt|without salt|enriched|unenriched|"
    r"with skin|without skin).*$",
    re.I,
)

# Explicit grocery / produce seed — short names users actually type.
# Flags are conservative commodity defaults (USDA/FoodEx2 class), not LOCKED.
_GROCERY_SEED: list[dict[str, Any]] = [
    # Vegetables
    *[{"name": n, "plant_origin": True, "animal_origin": False} for n in [
        "asparagus", "bamboo shoots", "bean sprouts", "beet", "bell pepper",
        "bok choy", "broccoli", "brussels sprouts", "cabbage", "carrot",
        "cauliflower", "celery", "chard", "collard greens", "cucumber",
        "eggplant", "fennel", "green beans", "kale", "kohlrabi", "leek",
        "lettuce", "mushroom", "mustard greens", "okra", "onion", "parsnip",
        "pea", "potato", "radish", "rutabaga", "shallot", "spinach", "squash",
        "sweet potato", "tomato", "turnip", "watercress", "yam",
    ]],
    # Fruits
    *[{"name": n, "plant_origin": True, "animal_origin": False} for n in [
        "apple", "apricot", "banana", "blackberry", "blueberry", "cantaloupe",
        "cherry", "cranberry", "date", "fig", "grapefruit", "grape", "guava",
        "honeydew melon", "kiwi", "lemon", "lime", "mango", "nectarine",
        "orange", "papaya", "peach", "pear", "pineapple", "plum",
        "pomegranate", "raspberry", "strawberry", "tangerine", "watermelon",
    ]],
    # Grains / starches
    *[{"name": n, "plant_origin": True, "animal_origin": False} for n in [
        "amaranth", "arrowroot starch", "buckwheat", "corn", "cornmeal",
        "millet", "oat", "quinoa", "rice", "tapioca", "teff",
    ]],
    # Legumes
    *[{"name": n, "plant_origin": True, "animal_origin": False} for n in [
        "adzuki beans", "black beans", "black-eyed peas", "chickpea",
        "fava beans", "great northern beans", "kidney beans", "lentil",
        "lima beans", "mung beans", "navy beans", "pinto beans", "split peas",
    ]],
    # Oils
    *[{"name": n, "plant_origin": True, "animal_origin": False} for n in [
        "avocado oil", "canola oil", "coconut oil", "corn oil", "grapeseed oil",
        "olive oil", "safflower oil", "sunflower oil",
    ]],
    # Spices / herbs
    *[{"name": n, "plant_origin": True, "animal_origin": False} for n in [
        "allspice", "basil", "bay leaves", "black pepper", "cardamom",
        "cayenne pepper", "cilantro", "cinnamon", "cloves", "coriander",
        "cumin", "curry powder", "dill", "fennel seeds", "garlic powder",
        "ginger", "marjoram", "mint", "nutmeg", "onion powder", "oregano",
        "paprika", "parsley", "rosemary", "saffron", "sage",
        "thyme", "turmeric",
    ]],
    # Seeds / sweeteners / drinks / pantry (plant)
    *[{"name": n, "plant_origin": True, "animal_origin": False} for n in [
        "chia seeds", "flaxseeds", "hemp seeds", "pumpkin seeds",
        "sunflower seeds", "agave nectar", "date sugar", "maple syrup",
        "molasses", "raw cane sugar", "stevia", "chamomile tea", "coffee",
        "green tea", "hibiscus tea", "agar-agar", "apple cider vinegar",
        "balsamic vinegar", "cocoa powder", "vanilla bean", "almond milk",
        "coconut milk", "hemp milk", "oat milk", "rice milk",
        "blackstrap molasses", "coconut aminos", "dijon mustard",
        "nutritional yeast", "tahini", "tomato paste", "tomato puree",
        "vegetable broth",
    ]],
    # Minerals / leaveners — neither plant nor animal
    *[{"name": n, "plant_origin": False, "animal_origin": False} for n in [
        "sea salt", "mineral water", "spring water",
        "baking powder", "baking soda", "cream of tartar",
    ]],
    # Roots / alliums needing extra flags
    {"name": "garlic", "plant_origin": True, "animal_origin": False,
     "root_vegetable": True, "garlic_source": True},
    {"name": "onion", "plant_origin": True, "animal_origin": False,
     "root_vegetable": True, "onion_source": True},
    {"name": "shallot", "plant_origin": True, "animal_origin": False,
     "root_vegetable": True, "onion_source": True},
    {"name": "leek", "plant_origin": True, "animal_origin": False,
     "root_vegetable": True, "onion_source": True},
    {"name": "potato", "plant_origin": True, "animal_origin": False,
     "root_vegetable": True},
    {"name": "sweet potato", "plant_origin": True, "animal_origin": False,
     "root_vegetable": True},
    {"name": "yam", "plant_origin": True, "animal_origin": False,
     "root_vegetable": True},
    {"name": "beet", "plant_origin": True, "animal_origin": False,
     "root_vegetable": True},
    {"name": "carrot", "plant_origin": True, "animal_origin": False,
     "root_vegetable": True},
    {"name": "radish", "plant_origin": True, "animal_origin": False,
     "root_vegetable": True},
    {"name": "turnip", "plant_origin": True, "animal_origin": False,
     "root_vegetable": True},
    {"name": "parsnip", "plant_origin": True, "animal_origin": False,
     "root_vegetable": True},
    {"name": "rutabaga", "plant_origin": True, "animal_origin": False,
     "root_vegetable": True},
    # Seafood (so vegetarian Avoid is correct, not Depends)
    *[{"name": n, "plant_origin": False, "animal_origin": True,
       "animal_species": "fish"} for n in [
        "anchovy", "bass", "carp", "cod", "flounder", "haddock", "halibut",
        "herring", "mackerel", "mahimahi", "perch", "pike", "pollock",
        "salmon", "sardine", "snapper", "sole", "tilapia", "trout", "tuna",
    ]],
    # Land meats
    *[{"name": n, "plant_origin": False, "animal_origin": True,
       "animal_species": "mammal"} for n in [
        "beef", "buffalo", "bison", "lamb", "veal", "venison",
    ]],
    *[{"name": n, "plant_origin": False, "animal_origin": True,
       "animal_species": "bird"} for n in [
        "chicken", "duck", "turkey",
    ]],
    # Dairy
    *[{"name": n, "plant_origin": False, "animal_origin": True,
       "dairy_source": True} for n in [
        "butter", "cheese", "milk", "yogurt",
    ]],
]

_DEFAULT_ENTRY: dict[str, Any] = {
    "derived_from": [],
    "contains": [],
    "may_contain": [],
    "animal_origin": False,
    "plant_origin": False,
    "synthetic": False,
    "fungal": False,
    "insect_derived": False,
    "animal_species": None,
    "egg_source": False,
    "dairy_source": False,
    "gluten_source": False,
    "nut_source": None,
    "soy_source": False,
    "sesame_source": False,
    "alcohol_content": None,
    "root_vegetable": False,
    "onion_source": False,
    "garlic_source": False,
    "fermented": False,
    "uncertainty_flags": [],
    "regions": [],
    "knowledge_state": "AUTO_CLASSIFIED",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _slug(name: str) -> str:
    s = _norm(name).replace(" ", "_")
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    return s.strip("_") or "unknown"


def _root_flags(name: str) -> dict[str, bool]:
    t = _norm(name)
    roots = (
        "potato", "carrot", "beet", "radish", "turnip", "yam", "onion",
        "garlic", "shallot", "leek", "parsnip", "rutabaga", "sweet potato",
    )
    out = {
        "root_vegetable": any(r == t or t.endswith(" " + r) for r in roots),
        "onion_source": t in ("onion", "shallot", "leek", "onion powder") or "onion" in t,
        "garlic_source": t in ("garlic", "garlic powder") or t.startswith("garlic"),
    }
    return out


def extract_commodity_head(canonical_name: str, category: str) -> str | None:
    """Turn 'Broccoli, raw' / 'Spices, cumin seed' into a short chat-friendly head."""
    name = (canonical_name or "").strip()
    if not name or _SKIP_NAME.search(name):
        return None
    low = name.lower()
    cat = (category or "").lower()

    m = re.match(r"^spices,\s*(.+)$", low)
    if m:
        head = re.sub(r",?\s*dried$", "", m.group(1)).strip()
        head = re.sub(r"\s+seed$", " seed", head).strip()
        if 2 <= len(head) <= 40 and " and " not in head:
            return head

    if ", raw" in low:
        head = low.split(",", 1)[0].strip()
        if " and " in head or " with " in head:
            return None
        if len(head.split()) > 4:
            return None
        if 2 <= len(head) <= 40:
            return head

    # Oils / simple plant names without heavy prep
    if cat.startswith("fats and oils") and low.endswith(" oil"):
        if len(low.split()) <= 4 and "mayonnaise" not in low:
            return low

    if "," not in low and len(low.split()) <= 3 and 2 <= len(low) <= 40:
        if any(cat.startswith(c) for c in _PLANT_CATEGORIES + _SEAFOOD_CATEGORIES):
            return low

    # Strip one prep tail: "lentils, dry" -> lentils
    stripped = _PREP_TAIL.sub("", low).strip()
    if stripped != low and "," not in stripped and len(stripped.split()) <= 3:
        if 2 <= len(stripped) <= 40 and " and " not in stripped:
            return stripped

    return None


def _entry_from_flags(name: str, flags: dict[str, Any], *, source: str) -> dict[str, Any]:
    entry = {
        "id": _slug(name),
        "canonical_name": _norm(name),
        "aliases": [],
        **{k: (list(v) if isinstance(v, list) else v) for k, v in _DEFAULT_ENTRY.items()},
    }
    for k, v in flags.items():
        if k in ("name", "aliases"):
            continue
        entry[k] = v
    roots = _root_flags(name)
    for k, v in roots.items():
        if v:
            entry[k] = True
    entry["knowledge_state"] = "AUTO_CLASSIFIED"
    # Do NOT put provenance in uncertainty_flags — IKE-2 treats any
    # uncertainty_flags as verdict uncertainty (Depends). Provenance belongs
    # in knowledge_state / optional non-gating metadata only.
    entry["uncertainty_flags"] = []
    return entry


def load_usda_commodities() -> list[dict[str, Any]]:
    if not _USDA_STAGING.exists():
        return []
    data = json.loads(_USDA_STAGING.read_text(encoding="utf-8"))
    rows = data.get("ingredients") or []
    by_head: dict[str, dict[str, Any]] = {}

    for raw in rows:
        if not isinstance(raw, dict):
            continue
        cat = (raw.get("_usda_category") or "").strip()
        cat_l = cat.lower()
        is_plant_cat = any(cat_l.startswith(c) for c in _PLANT_CATEGORIES)
        is_fish_cat = any(cat_l.startswith(c) for c in _SEAFOOD_CATEGORIES)
        if not is_plant_cat and not is_fish_cat:
            continue
        if is_plant_cat and not raw.get("plant_origin"):
            # Still allow if category is plant (some oils flagged oddly)
            if not cat_l.startswith("fats and oils"):
                continue
        head = extract_commodity_head(raw.get("canonical_name") or "", cat)
        if not head:
            continue
        head_n = _norm(head)
        aliases = [raw.get("canonical_name"), *(raw.get("aliases") or [])]
        aliases = [a for a in aliases if a and _norm(a) != head_n]

        if head_n not in by_head:
            flags = {
                "plant_origin": bool(raw.get("plant_origin")) or is_plant_cat,
                "animal_origin": bool(raw.get("animal_origin")) or is_fish_cat,
                "dairy_source": bool(raw.get("dairy_source")),
                "egg_source": bool(raw.get("egg_source")),
                "gluten_source": bool(raw.get("gluten_source")),
                "soy_source": bool(raw.get("soy_source")),
                "sesame_source": bool(raw.get("sesame_source")),
                "nut_source": raw.get("nut_source"),
                "root_vegetable": bool(raw.get("root_vegetable")),
                "onion_source": bool(raw.get("onion_source")),
                "garlic_source": bool(raw.get("garlic_source")),
            }
            if is_fish_cat:
                flags["plant_origin"] = False
                flags["animal_origin"] = True
                flags["animal_species"] = "fish"
            entry = _entry_from_flags(head_n, flags, source="usda")
            entry["aliases"] = []
            by_head[head_n] = entry

        existing = by_head[head_n]
        seen = {_norm(a) for a in existing.get("aliases") or []}
        seen.add(head_n)
        for a in aliases:
            an = _norm(a)
            if an and an not in seen:
                existing["aliases"].append(a if isinstance(a, str) else str(a))
                seen.add(an)
        # OR boolean flags
        for flag in (
            "plant_origin", "animal_origin", "dairy_source", "egg_source",
            "gluten_source", "soy_source", "sesame_source", "root_vegetable",
            "onion_source", "garlic_source",
        ):
            if raw.get(flag):
                existing[flag] = True

    return list(by_head.values())


def load_grocery_seed() -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}
    for raw in _GROCERY_SEED:
        name = _norm(raw["name"])
        entry = _entry_from_flags(name, raw, source="grocery_seed")
        if name in by_name:
            for flag in (
                "plant_origin", "animal_origin", "dairy_source", "egg_source",
                "root_vegetable", "onion_source", "garlic_source",
            ):
                if raw.get(flag):
                    by_name[name][flag] = True
            if raw.get("animal_species"):
                by_name[name]["animal_species"] = raw["animal_species"]
        else:
            by_name[name] = entry
    return list(by_name.values())


def _index_ontology(ingredients: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for ing in ingredients:
        keys = {_norm(ing.get("canonical_name") or ""), _norm(ing.get("id") or "")}
        for a in ing.get("aliases") or []:
            keys.add(_norm(a))
        keys.discard("")
        for k in keys:
            idx.setdefault(k, ing)
    return idx


def merge_into_ontology(
    ingredients: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
) -> dict[str, int]:
    idx = _index_ontology(ingredients)
    stats = {"new": 0, "merged": 0, "skipped_protected": 0, "aliases_added": 0}

    for row in incoming:
        key = _norm(row.get("canonical_name") or "")
        if not key:
            continue
        existing = idx.get(key)
        if existing is None:
            ingredients.append(row)
            idx[key] = row
            for a in row.get("aliases") or []:
                idx.setdefault(_norm(a), row)
            stats["new"] += 1
            continue

        if (existing.get("knowledge_state") or "") in _PROTECTED:
            # Only add missing aliases; never change flags on LOCKED/VERIFIED
            cur = list(existing.get("aliases") or [])
            seen = {_norm(a) for a in cur}
            seen.add(_norm(existing.get("canonical_name") or ""))
            for a in row.get("aliases") or []:
                an = _norm(a)
                if an and an not in seen:
                    cur.append(a)
                    seen.add(an)
                    stats["aliases_added"] += 1
            existing["aliases"] = cur
            stats["skipped_protected"] += 1
            continue

        for flag in (
            "plant_origin", "animal_origin", "dairy_source", "egg_source",
            "gluten_source", "soy_source", "sesame_source", "root_vegetable",
            "onion_source", "garlic_source", "fungal", "insect_derived",
        ):
            if row.get(flag):
                existing[flag] = True
        if row.get("animal_species") and not existing.get("animal_species"):
            existing["animal_species"] = row["animal_species"]
        if row.get("nut_source") and not existing.get("nut_source"):
            existing["nut_source"] = row["nut_source"]

        cur = list(existing.get("aliases") or [])
        seen = {_norm(a) for a in cur}
        seen.add(_norm(existing.get("canonical_name") or ""))
        for a in row.get("aliases") or []:
            an = _norm(a)
            if an and an not in seen:
                cur.append(a)
                seen.add(an)
                stats["aliases_added"] += 1
        existing["aliases"] = cur

        # Prefer short commodity canonical when existing is a long USDA string
        old_c = _norm(existing.get("canonical_name") or "")
        if "," in old_c and "," not in key and len(key) < len(old_c):
            if old_c not in seen:
                cur.append(existing["canonical_name"])
                existing["aliases"] = cur
            existing["canonical_name"] = key
            existing["id"] = _slug(key)

        ks = existing.get("knowledge_state") or "UNKNOWN"
        if ks in ("UNKNOWN", "DISCOVERED"):
            existing["knowledge_state"] = "AUTO_CLASSIFIED"

        uflags = list(existing.get("uncertainty_flags") or [])
        # Drop provenance-only tags; keep real uncertainty markers.
        uflags = [
            f for f in uflags
            if not str(f).startswith("promoted_from_") and "inferred" not in str(f)
        ]
        existing["uncertainty_flags"] = uflags
        stats["merged"] += 1

    return stats


def promote(*, dry_run: bool = False) -> dict[str, Any]:
    ontology = json.loads(_ONTOLOGY.read_text(encoding="utf-8"))
    ingredients: list[dict[str, Any]] = list(ontology.get("ingredients") or [])
    before = len(ingredients)

    usda = load_usda_commodities()
    seed = load_grocery_seed()
    stats_usda = merge_into_ontology(ingredients, usda)
    stats_seed = merge_into_ontology(ingredients, seed)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "before_count": before,
        "after_count": len(ingredients),
        "usda_commodities_extracted": len(usda),
        "grocery_seed_count": len(seed),
        "usda_merge": stats_usda,
        "seed_merge": stats_seed,
        "dry_run": dry_run,
    }

    if not dry_run:
        shutil.copy2(_ONTOLOGY, _BACKUP)
        ontology["ingredients"] = ingredients
        _ONTOLOGY.write_text(
            json.dumps(ontology, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        _REPORT.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    report = promote(dry_run=args.dry_run)
    print(json.dumps({k: report[k] for k in report if k != "timestamp"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
