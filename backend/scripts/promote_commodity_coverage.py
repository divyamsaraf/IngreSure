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
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_BACKEND = _REPO / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

_ONTOLOGY = _REPO / "data" / "ontology.json"
_BACKUP = _REPO / "data" / "ontology.json.bak"
_USDA_STAGING = _REPO / "data" / "usda_staging.json"
_REPORT = _REPO / "data" / "promote_commodity_report.json"
_EXPANDED_LIST = _REPO / "data" / "commodity_seed_lists" / "expanded_grocery.txt"
_IDENTITY_EXPAND = _REPO / "data" / "commodity_seed_lists" / "identity_expand.txt"
_VARIANT_ALIASES = _REPO / "data" / "commodity_seed_lists" / "variant_aliases.json"
_LAYER1_NIN = _REPO / "data" / "layer1_nin.json"
_LAYER1_IFCT = _REPO / "data" / "layer1_ifct.json"
_LAYER1_FOODEX2 = _REPO / "data" / "layer1_foodex2.json"
_REGIONAL_NAMES = _REPO / "data" / "regional_ingredient_names.json"

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

_MEAT_CATEGORIES = (
    "poultry products",
    "beef products",
    "pork products",
    "lamb, veal, and game products",
    "sausages and luncheon meats",
)

_DAIRY_CATEGORIES = (
    "dairy and egg products",
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

# Chat variants -> ontology canonical (also stored as aliases on the target).
_ALIAS_TO_CANONICAL: dict[str, str] = {
    "bell peppers": "bell pepper",
    "scallions": "scallion",
    "green onions": "scallion",
    "spring onions": "scallion",
    "corn starch": "cornstarch",
    "cornflour": "cornstarch",
    "açaí": "acai",
    "açai": "acai",
    "acai berry": "acai",
    "dragonfruit": "dragon fruit",
    "starfruit": "star fruit",
    "sunchoke": "sunchokes",
    "jerusalem artichoke": "sunchokes",
    "jerusalem artichokes": "sunchokes",
    "capres": "capers",  # common typo in lists
    "zaatar": "za'atar",
    "za atar": "za'atar",
    "asafoetida": "asafetida",
    "hing": "asafetida",
    "chicken eggs": "egg",
    "duck eggs": "duck egg",
    "quail eggs": "quail egg",
    "egg whites": "egg white",
    "egg yolks": "egg yolk",
    "swiss cheese": "swiss cheese",
    "feta cheese": "feta",
    "goat cheese": "goat cheese",
    "okra pods": "okra",
    "pepitas": "pumpkin seeds",
    "sunflower kernels": "sunflower seeds",
    "tiger nuts": "tigernuts",
    "yam bean": "jicama",
    "buffalo / bison": "bison",
    "wild boar": "wild boar",
    "powdered sugar": "powdered sugar",
    "icing sugar": "powdered sugar",
    "confectioners sugar": "powdered sugar",
}

_FISH = frozenset({
    "anchovy", "anchovies", "bass", "carp", "cod", "flounder", "haddock",
    "halibut", "herring", "mackerel", "mahimahi", "perch", "pike", "pollock",
    "salmon", "sardine", "sardines", "snapper", "sole", "tilapia", "trout",
    "tuna", "barramundi", "amberjack", "catfish", "grouper", "hake",
    "kingfish", "turbot", "eel", "sea bass", "sea bream", "john dory",
    "plaice", "pompano", "bonito",
})
_BIRD = frozenset({
    "chicken", "duck", "turkey", "quail", "pheasant", "goose", "ostrich", "squab",
})
_MAMMAL = frozenset({
    "beef", "buffalo", "bison", "lamb", "veal", "venison", "pork", "goat",
    "rabbit", "wild boar", "elk", "alligator", "kangaroo",
})
_DAIRY = frozenset({
    "butter", "cheese", "milk", "yogurt", "cream", "sour cream", "cream cheese",
    "cottage cheese", "ricotta", "mascarpone", "gorgonzola", "parmesan",
    "cheddar", "mozzarella", "feta", "gouda", "brie", "swiss cheese",
    "provolone", "buttermilk", "heavy cream", "evaporated milk",
    "condensed milk", "goat milk", "goat cheese", "sheep milk", "feta cheese",
    "ghee", "camembert", "blue cheese", "edam", "emmental", "comte", "comté",
    "quark", "colby", "fontina", "stilton", "monterey jack", "cotija",
    "brick cheese", "buffalo mozzarella", "paneer",
})
_EGG = frozenset({
    "egg", "chicken eggs", "duck eggs", "quail eggs", "egg whites", "egg yolks",
    "duck egg", "quail egg", "egg white", "egg yolk",
})
_ANIMAL_FAT = frozenset({"lard", "tallow"})
_BEE = frozenset({"honey"})
_PEANUT = frozenset({"peanut", "peanuts", "peanut oil"})
_SESAME = frozenset({
    "sesame", "sesame seeds", "black sesame seeds", "sesame oil", "tahini",
})
_TREE_NUT = frozenset({
    "almond", "almonds", "walnut", "walnuts", "cashew", "cashews", "pistachio",
    "pistachios", "pecan", "pecans", "hazelnut", "hazelnuts", "macadamia nuts",
    "brazil nuts", "pine nuts", "chestnut", "chestnuts", "almond oil",
    "walnut oil", "hazelnut oil", "almond flour",
    # coconut and water chestnut are NOT tree-nut allergens for our rules
})
_SOY = frozenset({"soybeans", "edamame", "soy", "soya"})
_GLUTEN = frozenset({
    "wheat", "barley", "rye", "spelt", "kamut", "farro", "freekeh", "bulgur",
    "couscous", "semolina", "barley malt syrup",
})
_MINERAL = frozenset({
    "sea salt", "mineral water", "spring water", "baking powder", "baking soda",
    "cream of tartar", "erythritol", "xylitol",
})

# Prepared / multi-ingredient / coffee-dessert dishes — never invent firm
# dairy/egg/meat flags. Composition varies (e.g. affogato may include gelato
# with dairy and/or egg; vegan versions exist). Tier-1 WARN or L5 Depends.
_COMPOUND_NEVER_FIRM_SEED = frozenset({
    "affogato", "tempered spices", "tadka", "tarka",
    "tiramisu", "latte", "cappuccino", "macchiato", "mocha", "frappe",
    "milkshake", "hot chocolate", "sundae", "parfait", "souffle", "soufflé",
    "spinach souffle", "omelette", "omelet", "quiche", "pancake", "waffle",
    "french toast", "burrito", "taco", "pizza", "veggie burger",
    "ice cream sandwich", "ice cream", "gelato", "custard", "mousse",
    "cheesecake", "smoothie", "protein shake",
})

_COMPOUND_DISH_RE = re.compile(
    r"\b("
    r"affogato|tiramisu|latte|cappuccino|macchiato|mocha|frappe|milkshake|"
    r"sundae|parfait|souffle|soufflé|omelette|omelet|quiche|pancake|waffle|"
    r"burrito|taco|pizza|smoothie|milkshake|cheesecake|mousse|tiramisu|"
    r"sandwich|burger"
    r")\b|\bice cream\b|\bhot chocolate\b|\bfrench toast\b|\bwith\b",
    re.I,
)

# FoodEx2 / IFCT additive-ish labels — not grocery whole foods.
_ADDITIVE_LABEL_RE = re.compile(
    r"\b("
    r"regulator|essence|flavour|flavor|additive|sweetener|colouring|coloring|"
    r"emulsifier|stabiliser|stabilizer|thickener|preservative|agent|"
    r"acesulfame|advantame|aspartame|sucralose|saccharin"
    r")\b|^(acid|acids|acidity regulator)$",
    re.I,
)

# NIN / regional aliases that collide with a different Western identity.
_DANGEROUS_ALIASES = frozenset({
    "cottage cheese",  # Western cottage cheese ≠ paneer
})

# Explicit grocery / produce seed — short names users actually type.
# Flags are conservative commodity defaults (USDA/FoodEx2 class), not LOCKED.
_GROCERY_SEED: list[dict[str, Any]] = []  # built from expanded list + classifier below


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
    """Turn dump names into short chat-friendly heads (shared safe rules)."""
    from core.knowledge.ike2.commodity_head import simple_commodity_head

    name = (canonical_name or "").strip()
    if not name or _SKIP_NAME.search(name):
        return None
    # Prefer shared safe extractor (single-comma prep / spices).
    head = simple_commodity_head(name)
    if head:
        return head

    low = name.lower()
    cat = (category or "").lower()

    # Oils / simple plant names without heavy prep
    if cat.startswith("fats and oils") and low.endswith(" oil"):
        if len(low.split()) <= 4 and "mayonnaise" not in low:
            return _norm(low)

    if "," not in low and len(low.split()) <= 3 and 2 <= len(low) <= 40:
        if any(cat.startswith(c) for c in _PLANT_CATEGORIES + _SEAFOOD_CATEGORIES + _MEAT_CATEGORIES + _DAIRY_CATEGORIES):
            return _norm(low)

    # Strip one prep tail: "lentils, dry" -> lentils (multi-token prep already handled above)
    stripped = _PREP_TAIL.sub("", low).strip()
    if stripped != low and "," not in stripped and len(stripped.split()) <= 3:
        if 2 <= len(stripped) <= 40 and " and " not in stripped:
            return _norm(stripped)

    return None


def classify_flags(name: str) -> dict[str, Any]:
    """Assign conservative diet/allergen flags from the commodity name.

    Diet/origin heuristics live here; allergen bits are finalized by
    ``derive_identity_flags`` so ETL and chat share one derivation path.
    """
    from core.knowledge.ike2.flag_derive import derive_identity_flags

    n = _norm(name)
    n = _ALIAS_TO_CANONICAL.get(n, n)
    flags: dict[str, Any] = {
        "plant_origin": True,
        "animal_origin": False,
    }

    if n in _MINERAL or n.endswith(" salt"):
        return {"plant_origin": False, "animal_origin": False}

    if n in _FISH or n.rstrip("s") in _FISH:
        flags = {
            "plant_origin": False,
            "animal_origin": True,
            "animal_species": "fish",
        }
    elif n in _BIRD:
        flags = {"plant_origin": False, "animal_origin": True, "animal_species": "bird"}
    elif n in _MAMMAL:
        flags = {"plant_origin": False, "animal_origin": True, "animal_species": "mammal"}
    elif n in _ANIMAL_FAT:
        flags = {"plant_origin": False, "animal_origin": True, "animal_species": "mammal"}
    elif n in _BEE:
        flags = {"plant_origin": False, "animal_origin": True, "bee_product": True}
    else:
        plant_milks = (
            "almond milk", "oat milk", "rice milk", "coconut milk", "hemp milk", "soy milk",
        )
        if n in plant_milks:
            flags = {"plant_origin": True, "animal_origin": False}
        elif (
            n in _DAIRY
            or n.endswith(" cheese")
            or n in ("goat milk", "sheep milk", "heavy cream", "sour cream")
        ):
            flags = {"plant_origin": False, "animal_origin": True, "dairy_source": True}
        elif n in _EGG or n.endswith(" egg") or n.endswith(" eggs") or n in ("egg white", "egg yolk"):
            flags = {
                "plant_origin": False,
                "animal_origin": True,
                "egg_source": True,
                "animal_species": "bird",
            }
        else:
            if n in _GLUTEN or any(
                g in n for g in ("wheat", "barley", "spelt", "semolina", "farro", "freekeh", "bulgur", "couscous")
            ):
                if "buckwheat" not in n:
                    flags["gluten_source"] = True

    return derive_identity_flags(n, flags, animal_species=flags.get("animal_species"))


def _entry_from_flags(name: str, flags: dict[str, Any], *, source: str) -> dict[str, Any]:
    canon = _ALIAS_TO_CANONICAL.get(_norm(name), _norm(name))
    entry = {
        "id": _slug(canon),
        "canonical_name": canon,
        "aliases": [],
        **{k: (list(v) if isinstance(v, list) else v) for k, v in _DEFAULT_ENTRY.items()},
    }
    for k, v in flags.items():
        if k in ("name", "aliases"):
            continue
        entry[k] = v
    roots = _root_flags(canon)
    for k, v in roots.items():
        if v:
            entry[k] = True
    # Keep original spelling as alias when remapped.
    if _norm(name) != canon:
        entry["aliases"] = [name]
    entry["knowledge_state"] = "AUTO_CLASSIFIED"
    # Do NOT put provenance in uncertainty_flags — IKE-2 treats any
    # uncertainty_flags as verdict uncertainty (Depends).
    entry["uncertainty_flags"] = []
    return entry


def load_usda_commodities() -> list[dict[str, Any]]:
    if not _USDA_STAGING.exists():
        return []
    data = json.loads(_USDA_STAGING.read_text(encoding="utf-8"))
    rows = data.get("ingredients") or []
    by_head: dict[str, dict[str, Any]] = {}
    allowed_cats = _PLANT_CATEGORIES + _SEAFOOD_CATEGORIES + _MEAT_CATEGORIES + _DAIRY_CATEGORIES

    for raw in rows:
        if not isinstance(raw, dict):
            continue
        cat = (raw.get("_usda_category") or "").strip()
        cat_l = cat.lower()
        is_plant_cat = any(cat_l.startswith(c) for c in _PLANT_CATEGORIES)
        is_fish_cat = any(cat_l.startswith(c) for c in _SEAFOOD_CATEGORIES)
        is_meat_cat = any(cat_l.startswith(c) for c in _MEAT_CATEGORIES)
        is_dairy_cat = any(cat_l.startswith(c) for c in _DAIRY_CATEGORIES)
        if not any(cat_l.startswith(c) for c in allowed_cats):
            continue
        if is_plant_cat and not raw.get("plant_origin"):
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
                "animal_origin": bool(raw.get("animal_origin")) or is_fish_cat or is_meat_cat or is_dairy_cat,
                "dairy_source": bool(raw.get("dairy_source")) or is_dairy_cat,
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
                flags["fish_source"] = True
            if is_meat_cat:
                flags["plant_origin"] = False
                flags["animal_origin"] = True
            if is_dairy_cat and not flags.get("egg_source"):
                flags["plant_origin"] = False
                flags["animal_origin"] = True
                flags["dairy_source"] = True
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
        for flag in (
            "plant_origin", "animal_origin", "dairy_source", "egg_source",
            "gluten_source", "soy_source", "sesame_source", "root_vegetable",
            "onion_source", "garlic_source", "fish_source",
        ):
            if raw.get(flag):
                existing[flag] = True

    return list(by_head.values())


def load_grocery_seed() -> list[dict[str, Any]]:
    """Load expanded grocery + identity expand lists; classify flags automatically."""
    names: list[str] = []
    for path in (_EXPANDED_LIST, _IDENTITY_EXPAND):
        if path.exists():
            raw_text = path.read_text(encoding="utf-8")
            names.extend(x.strip() for x in raw_text.replace("\n", " ").split(",") if x.strip())
    for raw in _GROCERY_SEED:
        names.append(raw["name"])

    by_name: dict[str, dict[str, Any]] = {}
    for name in names:
        if _is_compound_dish_name(name):
            continue
        flags = classify_flags(name)
        # Allow inline seed overrides
        for raw in _GROCERY_SEED:
            if _norm(raw["name"]) == _norm(name):
                flags.update({k: v for k, v in raw.items() if k != "name"})
        entry = _entry_from_flags(name, flags, source="grocery_seed")
        key = entry["canonical_name"]
        if key in by_name:
            existing = by_name[key]
            for flag in (
                "plant_origin", "animal_origin", "dairy_source", "egg_source",
                "root_vegetable", "onion_source", "garlic_source", "fish_source",
                "peanut_source", "tree_nut_source", "sesame_source", "soy_source",
                "gluten_source", "bee_product",
            ):
                if entry.get(flag):
                    existing[flag] = True
            if entry.get("animal_species") and not existing.get("animal_species"):
                existing["animal_species"] = entry["animal_species"]
            # merge aliases
            seen = {_norm(a) for a in existing.get("aliases") or []}
            seen.add(key)
            for a in entry.get("aliases") or []:
                if _norm(a) not in seen:
                    existing.setdefault("aliases", []).append(a)
                    seen.add(_norm(a))
            if _norm(name) != key and _norm(name) not in seen:
                existing.setdefault("aliases", []).append(name)
        else:
            if _norm(name) != key:
                entry.setdefault("aliases", [])
                if name not in entry["aliases"]:
                    entry["aliases"].append(name)
            by_name[key] = entry
    return list(by_name.values())


def _static_regional_pairs() -> list[tuple[str, str]]:
    """(regional_key, english_canonical) from curated regional file + built-ins."""
    pairs: list[tuple[str, str]] = []
    try:
        from core.external_apis.regional_names import _BUILTIN_REGIONAL, _load_static, _static_only_regional

        _load_static()
        for k, v in _static_only_regional.items():
            pairs.append((k.replace("_", " "), v))
        for k, v in _BUILTIN_REGIONAL.items():
            pairs.append((k.replace("_", " "), v))
    except Exception:
        pass
    if _REGIONAL_NAMES.exists():
        data = json.loads(_REGIONAL_NAMES.read_text(encoding="utf-8"))
        for entry in data.get("mappings") or []:
            can = (entry.get("canonical") or "").strip()
            if not can:
                continue
            for name in entry.get("regional") or []:
                if name and str(name).strip():
                    pairs.append((str(name).strip(), can))
    # dedupe
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for a, b in pairs:
        key = (_norm(a), _norm(b))
        if key in seen or not key[0] or not key[1]:
            continue
        seen.add(key)
        out.append((a, b))
    return out


def _is_compound_dish_name(name: str) -> bool:
    n = _norm(name)
    if not n:
        return False
    if n in _COMPOUND_NEVER_FIRM_SEED:
        return True
    return bool(_COMPOUND_DISH_RE.search(n))


def _is_promotable_short_food(name: str, flags: dict[str, Any]) -> bool:
    """Strict bar: short whole-food identity with origin signal; no dishes/additives."""
    n = _norm(name)
    if not n or "," in n:
        return False
    if len(n.split()) > 3 or not (2 <= len(n) <= 40):
        return False
    if " and " in n or " with " in n:
        return False
    if _is_compound_dish_name(n):
        return False
    if _ADDITIVE_LABEL_RE.search(n):
        return False
    if flags.get("plant_origin") or flags.get("animal_origin"):
        return True
    if n in _MINERAL or n.endswith(" salt"):
        return True
    return False


def _flags_from_layer1_row(raw: dict[str, Any]) -> dict[str, Any]:
    from core.knowledge.ike2.flag_derive import derive_identity_flags

    name = (raw.get("canonical_name") or "").strip()
    flags: dict[str, Any] = {
        "plant_origin": bool(raw.get("plant_origin")),
        "animal_origin": bool(raw.get("animal_origin")),
        "dairy_source": bool(raw.get("dairy_source")),
        "egg_source": bool(raw.get("egg_source")),
        "gluten_source": bool(raw.get("gluten_source")),
        "soy_source": bool(raw.get("soy_source")),
        "sesame_source": bool(raw.get("sesame_source")),
        "fish_source": bool(raw.get("fish_source")),
        "root_vegetable": bool(raw.get("root_vegetable")),
        "onion_source": bool(raw.get("onion_source")),
        "garlic_source": bool(raw.get("garlic_source")),
    }
    if raw.get("animal_species"):
        flags["animal_species"] = raw["animal_species"]
    flags = derive_identity_flags(name, flags, animal_species=flags.get("animal_species"))
    for alias in raw.get("aliases") or []:
        flags = derive_identity_flags(str(alias), flags, animal_species=flags.get("animal_species"))
    return flags


def load_layer1_regional_foods(path: Path, *, source: str) -> list[dict[str, Any]]:
    """Promote short, flagged whole foods from IFCT / FoodEx2 (strict filter)."""
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        return []
    by_canon: dict[str, dict[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        name = (raw.get("canonical_name") or "").strip()
        if not name:
            continue
        flags = _flags_from_layer1_row(raw)
        if not _is_promotable_short_food(name, flags):
            continue
        entry = _entry_from_flags(name, flags, source=source)
        entry["uncertainty_flags"] = []
        entry["knowledge_state"] = "AUTO_CLASSIFIED"
        if raw.get("regions"):
            entry["regions"] = list(raw["regions"])
        elif raw.get("region"):
            entry["regions"] = [raw["region"]]
        aliases: list[str] = []
        seen = {_norm(entry["canonical_name"])}
        for a in raw.get("aliases") or []:
            an = _norm(a)
            # Skip FoodEx2 code-like aliases
            if an.startswith("foodex") or ":" in an:
                continue
            if an and an not in seen and an not in _DANGEROUS_ALIASES:
                aliases.append(str(a))
                seen.add(an)
        entry["aliases"] = aliases
        key = entry["canonical_name"]
        if key in by_canon:
            existing = by_canon[key]
            for flag in (
                "plant_origin", "animal_origin", "dairy_source", "egg_source",
                "gluten_source", "soy_source", "sesame_source", "fish_source",
                "peanut_source", "tree_nut_source", "root_vegetable",
                "onion_source", "garlic_source",
            ):
                if entry.get(flag):
                    existing[flag] = True
            eseen = {_norm(a) for a in existing.get("aliases") or []}
            eseen.add(_norm(existing.get("canonical_name") or ""))
            for a in aliases:
                if _norm(a) not in eseen:
                    existing.setdefault("aliases", []).append(a)
        else:
            by_canon[key] = entry
    return list(by_canon.values())


def load_nin_commodities() -> list[dict[str, Any]]:
    """Promote curated NIN India foods into chat Tier-2 (design 2026-07-20)."""
    from core.knowledge.ike2.flag_derive import derive_identity_flags

    if not _LAYER1_NIN.exists():
        return []
    rows = json.loads(_LAYER1_NIN.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        return []

    # Reverse regional map: English target -> regional names (and vice versa).
    regional_by_any: dict[str, set[str]] = {}
    for regional, english in _static_regional_pairs():
        rn, en = _norm(regional), _norm(english)
        regional_by_any.setdefault(rn, set()).update({regional, english})
        regional_by_any.setdefault(en, set()).update({regional, english})

    by_canon: dict[str, dict[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        name = (raw.get("canonical_name") or "").strip()
        if not name:
            continue
        flags: dict[str, Any] = {
            "plant_origin": bool(raw.get("plant_origin")),
            "animal_origin": bool(raw.get("animal_origin")),
            "dairy_source": bool(raw.get("dairy_source")),
            "egg_source": bool(raw.get("egg_source")),
            "gluten_source": bool(raw.get("gluten_source")),
            "soy_source": bool(raw.get("soy_source")),
            "sesame_source": bool(raw.get("sesame_source")),
            "fish_source": bool(raw.get("fish_source")),
            "root_vegetable": bool(raw.get("root_vegetable")),
            "onion_source": bool(raw.get("onion_source")),
            "garlic_source": bool(raw.get("garlic_source")),
        }
        if raw.get("animal_species"):
            flags["animal_species"] = raw["animal_species"]
        # Derive from canonical + aliases (atta→gluten, groundnut→peanut, …).
        flags = derive_identity_flags(name, flags, animal_species=flags.get("animal_species"))
        for alias in raw.get("aliases") or []:
            flags = derive_identity_flags(str(alias), flags, animal_species=flags.get("animal_species"))

        entry = _entry_from_flags(name, flags, source="nin")
        entry["uncertainty_flags"] = []
        entry["knowledge_state"] = "AUTO_CLASSIFIED"
        if raw.get("regions"):
            entry["regions"] = list(raw["regions"])
        elif raw.get("region"):
            entry["regions"] = [raw["region"]]

        aliases: list[str] = []
        seen = {_norm(entry["canonical_name"])}
        for a in raw.get("aliases") or []:
            an = _norm(a)
            if an and an not in seen and an not in _DANGEROUS_ALIASES:
                aliases.append(str(a))
                seen.add(an)
        # Attach regional English + regional keys that point at this identity.
        for probe in (name, entry["canonical_name"], *list(raw.get("aliases") or [])):
            for extra in regional_by_any.get(_norm(probe), ()):
                en = _norm(extra)
                if en and en not in seen:
                    aliases.append(extra)
                    seen.add(en)
        # Remapped form of the NIN name (bajra → pearl millet) must be an alias.
        remapped = _ALIAS_TO_CANONICAL.get(_norm(name), _norm(name))
        try:
            from core.normalization.normalizer import normalize_ingredient_key

            remapped_n = normalize_ingredient_key(name, apply_regional=True)
            if remapped_n and remapped_n not in seen:
                aliases.append(remapped_n)
                seen.add(remapped_n)
        except Exception:
            pass
        if remapped and remapped not in seen:
            aliases.append(remapped)
            seen.add(remapped)
        entry["aliases"] = aliases

        key = entry["canonical_name"]
        if key in by_canon:
            existing = by_canon[key]
            for flag in (
                "plant_origin", "animal_origin", "dairy_source", "egg_source",
                "gluten_source", "soy_source", "sesame_source", "fish_source",
                "peanut_source", "tree_nut_source", "root_vegetable",
                "onion_source", "garlic_source",
            ):
                if entry.get(flag):
                    existing[flag] = True
            eseen = {_norm(a) for a in existing.get("aliases") or []}
            eseen.add(_norm(existing.get("canonical_name") or ""))
            for a in aliases:
                if _norm(a) not in eseen:
                    existing.setdefault("aliases", []).append(a)
                    eseen.add(_norm(a))
        else:
            by_canon[key] = entry
    return list(by_canon.values())


def load_regional_target_seeds() -> list[dict[str, Any]]:
    """Ensure every static regional English target has a Tier-2 row (plant default)."""
    names: list[str] = []
    for regional, english in _static_regional_pairs():
        names.append(english)
        names.append(regional)
    by_name: dict[str, dict[str, Any]] = {}
    for name in names:
        if _is_compound_dish_name(name):
            continue
        flags = classify_flags(name)
        entry = _entry_from_flags(name, flags, source="regional_seed")
        entry["uncertainty_flags"] = []
        key = entry["canonical_name"]
        if key in by_name:
            existing = by_name[key]
            seen = {_norm(a) for a in existing.get("aliases") or []}
            seen.add(key)
            if _norm(name) != key and _norm(name) not in seen:
                existing.setdefault("aliases", []).append(name)
        else:
            if _norm(name) != key:
                entry.setdefault("aliases", []).append(name)
            by_name[key] = entry
    return list(by_name.values())


def apply_variant_aliases_as_row_aliases(ingredients: list[dict[str, Any]]) -> int:
    """Attach curated L2 variant phrases onto target ontology rows (offline M2–M7)."""
    if not _VARIANT_ALIASES.exists():
        return 0
    data = json.loads(_VARIANT_ALIASES.read_text(encoding="utf-8"))
    aliases = data.get("aliases") or {}
    idx = _index_ontology(ingredients)
    added = 0
    for src, dst in aliases.items():
        if str(src).startswith("_"):
            continue
        sn, dn = _norm(src), _norm(dst)
        if not sn or not dn or sn == dn:
            continue
        target = idx.get(dn)
        if target is None:
            continue
        if (target.get("knowledge_state") or "") in _PROTECTED:
            # Still allow alias attach on protected rows (routing only).
            pass
        cur = list(target.get("aliases") or [])
        seen = {_norm(a) for a in cur}
        seen.add(_norm(target.get("canonical_name") or ""))
        if sn not in seen:
            cur.append(src)
            target["aliases"] = cur
            idx.setdefault(sn, target)
            added += 1
    return added


def _scrub_compound_never_firm(ingredients: list[dict[str, Any]]) -> int:
    """Remove invented firm rows for compounds; strip dangerous aliases (paneer≠cottage cheese)."""
    removed = 0
    kept: list[dict[str, Any]] = []
    for row in ingredients:
        canon = _norm(row.get("canonical_name") or "")
        if _is_compound_dish_name(canon):
            removed += 1
            continue
        aliases = [
            a for a in (row.get("aliases") or [])
            if _norm(a) not in _DANGEROUS_ALIASES and not _is_compound_dish_name(a)
        ]
        if len(aliases) != len(row.get("aliases") or []):
            row["aliases"] = aliases
            removed += 1
        kept.append(row)
    ingredients[:] = kept
    return removed


def _scrub_contradictory_identity_flags(ingredients: list[dict[str, Any]]) -> int:
    """Clear impossible OR-merge pollution (fish≠dairy, egg≠dairy, fish≠sesame)."""
    fixed = 0
    for row in ingredients:
        canon = _norm(row.get("canonical_name") or "")
        species = str(row.get("animal_species") or "").lower()
        is_fish = bool(row.get("fish_source")) or species == "fish" or canon == "fish"
        is_shellfish = (
            bool(row.get("shellfish_source"))
            or species == "shellfish"
            or canon in {
                "shrimp", "crab", "lobster", "clam", "oyster", "mussel",
                "scallop", "prawn", "clams", "oysters", "mussels", "scallops",
            }
        )
        is_egg = bool(row.get("egg_source")) and (
            canon in ("egg", "eggs") or species in ("bird", "chicken", "hen")
        )
        changed = False
        if is_fish or is_shellfish:
            for flag in ("dairy_source", "egg_source", "sesame_source", "plant_origin"):
                if row.get(flag):
                    row[flag] = False
                    changed = True
            if not row.get("animal_origin"):
                row["animal_origin"] = True
                changed = True
        if is_egg and row.get("dairy_source"):
            row["dairy_source"] = False
            changed = True
        if changed:
            fixed += 1
    return fixed


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
            "fish_source", "peanut_source", "tree_nut_source", "shellfish_source",
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
    nin = load_nin_commodities()
    ifct = load_layer1_regional_foods(_LAYER1_IFCT, source="ifct")
    foodex = load_layer1_regional_foods(_LAYER1_FOODEX2, source="foodex2")
    regional_seeds = load_regional_target_seeds()
    stats_usda = merge_into_ontology(ingredients, usda)
    stats_seed = merge_into_ontology(ingredients, seed)
    stats_nin = merge_into_ontology(ingredients, nin)
    stats_ifct = merge_into_ontology(ingredients, ifct)
    stats_foodex = merge_into_ontology(ingredients, foodex)
    stats_regional = merge_into_ontology(ingredients, regional_seeds)
    alias_added = apply_variant_aliases_as_row_aliases(ingredients)
    scrubbed = _scrub_compound_never_firm(ingredients)
    identity_scrubbed = _scrub_contradictory_identity_flags(ingredients)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "before_count": before,
        "after_count": len(ingredients),
        "usda_commodities_extracted": len(usda),
        "grocery_seed_count": len(seed),
        "nin_count": len(nin),
        "ifct_count": len(ifct),
        "foodex2_count": len(foodex),
        "regional_seed_count": len(regional_seeds),
        "variant_aliases_attached": alias_added,
        "compound_rows_scrubbed": scrubbed,
        "identity_flags_scrubbed": identity_scrubbed,
        "usda_merge": stats_usda,
        "seed_merge": stats_seed,
        "nin_merge": stats_nin,
        "ifct_merge": stats_ifct,
        "foodex2_merge": stats_foodex,
        "regional_merge": stats_regional,
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
