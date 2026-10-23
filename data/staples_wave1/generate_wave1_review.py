#!/usr/bin/env python3
"""Offline Wave 1 staple review CSVs (GLOBAL / IN / US).

Spec: docs/l5_staples_spec.md
Does not ingest, does not write ontology/DB/Supabase, does not touch evaluate.
LLM does not set verified / class_trusted / knowledge_state / asserted_flags as
truth: knowledge_state comes from sources.py + license_check; asserted_flags
are true-only from source columns and derive_identity_flags.
"""
from __future__ import annotations

import csv
import json
import random
import re
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
sys.path.insert(0, str(BACKEND))

from core.knowledge.ike2.commodity_head import simple_commodity_head  # noqa: E402
from core.knowledge.ike2.etl.license_check import license_check  # noqa: E402
from core.knowledge.ike2.etl.sources import (  # noqa: E402
    canonical_source,
    default_knowledge_state,
)
from core.knowledge.ike2.flag_derive import derive_identity_flags  # noqa: E402
from core.knowledge.ike2.rules import RULE_SEED  # noqa: E402
from core.normalization.normalizer import normalize_ingredient_key  # noqa: E402

OUT = Path(__file__).resolve().parent
STAPLE_NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://ingresure.local/l5-staple")
GENERATED_AT = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
AUDIT_SEED = 5
BATCH_SIZE = 200
AUDIT_SIZE = 300

FLAG_COLUMNS = [
    "peanut_source",
    "tree_nut_source",
    "soy_source",
    "sesame_source",
    "fish_source",
    "shellfish_source",
    "mustard_source",
    "lupin_source",
    "celery_source",
    "onion_source",
    "garlic_source",
    "gluten_source",
    "dairy_source",
    "egg_source",
    "sulphite_source",
    "animal_origin",
    "plant_origin",
    "synthetic",
    "root_vegetable",
    "fungal",
    "fermented",
    "insect_derived",
    "bee_product",
    "enzyme_animal_source",
    "enzyme_microbial_source",
]
HAZARD_AUDIT_FLAGS = [
    "peanut_source",
    "tree_nut_source",
    "soy_source",
    "sesame_source",
    "fish_source",
    "shellfish_source",
    "gluten_source",
    "dairy_source",
    "egg_source",
    "sulphite_source",
    "insect_derived",
    "bee_product",
    "root_vegetable",
    "onion_source",
    "garlic_source",
    "fungal",
    "animal_origin",
]
CATEGORIES = [
    "vegetables",
    "fruits",
    "herbs/spices",
    "grains/flours",
    "pulses",
    "nuts/seeds",
    "oils",
    "sweeteners",
    "dairy",
    "eggs",
    "meat",
    "fish/seafood",
    "fungi",
    "beverages",
    "common additives",
]
SOURCE_RANK = {
    "produce_catalog": 10,
    "animal_catalog": 9,
    "infoods": 8,
    "nin": 7,
    "ifct": 6,
    "e_number_catalog": 6,
    "usda": 5,
    "fda": 4,
    "india_catalog": 3,
    "regional_names": 2,
    "grocery_seed": 1,
}
LICENSE_SPDX = {
    "produce_catalog": "CC0-1.0",
    "animal_catalog": "CC0-1.0",
    "infoods": "CC-BY-4.0",
}
SOURCE_URL = {
    "produce_catalog": "backend/core/knowledge/ike2/etl/adapters/seeds/produce_catalog_seed.json",
    "animal_catalog": "backend/core/knowledge/ike2/etl/adapters/seeds/animal_catalog_seed.json",
    "infoods": "https://www.fao.org/infoods/infoods/tables-and-databases/en/",
    "usda": "https://fdc.nal.usda.gov/",
    "fda": "https://www.fda.gov/food/generally-recognized-safe-gras",
    "nin": "data/layer1_nin.json",
    "ifct": "data/layer1_ifct.json",
    "e_number_catalog": "data/layer1_e_numbers.json",
    "india_catalog": "backend/data/india_ingredients_catalog.json",
    "regional_names": "data/regional_ingredient_names.json",
    "grocery_seed": "data/commodity_seed_lists/expanded_grocery.txt",
}
USDA_KEEP_CATS = {
    "Vegetables and Vegetable Products": "vegetables",
    "Fruits and Fruit Juices": "fruits",
    "Dairy and Egg Products": "dairy",
    "Legumes and Legume Products": "pulses",
    "Finfish and Shellfish Products": "fish/seafood",
    "Cereal Grains and Pasta": "grains/flours",
    "Fats and Oils": "oils",
    "Nut and Seed Products": "nuts/seeds",
    "Spices and Herbs": "herbs/spices",
    "Poultry Products": "meat",
    "Pork Products": "meat",
    "Beef Products": "meat",
    "Lamb, Veal, and Game Products": "meat",
    "Beverages": "beverages",
    "Sweets": "sweeteners",
}
UMBRELLA = {
    "spices",
    "spice",
    "vegetable oil",
    "natural flavors",
    "natural flavour",
    "natural flavor",
    "artificial flavors",
    "artificial flavour",
    "artificial flavor",
    "seasoning",
    "mixed spices",
    "oil",
    "flavor",
    "flavour",
    "flavors",
    "flavours",
}
SKIP_NAME_RE = re.compile(
    r"\b(babyfood|baby food|restaurant|industrial|fast food|applebee|"
    r"separable|infant|formula|gravy|soup|entree|entrée|nugget|"
    r"hot dog|hotdog|sausage|lunch meat|luncheon)\b",
    re.I,
)
FORM_WORDS = frozenset({
    "raw", "fresh", "frozen", "canned", "cooked", "dried", "dehydrated",
    "unprepared", "boiled", "steamed", "unsalted", "salted", "peeled",
    "unpeeled", "ground", "sliced", "chopped", "condensed", "evaporated",
    "liquid", "solid", "pasteurized", "cultured", "sweetened", "unsweetened",
    "roasted", "toasted", "blanched", "hulled", "shelled", "unshelled",
    "dry", "wet", "pickled", "smoked", "grilled", "baked", "fried",
    "mature", "seeds", "seed", "unprocessed", "processed", "prepared",
    "unfortified", "fortified", "enriched", "refined", "unrefined",
    "whole",
})
HAZARD_TRUE_WINS = frozenset({
    "peanut_source", "tree_nut_source", "soy_source", "sesame_source",
    "fish_source", "shellfish_source", "mustard_source", "lupin_source",
    "celery_source", "onion_source", "garlic_source", "gluten_source",
    "dairy_source", "egg_source", "sulphite_source", "animal_origin",
    "root_vegetable", "fungal", "insect_derived", "bee_product",
    "enzyme_animal_source",
})
BINOMIAL_RE = re.compile(
    r"^[A-Z][a-z]{2,} (?:[a-z]{3,}|× [a-z]{3,})(?: (?:subsp|var)\.? [a-z]+)?$"
)
JUNK_ALIAS_RE = re.compile(
    r"^(IFCT:|INFOODS:|NDB |GRN |Place of|Crateva$)",
    re.I,
)

ROOT_VEGETABLE = frozenset({
    "potato", "sweet potato", "yam", "taro", "taro root", "cassava", "yuca",
    "carrot", "beet", "beetroot", "radish", "daikon", "turnip", "rutabaga",
    "parsnip", "jicama", "lotus root", "sunchoke", "jerusalem artichoke",
    "horseradish", "ginger", "turmeric", "galangal", "onion", "garlic",
    "shallot", "elephant foot yam", "arbi", "arvi", "suran", "celeriac",
    "celery root", "water chestnut", "asafoetida", "hing", "heeng",
    "beets", "carrots", "onions", "potatoes", "radishes", "parsnips",
    "turnips", "yams", "sunchokes", "tigernuts", "tiger nuts",
})
ONION_SOURCE = frozenset({
    "onion", "onions", "shallot", "shallots", "leek", "leeks", "scallion",
    "scallions", "spring onion", "chives", "onion powder", "pyaz",
})
GARLIC_SOURCE = frozenset({
    "garlic", "garlic clove", "garlic powder", "lahsun",
})
FUNGAL = frozenset({
    "mushroom", "mushrooms", "yeast", "nutritional yeast", "baker's yeast",
    "brewers yeast", "brewer's yeast", "koji", "tempeh", "mycoprotein",
    "chanterelles", "morels", "enoki mushrooms", "cremini mushrooms",
    "portobello mushrooms", "shiitake mushrooms", "oyster mushrooms",
    "porcini mushrooms", "black trumpets", "morel mushrooms",
})
FERMENTED = frozenset({
    "yogurt", "yoghurt", "dahi", "kefir", "lassi", "cheese", "vinegar",
    "wine", "beer", "cider", "tempeh", "miso", "kimchi", "sauerkraut",
    "idli", "dosa", "dhokla", "sourdough", "kombucha", "soy sauce",
    "apple cider vinegar", "balsamic vinegar", "rice vinegar", "malt vinegar",
    "red wine vinegar", "white wine vinegar", "sherry vinegar",
})
ALCOHOL_INGREDIENT = frozenset({
    "wine", "beer", "rum", "whiskey", "whisky", "vodka", "brandy", "cider",
    "sake", "soju", "sherry", "vermouth", "red wine", "white wine",
})
ALCOHOL_PROCESS = frozenset({
    "vinegar", "apple cider vinegar", "balsamic vinegar", "rice vinegar",
    "malt vinegar", "red wine vinegar", "white wine vinegar", "sherry vinegar",
    "champagne vinegar", "chinkiang vinegar",
})
COMMON_ADDITIVES = frozenset({
    "salt", "sea salt", "kosher salt", "table salt", "baking soda",
    "baking powder", "citric acid", "pectin", "lecithin", "vanilla",
    "vanilla extract", "cream of tartar", "msg", "monosodium glutamate",
})
SWEET_WORDS = (
    "sugar", "honey", "jaggery", "syrup", "molasses", "stevia", "agave",
    "erythritol", "xylitol",
)
GRAIN_WORDS = (
    "rice", "wheat", "oat", "oats", "barley", "rye", "millet", "quinoa",
    "corn", "maize", "sorghum", "buckwheat", "teff", "farro", "spelt",
    "atta", "maida", "flour", "semolina", "couscous", "bulgur", "polenta",
    "hominy", "masa", "cornmeal", "poha",
)
PULSE_WORDS = (
    "bean", "beans", "lentil", "lentils", "chickpea", "pea", "peas", "dal",
    "gram", "soybean", "edamame", "toor", "urad", "moong", "masoor", "chana",
    "rajma",
)
NUT_WORDS = (
    "almond", "walnut", "cashew", "pistachio", "pecan", "hazelnut",
    "macadamia", "peanut", "sesame", "chia", "flaxseed", "flax seed",
    "sunflower seed", "pumpkin seed", "kaju", "pine nut", "chestnut",
    "brazil nut", "sesame seed",
)
DAIRY_WORDS = (
    "milk", "cheese", "yogurt", "yoghurt", "cream", "butter", "ghee",
    "paneer", "dahi", "khoa", "lassi", "whey", "buttermilk", "ricotta",
    "cheddar", "mozzarella", "parmesan", "feta", "brie", "cottage",
)
MEAT_WORDS = (
    "beef", "pork", "chicken", "lamb", "goat", "turkey", "duck", "veal",
    "venison", "bacon", "ham", "mutton", "buffalo", "bison",
)
FISH_WORDS = (
    "fish", "salmon", "shrimp", "prawn", "tuna", "cod", "tilapia", "trout",
    "sardine", "mackerel", "anchovy", "crab", "lobster", "oyster", "mussel",
    "clam", "scallop", "squid", "octopus", "pomfret", "hilsa", "rohu",
)
FRUIT_WORDS = (
    "apple", "banana", "mango", "orange", "grape", "berry", "lemon", "lime",
    "papaya", "guava", "pineapple", "peach", "pear", "plum", "cherry",
    "watermelon", "melon", "pomegranate", "coconut", "date", "fig", "kiwi",
)
VEG_WORDS = (
    "spinach", "tomato", "gourd", "cabbage", "lettuce", "broccoli", "kale",
    "cucumber", "eggplant", "zucchini", "pepper", "okra", "cauliflower",
    "asparagus", "celery", "chard", "palak", "lauki", "karela",
)
HERB_WORDS = (
    "cumin", "turmeric", "coriander", "pepper", "chili", "chilli", "basil",
    "mint", "oregano", "thyme", "rosemary", "cinnamon", "clove", "cardamom",
    "fenugreek", "mustard seed", "asafoetida", "hing", "saffron", "paprika",
    "curry leaf", "curry leaves", "masala", "ajwain", "fennel", "dill",
)
BEV_WORDS = ("tea", "coffee", "lassi", "water", "juice")
EGG_WORDS = ("egg", "eggs")

CSV_FIELDS = [
    "staple_id",
    "canonical_name",
    "normalized_key",
    "region",
    "language",
    "category",
    "taxon",
    "local_names",
    "animal_species",
    "alcohol_role",
    "alcohol_content",
    *FLAG_COLUMNS,
    "asserted_flags",
    "primary_source",
    "primary_source_url",
    "license_spdx",
    "license_check",
    "knowledge_state",
    "class_trusted",
    "verified",
    "reviewer",
    "trust_timestamp",
    "uncertainty_flags",
    "completeness",
    "completeness_gaps",
    "disagreeing_signals",
    "implied_restrictions",
    "frequency",
    "queue_reason",
    "source_snippets",
    "sources",
    "generated_at",
    "notes",
]


def load_json(rel: str) -> Any:
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def title_name(name: str) -> str:
    raw = re.sub(r"\s+", " ", (name or "").strip())
    if not raw:
        return raw
    small = {"and", "or", "of", "the", "de", "da"}
    parts = []
    for i, w in enumerate(raw.split(" ")):
        if i > 0 and w.lower() in small:
            parts.append(w.lower())
        else:
            parts.append(w[:1].upper() + w[1:] if w else w)
    return " ".join(parts)


TAXON_SECOND_BLOCK = frozenset({
    "oil", "raw", "flour", "bean", "beans", "milk", "seed", "seeds", "leaves",
    "gum", "acid", "meat", "fish", "dal", "powder", "butter", "cheese", "sauce",
    "syrup", "mavu", "bele", "soppu", "keerai", "akulu", "paat", "shak", "sag",
    "whole", "leaf", "root", "roots", "nuts", "nut",
})
TAXON_FIRST_BLOCK = frozenset({
    "black", "white", "red", "green", "yellow", "sweet", "common", "indian",
    "french", "garden", "maida", "wheat", "rice", "corn", "sugar", "groundnut",
    "peanut", "palm", "olive", "mustard", "game", "sea", "fresh", "dry",
})


def is_binomial(text: str) -> bool:
    s = (text or "").strip().rstrip(".")
    if not s or JUNK_ALIAS_RE.search(s) or "," in s or ":" in s:
        return False
    if not BINOMIAL_RE.match(s):
        return False
    parts = s.split()
    if parts[0].lower() in TAXON_FIRST_BLOCK:
        return False
    if parts[1].lower().rstrip(".") in TAXON_SECOND_BLOCK:
        return False
    return True


def extract_taxon(aliases: list[str], canonical: str) -> str:
    items = list(aliases or [])
    for i, item in enumerate(items):
        marker = item.startswith("IFCT:") or item.startswith("INFOODS:") or item.startswith("NDB ")
        if marker and i:
            prev = items[i - 1].strip().rstrip(".")
            if is_binomial(prev):
                return prev
    for item in items:
        if is_binomial(item):
            return item.strip().rstrip(".")
    if is_binomial(canonical):
        return canonical.strip().rstrip(".")
    return ""


def flag_value(rec: dict, key: str):
    if key not in rec or rec[key] is None:
        return None
    v = rec[key]
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        if v.lower() in ("true", "1", "yes"):
            return True
        if v.lower() in ("false", "0", "no"):
            return False
    return None


def merge_flag(existing, incoming):
    if incoming is None:
        return existing
    if existing is None:
        return incoming
    if existing != incoming:
        return "DISAGREE"
    return existing


def strip_form(name: str) -> str:
    raw = re.sub(r"\([^)]*\)", " ", (name or "")).strip()
    raw = re.sub(r"\s+", " ", raw)
    if raw.count(",") == 1:
        left, right = raw.split(",", 1)
        rtoks = set(normalize_ingredient_key(right).split())
        if rtoks and rtoks <= FORM_WORDS:
            raw = left.strip()
        elif normalize_ingredient_key(right) in FORM_WORDS:
            raw = left.strip()
    n = normalize_ingredient_key(raw)
    words = n.split()
    while len(words) > 1 and words[-1] in FORM_WORDS:
        words.pop()
    return " ".join(words)


def commodity_key(name: str) -> str | None:
    raw = (name or "").strip()
    if not raw:
        return None
    if SKIP_NAME_RE.search(raw):
        return None
    if re.search(r"\b\d+\s*(yr|year|%|mg|iu)\b", raw, re.I):
        return None
    stripped = strip_form(raw)
    head = simple_commodity_head(raw) or simple_commodity_head(stripped)
    if head:
        return head
    n = stripped or normalize_ingredient_key(raw)
    if not n or n in UMBRELLA:
        return None
    if SKIP_NAME_RE.search(n):
        return None
    if " and " in n or " with " in n:
        return None
    words = n.split()
    if not (1 <= len(words) <= 4):
        return None
    if not (2 <= len(n) <= 40):
        return None
    return n


def split_csv_line(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for part in line.split(","):
            name = part.strip()
            if name:
                items.append(name)
    return items


def classify(name: str, food_category: str | None = None, aliases: list[str] | None = None) -> str:
    n = normalize_ingredient_key(name)
    blob = " ".join([n] + [normalize_ingredient_key(a) for a in (aliases or [])[:8]])
    if n in {"sago", "sabudana", "tapioca", "arrowroot", "arrowroot starch"}:
        return "grains/flours"
    if n in {"vanaspati", "dalda"} or n.endswith(" vanaspati"):
        return "oils"
    if n in {"pumpkin", "pumpkin squash"}:
        return "vegetables"
    if n.endswith(" seed") or n.endswith(" seeds") or n in {"chia", "flax", "sesame", "peanut"}:
        if any(w in n for w in ("mustard", "cumin", "fennel", "coriander", "ajwain", "fenugreek")):
            return "herbs/spices"
        return "nuts/seeds"
    if n in COMMON_ADDITIVES or n.endswith(" salt") or n.endswith(" gum") or n.endswith(" acid"):
        return "common additives"
    if n in FUNGAL or "mushroom" in n or n.endswith(" yeast") or n == "yeast":
        return "fungi"
    if n in EGG_WORDS or n.endswith(" egg") or n.endswith(" eggs"):
        return "eggs"
    if n in ALCOHOL_INGREDIENT or any(n.endswith(w) for w in (" wine", " beer")):
        return "beverages"
    if any(n.endswith(w) or n == w.strip() for w in (" oil",)) or n in {
        "ghee", "lard", "tallow", "olive oil", "mustard oil",
    }:
        if n == "ghee":
            return "oils"
        return "oils"
    if any(w in n for w in SWEET_WORDS) and "pea" not in n:
        return "sweeteners"
    if any(w in n.split() or w in n for w in DAIRY_WORDS) and "coconut" not in n and "almond milk" not in n:
        if "butter" in n and any(x in n for x in ("peanut", "almond", "cashew", "cocoa", "shea", "seed")):
            pass
        else:
            return "dairy"
    if any(w in n for w in FISH_WORDS):
        return "fish/seafood"
    if any(w in n for w in MEAT_WORDS):
        return "meat"
    if any(w in n for w in PULSE_WORDS):
        return "pulses"
    if any(w in n for w in NUT_WORDS):
        return "nuts/seeds"
    if any(w in n for w in GRAIN_WORDS):
        return "grains/flours"
    if any(w in n for w in HERB_WORDS) or "seed" in n and any(
        x in n for x in ("cumin", "mustard", "fennel", "coriander", "ajwain")
    ):
        return "herbs/spices"
    if any(w in n for w in BEV_WORDS):
        return "beverages"
    if any(w in blob for w in FRUIT_WORDS):
        return "fruits"
    if any(w in blob for w in VEG_WORDS) or n in ROOT_VEGETABLE:
        return "vegetables"
    mapped = USDA_KEEP_CATS.get(food_category or "")
    if mapped:
        if mapped == "dairy" and ("egg" in n and "eggplant" not in n):
            return "eggs"
        if mapped == "fruits" and "juice" in n:
            return "beverages"
        if mapped == "vegetables" and ("mushroom" in n):
            return "fungi"
        return mapped
    alias_l = " ".join(aliases or []).lower()
    if "green leafy" in alias_l or "vegetable" in alias_l:
        return "vegetables"
    if "fruit" in alias_l:
        return "fruits"
    if "spice" in alias_l or "condiment" in alias_l:
        return "herbs/spices"
    if "pulse" in alias_l or "legume" in alias_l:
        return "pulses"
    if "cereal" in alias_l or "grain" in alias_l:
        return "grains/flours"
    if "fish" in alias_l or "marine" in alias_l:
        return "fish/seafood"
    if "meat" in alias_l or "poultry" in alias_l:
        return "meat"
    if "milk" in alias_l or "dairy" in alias_l:
        return "dairy"
    return ""


def closed_identity_flags(key: str, display: str) -> dict[str, Any]:
    n = key or normalize_ingredient_key(display)
    out: dict[str, Any] = {}
    if n in ROOT_VEGETABLE or any(n.endswith(" " + r) for r in ("potato", "onion", "garlic", "carrot")):
        out["root_vegetable"] = True
        out["plant_origin"] = True
    if n in ONION_SOURCE or n.endswith(" onion"):
        out["onion_source"] = True
        out["root_vegetable"] = True
        out["plant_origin"] = True
    if n in GARLIC_SOURCE or n.endswith(" garlic"):
        out["garlic_source"] = True
        out["root_vegetable"] = True
        out["plant_origin"] = True
    if n in FUNGAL or "mushroom" in n or n.endswith(" yeast") or n == "yeast":
        out["fungal"] = True
    if n in FERMENTED or n.endswith(" vinegar") or n.endswith(" cheese") or n.endswith(" yogurt"):
        out["fermented"] = True
    if n in {"honey", "bee honey", "beeswax", "royal jelly", "propolis"}:
        out["bee_product"] = True
        out["insect_derived"] = True
        out["animal_origin"] = True
        out["animal_species"] = "insect"
    return out


def alcohol_fields(key: str) -> tuple[str, str | None, list[str]]:
    if key in ALCOHOL_INGREDIENT:
        return "ingredient", None, ["alcohol_content_unevaluated"]
    if key in ALCOHOL_PROCESS or key.endswith(" vinegar"):
        return "process", None, ["alcohol_role_process_residual_possible"]
    return "none", "0", []


def species_from(name: str, existing: str | None, flags: dict) -> str | None:
    n = normalize_ingredient_key(name)
    if flags.get("fish_source") or (existing or "").lower().startswith("fish"):
        return "fish"
    if flags.get("shellfish_source") or (existing or "").lower() in {
        "shellfish", "crustacean", "mollusk",
    }:
        return "shellfish"
    if flags.get("egg_source"):
        return "bird"
    if flags.get("insect_derived") or flags.get("bee_product"):
        return "insect"
    if any(w in n for w in ("chicken", "turkey", "duck", "goose", "quail")):
        return "bird"
    if any(w in n for w in ("pork", "pig", "bacon", "ham")):
        return "pig"
    if any(w in n for w in ("beef", "cow", "cattle", "buffalo")):
        return "cow"
    if "goat" in n:
        return "goat"
    if any(w in n for w in ("sheep", "lamb", "mutton")):
        return "sheep"
    if "deer" in n or "venison" in n:
        return "deer"
    if "lard" in n:
        return "pig"
    if "tallow" in n:
        return "cow"
    if flags.get("dairy_source") or any(
        w in n for w in ("milk", "cheese", "yogurt", "yoghurt", "ghee", "paneer", "dahi", "khoa", "butter", "cream", "lassi", "whey")
    ):
        if "coconut" not in n and "almond milk" not in n:
            return "cow"
    e = str(existing or "").strip().lower()
    if e and e not in {"mammal"}:
        return e
    if flags.get("animal_origin"):
        return None
    return None


def implied_restrictions(flags: dict[str, Any], species: str | None, alcohol_role: str) -> list[str]:
    hits: list[str] = []
    for rule in RULE_SEED:
        field = rule.get("field")
        cat = rule.get("category")
        if not cat:
            continue
        if field in flags and flags.get(field) is True:
            hits.append(cat)
            continue
        if field == "animal_species" and species:
            val = str(rule.get("value") or "")
            if rule.get("operator") == "eq" and species == val:
                hits.append(cat)
            elif rule.get("operator") == "in_list" and species in val:
                hits.append(cat)
        if field == "alcohol_role" and alcohol_role not in ("", "none"):
            hits.append(cat)
        if field == "alcohol_content" and alcohol_role in ("ingredient", "process"):
            hits.append(cat)
        if field == "meat_fish_derived" and (
            flags.get("animal_origin") and (flags.get("fish_source") or species in {"pig", "cow", "bird", "goat", "sheep", "fish"})
        ):
            hits.append(cat)
    return sorted(set(hits))


class Concept:
    def __init__(self, key: str):
        self.key = key
        self.staple_id = str(uuid.uuid5(STAPLE_NS, key))
        self.display = ""
        self.taxon = ""
        self.category = ""
        self.food_category = ""
        self.local_names: set[str] = set()
        self.aliases: set[str] = set()
        self.regions_hint: set[str] = set()
        self.sources: list[str] = []
        self.source_recs: list[tuple[str, dict]] = []
        self.flag_votes: dict[str, list[tuple[str, bool]]] = defaultdict(list)
        self.species_votes: list[str] = []
        self.uncertainty: set[str] = set()
        self.freq = 0
        self.e_locked = False
        self.e_url = ""

    def add_name(self, name: str) -> None:
        n = (name or "").strip()
        if n and normalize_ingredient_key(n) != self.key:
            self.local_names.add(n)
            self.aliases.add(n)

    def prefer_display(self, name: str, rank: int) -> None:
        stripped = strip_form(name)
        cand = title_name(stripped.replace("_", " ") if stripped else name)
        if not cand or "," in cand:
            return
        if not self.display:
            self.display = cand
            self._display_rank = rank
            return
        current = getattr(self, "_display_rank", 0)
        if rank > current:
            self.display = cand
            self._display_rank = rank
        elif rank == current and len(cand) < len(self.display):
            self.display = cand


def ingest_record(concepts: dict[str, Concept], rec: dict, source: str, default_region: str | None) -> None:
    source = canonical_source(source)
    name = rec.get("canonical_name") or ""
    key = commodity_key(name)
    if not key:
        return
    c = concepts.get(key)
    if c is None:
        c = Concept(key)
        concepts[key] = c
    rank = SOURCE_RANK.get(source, 0)
    c.prefer_display(name, rank)
    for a in rec.get("aliases") or []:
        if isinstance(a, str):
            c.add_name(a)
            ak = commodity_key(a)
            if ak == key:
                c.prefer_display(a, rank - 1)
    c.add_name(name)
    c.sources.append(source)
    c.source_recs.append((source, rec))
    if not c.taxon:
        c.taxon = extract_taxon(rec.get("aliases") or [], name)
    cat = classify(c.display or name, rec.get("food_category"), rec.get("aliases") or [])
    if cat and (not c.category or SOURCE_RANK.get(source, 0) >= 6):
        c.category = cat
    if rec.get("food_category"):
        c.food_category = rec["food_category"]
    regions = rec.get("regions") or ([rec["region"]] if rec.get("region") else [])
    for r in regions:
        ru = str(r).strip().upper()
        if ru in {"GLOBAL", "WORLD"}:
            c.regions_hint.add("GLOBAL")
        elif ru in {"IN", "INDIA"}:
            c.regions_hint.add("IN")
        elif ru in {"US", "USA", "UNITED STATES"}:
            c.regions_hint.add("US")
    if default_region:
        c.regions_hint.add(default_region)
    for col in FLAG_COLUMNS:
        v = flag_value(rec, col)
        if v is not None:
            c.flag_votes[col].append((source, v))
    sp = rec.get("animal_species")
    if sp:
        c.species_votes.append(str(sp))
    for u in rec.get("uncertainty_flags") or []:
        c.uncertainty.add(str(u))
    if source == "e_number_catalog" and rec.get("knowledge_state") == "LOCKED":
        c.e_locked = True
        c.category = "common additives"
        c.e_url = rec.get("primary_source_url") or SOURCE_URL["e_number_catalog"]
        if rec.get("e_code"):
            c.add_name(rec["e_code"])


def load_concepts() -> dict[str, Concept]:
    concepts: dict[str, Concept] = {}

    produce = load_json("backend/core/knowledge/ike2/etl/adapters/seeds/produce_catalog_seed.json")
    for rec in produce.get("ingredients") or []:
        ingest_record(concepts, rec, "produce_catalog", "GLOBAL")

    animal = load_json("backend/core/knowledge/ike2/etl/adapters/seeds/animal_catalog_seed.json")
    for rec in animal.get("ingredients") or []:
        ingest_record(concepts, rec, "animal_catalog", "GLOBAL")

    for rec in load_json("data/layer1_nin.json"):
        ingest_record(concepts, rec, "nin", "IN")
    for rec in load_json("data/layer1_ifct.json"):
        ingest_record(concepts, rec, "ifct", "IN")
    for rec in load_json("data/layer1_infoods_anfood.json"):
        ingest_record(concepts, rec, "infoods", None)
    for rec in load_json("data/layer1_usda_fdc.json"):
        if rec.get("food_category") not in USDA_KEEP_CATS:
            continue
        ingest_record(concepts, rec, "usda", "US")

    india = load_json("backend/data/india_ingredients_catalog.json")
    for rec in india.get("ingredients") or []:
        ingest_record(concepts, rec, "india_catalog", "IN")

    regional = load_json("data/regional_ingredient_names.json")
    for m in regional.get("mappings") or []:
        canon = m.get("canonical") or ""
        key = commodity_key(canon)
        if not key:
            continue
        rec = {"canonical_name": canon, "aliases": m.get("regional") or [], "regions": ["IN"]}
        ingest_record(concepts, rec, "regional_names", "IN")

    grocery = split_csv_line((REPO / "data/commodity_seed_lists/expanded_grocery.txt").read_text())
    grocery += split_csv_line((REPO / "data/commodity_seed_lists/identity_expand.txt").read_text())
    grocery += split_csv_line((REPO / "data/commodity_seed_lists/variant_recall.txt").read_text())
    for name in grocery:
        key = commodity_key(name)
        if not key:
            continue
        rec = {"canonical_name": name, "aliases": [], "regions": ["GLOBAL"]}
        ingest_record(concepts, rec, "grocery_seed", "GLOBAL")

    # FDA / FSSAI are signals only when the staple already exists.
    existing = set(concepts)
    for rec in load_json("data/layer1_fda_gras.json"):
        key = commodity_key(rec.get("canonical_name") or "")
        if key in existing:
            ingest_record(concepts, rec, "fda", "US")
    for rec in load_json("data/layer1_fssai.json"):
        key = commodity_key(rec.get("canonical_name") or "")
        if key in existing:
            ingest_record(concepts, rec, "fssai", "IN")

    # Common culinary additives from the existing LOCKED e-number catalog only.
    culinary = {
        "curcumin", "lecithin", "pectin", "ascorbic acid", "citric acid",
        "lactic acid", "tartaric acid", "acetic acid", "sodium bicarbonate",
        "potassium sorbate", "sorbic acid", "tocopherol", "beta carotene",
        "chlorophyll", "caramel", "locust bean gum", "guar gum", "xanthan gum",
        "agar", "carrageenan", "glycerol", "sorbitol",
    }
    for rec in load_json("data/layer1_e_numbers.json"):
        name = rec.get("canonical_name") or ""
        key = commodity_key(name)
        if key in culinary or name.lower() in culinary:
            rec = dict(rec)
            rec.setdefault("regions", ["GLOBAL"])
            ingest_record(concepts, rec, "e_number_catalog", "GLOBAL")

    return concepts


def frequency_table(concepts: dict[str, Concept]) -> Counter:
    freq: Counter = Counter()
    for key, c in concepts.items():
        freq[key] += 2 * len(set(c.sources))
        freq[key] += min(8, len(c.local_names))
        if "GLOBAL" in c.regions_hint:
            freq[key] += 2
        if "IN" in c.regions_hint:
            freq[key] += 2
        if "US" in c.regions_hint:
            freq[key] += 2
    corpus = (REPO / "backend/tests/fixtures/labels/corpus.jsonl").read_text(encoding="utf-8")
    corpus_l = corpus.lower()
    for key in concepts:
        token = key.replace("_", " ")
        if len(token) < 3:
            continue
        n = corpus_l.count(token)
        if n:
            freq[key] += 5 * n
    return freq


def pick_primary(sources: list[str]) -> str:
    ranked = sorted(set(sources), key=lambda s: SOURCE_RANK.get(s, 0), reverse=True)
    return ranked[0] if ranked else "grocery_seed"


def build_row(c: Concept, region: str, language: str, freq: int) -> dict[str, Any]:
    display = c.display or title_name(c.key.replace("_", " "))
    flags: dict[str, Any] = {k: None for k in FLAG_COLUMNS}
    disagreements: list[str] = []
    source_true: dict[str, set[str]] = defaultdict(set)
    source_false: dict[str, set[str]] = defaultdict(set)

    for src, rec in c.source_recs:
        for col in FLAG_COLUMNS:
            v = flag_value(rec, col)
            if v is True:
                source_true[col].add(src)
            elif v is False:
                source_false[col].add(src)

    for col in FLAG_COLUMNS:
        trues = source_true.get(col) or set()
        falses = source_false.get(col) or set()
        if trues and falses:
            disagreements.append(
                f"source_flag_conflict:{col}:true={'+'.join(sorted(trues))};false={'+'.join(sorted(falses))}"
            )
            if col in HAZARD_TRUE_WINS:
                flags[col] = True
            else:
                winner = pick_primary(list(trues | falses))
                flags[col] = winner in trues
        elif trues:
            flags[col] = True
        elif falses:
            flags[col] = False

    closed = closed_identity_flags(c.key, display)
    species_hint = c.species_votes[0] if c.species_votes else None
    derived = derive_identity_flags(display, {k: v for k, v in flags.items() if v is True}, animal_species=species_hint)
    derived.update({k: v for k, v in closed.items() if v is True})

    for col, val in derived.items():
        if col not in FLAG_COLUMNS or val is not True:
            continue
        if flags[col] is False:
            disagreements.append(f"derive_disagrees_source_false:{col}")
            flags[col] = True
        elif flags[col] is None:
            flags[col] = True
        # if already True, keep

    # Closed-class identity that derive does not cover.
    for col, val in closed.items():
        if col in FLAG_COLUMNS and val is True and flags[col] is not True:
            if flags[col] is False:
                disagreements.append(f"closed_class_disagrees_source_false:{col}")
            flags[col] = True

    species = species_from(display, species_hint, flags)
    alcohol_role, alcohol_content, alcohol_u = alcohol_fields(c.key)
    uncertainty = set(c.uncertainty)
    uncertainty.update(alcohol_u)

    if flags.get("animal_origin") and flags.get("plant_origin"):
        if not uncertainty:
            disagreements.append("dual_origin_missing_uncertainty")
            uncertainty.add("dual_origin")
    if flags.get("onion_source") or flags.get("garlic_source"):
        if flags.get("root_vegetable") is not True:
            disagreements.append("jain_root_consistency")
            flags["root_vegetable"] = True
    if flags.get("fungal") is True and flags.get("plant_origin") is True:
        uncertainty.add("fungal_not_forced_plant")
    if c.key in {"yeast", "idli", "dosa", "hing", "asafoetida", "tempeh"}:
        disagreements.append("jain_class_ambiguity")
    if alcohol_role == "process":
        disagreements.append("alcohol_role_unclear")

    primary = pick_primary(c.sources)
    spdx = LICENSE_SPDX.get(primary, "")
    url = c.e_url if primary == "e_number_catalog" and c.e_url else SOURCE_URL.get(primary, "")
    decision = license_check(primary, spdx or None)
    license_ok = bool(decision)

    if c.e_locked and primary == "e_number_catalog":
        state = "LOCKED"
    else:
        state = default_knowledge_state(primary)
        if state == "AUTO_CLASSIFIED" and not license_ok:
            state = "DISCOVERED"
        if primary in {"grocery_seed", "regional_names", "india_catalog"}:
            state = "DISCOVERED"
        if state not in {"DISCOVERED", "AUTO_CLASSIFIED", "LOCKED"}:
            state = "DISCOVERED"

    asserted = [col for col in FLAG_COLUMNS if flags.get(col) is True]
    # CHECK: insect/egg/dairy/fish/shellfish/enzyme_animal imply animal
    for imply_from in (
        "insect_derived",
        "egg_source",
        "dairy_source",
        "fish_source",
        "shellfish_source",
        "enzyme_animal_source",
    ):
        if flags.get(imply_from) is True and flags.get("animal_origin") is not True:
            disagreements.append(f"implication:{imply_from}_implies_animal")
            flags["animal_origin"] = True
            if "animal_origin" not in asserted:
                asserted.append("animal_origin")
    if flags.get("enzyme_animal_source") and flags.get("enzyme_microbial_source"):
        disagreements.append("enzyme_origin_both")

    if flags.get("animal_origin") is True and not species:
        disagreements.append("animal_missing_species")

    category = c.category or classify(display, c.food_category, list(c.aliases))
    if c.e_locked:
        category = "common additives"
    if not category:
        category = "vegetables" if flags.get("plant_origin") else ""
        if not category and flags.get("animal_origin"):
            if flags.get("fish_source") or flags.get("shellfish_source"):
                category = "fish/seafood"
            elif flags.get("egg_source"):
                category = "eggs"
            elif flags.get("dairy_source"):
                category = "dairy"
            else:
                category = "meat"
        if not category:
            category = "common additives" if c.key in COMMON_ADDITIVES else "vegetables"

    biological = category in {
        "vegetables", "fruits", "herbs/spices", "grains/flours", "pulses",
        "nuts/seeds", "dairy", "eggs", "meat", "fish/seafood", "fungi",
    }
    gaps: list[str] = []
    if not display:
        gaps.append("canonical_name")
    if not c.key:
        gaps.append("normalized_key")
    if not region:
        gaps.append("region")
    if not c.staple_id:
        gaps.append("staple_id")
    if not category:
        gaps.append("category")
    if biological and not c.taxon:
        gaps.append("taxon")
    for col in FLAG_COLUMNS:
        if flags.get(col) is None:
            gaps.append(f"flag:{col}")
    if flags.get("animal_origin") is True and not species:
        gaps.append("animal_species")
    if not license_ok:
        gaps.append(f"license:{decision.reason}")
    if state in {"VERIFIED", "LOCKED"} and not url:
        gaps.append("verified_requires_source")
    if flags.get("animal_origin") and flags.get("plant_origin") and not uncertainty:
        gaps.append("dual_origin_uncertainty")
    if alcohol_role == "none" and alcohol_content not in (None, "0", 0):
        gaps.append("alcohol_role_content")

    complete = not gaps
    local = sorted(
        {
            x
            for x in c.local_names
            if normalize_ingredient_key(x) != c.key and x.lower() != display.lower()
        },
        key=str.lower,
    )[:12]
    snippets = []
    for src, rec in c.source_recs[:4]:
        snippets.append(f"{src}:{rec.get('canonical_name')}")
    queue: list[str] = []
    if disagreements:
        queue.append("disagreeing_signal")
    if complete and state == "AUTO_CLASSIFIED" and category in {"vegetables", "fruits"} and primary == "produce_catalog":
        queue.append("owner_class_trusted_accept")
    elif not complete:
        queue.append("incomplete_record")
    if "jain_class_ambiguity" in disagreements:
        queue.append("jain_review")

    notes = "SPEC_ONLY_NO_INGEST; verified=false; class_trusted=false; owner_accept_later"
    row = {
        "staple_id": c.staple_id,
        "canonical_name": display,
        "normalized_key": c.key,
        "region": region,
        "language": language,
        "category": category,
        "taxon": c.taxon,
        "local_names": "|".join(local),
        "animal_species": species or "",
        "alcohol_role": alcohol_role,
        "alcohol_content": "" if alcohol_content is None else str(alcohol_content),
        "asserted_flags": "|".join(asserted),
        "primary_source": primary,
        "primary_source_url": url,
        "license_spdx": spdx,
        "license_check": "allow" if license_ok else f"deny:{decision.reason}",
        "knowledge_state": state,
        "class_trusted": "false",
        "verified": "false",
        "reviewer": "",
        "trust_timestamp": "",
        "uncertainty_flags": "|".join(sorted(uncertainty)),
        "completeness": "complete" if complete else "incomplete",
        "completeness_gaps": "|".join(gaps),
        "disagreeing_signals": "; ".join(disagreements),
        "implied_restrictions": "|".join(implied_restrictions(flags, species, alcohol_role)),
        "frequency": str(freq),
        "queue_reason": "|".join(queue) or "frequency_ranked_review",
        "source_snippets": " || ".join(snippets),
        "sources": "|".join(sorted(set(c.sources))),
        "generated_at": GENERATED_AT,
        "notes": notes,
    }
    for col in FLAG_COLUMNS:
        v = flags.get(col)
        row[col] = "" if v is None else ("true" if v else "false")
    return row


def region_membership(c: Concept) -> set[str]:
    regions = set(c.regions_hint)
    srcs = set(c.sources)
    if srcs & {"produce_catalog", "animal_catalog", "grocery_seed", "infoods", "e_number_catalog"}:
        regions.add("GLOBAL")
    if srcs & {"nin", "ifct", "india_catalog", "regional_names", "fssai"}:
        regions.add("IN")
    if srcs & {"usda", "fda", "infoods"}:
        regions.add("US")
    if "IN" in regions and "US" in regions:
        regions.add("GLOBAL")
    # Shared global core also overlays IN and US (same staple_id, extra region rows).
    if "GLOBAL" in regions:
        regions.update({"IN", "US"})
    regions.discard("AE")
    regions.discard("JP")
    return {r for r in regions if r in {"GLOBAL", "IN", "US"}}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda r: (-int(r["frequency"] or 0), r["normalized_key"], r["region"], r["language"]),
    )


def first_batch(all_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # One queue item per staple_id so owner accept is not tripled across overlays.
    seen: set[str] = set()
    picked: list[dict[str, Any]] = []

    def take(pred) -> None:
        for row in all_rows:
            if len(picked) >= BATCH_SIZE:
                return
            sid = row["staple_id"]
            if sid in seen:
                continue
            if pred(row):
                seen.add(sid)
                picked.append(row)

    take(lambda r: "disagreeing_signal" in r["queue_reason"] or r["disagreeing_signals"])
    take(lambda r: "owner_class_trusted_accept" in r["queue_reason"])
    take(lambda r: "jain_review" in r["queue_reason"])
    take(lambda r: r["completeness"] != "complete")
    take(lambda r: True)
    return picked[:BATCH_SIZE]


def audit_sample(all_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Prefer complete, then fewest gaps. Stratify across categories. Deterministic.
    rng = random.Random(AUDIT_SEED)
    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        by_cat[row["category"]].append(row)

    def score(row: dict[str, Any]) -> tuple:
        gaps = [g for g in (row["completeness_gaps"] or "").split("|") if g]
        complete = 0 if row["completeness"] == "complete" else 1
        missing_taxon = 0 if row.get("taxon") else 1
        region_pref = {"GLOBAL": 0, "IN": 1, "US": 2}.get(row["region"], 9)
        return (complete, missing_taxon, len(gaps), region_pref, -int(row["frequency"] or 0), row["normalized_key"])

    for cat in by_cat:
        by_cat[cat].sort(key=score)

    picked: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_row(row: dict[str, Any]) -> bool:
        sid = row["staple_id"]
        if sid in seen:
            return False
        seen.add(sid)
        picked.append(row)
        return True

    # At least one per required category (from the best available rows).
    for cat in CATEGORIES:
        pool = by_cat.get(cat) or []
        if pool:
            add_row(pool[0])

    # Fill remaining with round-robin from best remaining.
    idx = {cat: 1 if by_cat.get(cat) else 0 for cat in CATEGORIES}
    while len(picked) < AUDIT_SIZE:
        progressed = False
        order = list(CATEGORIES)
        rng.shuffle(order)
        for cat in order:
            pool = by_cat.get(cat) or []
            i = idx[cat]
            while i < len(pool) and not add_row(pool[i]):
                i += 1
            idx[cat] = i + 1
            if i < len(pool):
                progressed = True
            if len(picked) >= AUDIT_SIZE:
                break
        if not progressed:
            break
    return picked[:AUDIT_SIZE]


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    cats = Counter(r["category"] for r in rows)
    states = Counter(r["knowledge_state"] for r in rows)
    complete = sum(1 for r in rows if r["completeness"] == "complete")
    return {
        "rows": len(rows),
        "complete": complete,
        "incomplete": len(rows) - complete,
        "categories": dict(cats),
        "knowledge_state": dict(states),
        "unique_staples": len({r["staple_id"] for r in rows}),
        "disagreeing": sum(1 for r in rows if r["disagreeing_signals"]),
    }


def main() -> int:
    concepts = load_concepts()
    freq = frequency_table(concepts)
    for key, c in concepts.items():
        c.freq = int(freq.get(key, 0))

    rows_by_region: dict[str, list[dict[str, Any]]] = {"GLOBAL": [], "IN": [], "US": []}
    seen_triple: set[tuple[str, str, str]] = set()
    for c in concepts.values():
        if not c.key or c.key in UMBRELLA:
            continue
        for region in sorted(region_membership(c)):
            language = "en"
            triple = (region, language, c.key)
            if triple in seen_triple:
                continue
            seen_triple.add(triple)
            row = build_row(c, region, language, c.freq)
            rows_by_region[region].append(row)

    for region, rows in rows_by_region.items():
        rows_by_region[region] = sort_rows(rows)

    all_rows = sort_rows([r for rows in rows_by_region.values() for r in rows])
    batch = first_batch(all_rows)
    audit = audit_sample(all_rows)

    write_csv(OUT / "review_global.csv", rows_by_region["GLOBAL"])
    write_csv(OUT / "review_india.csv", rows_by_region["IN"])
    write_csv(OUT / "review_usa.csv", rows_by_region["US"])
    write_csv(OUT / "batch_001_owner_accept.csv", batch)
    write_csv(OUT / "audit_sample_300.csv", audit)

    report = {
        "generated_at": GENERATED_AT,
        "spec": "docs/l5_staples_spec.md",
        "ingest": False,
        "database_writes": False,
        "verified_always": False,
        "class_trusted_always": False,
        "batch_size": len(batch),
        "audit_size": len(audit),
        "audit_seed": AUDIT_SEED,
        "regions": {k: summary(v) for k, v in rows_by_region.items()},
        "batch": summary(batch),
        "audit": summary(audit),
        "notes": [
            "Wave 1 review artifacts only. Do not ingest. Do not apply to DB.",
            "asserted_flags are true-only from source columns + derive_identity_flags + closed Jain/root class.",
            "Unevaluated flags are empty (null), not invented falses.",
            "Audit CSV is an ungraded human sample; LLM must not grade it.",
            "Owner accept of batch_001 may later set reviewer/trust_timestamp/class_trusted.",
        ],
    }
    (OUT / "wave1_summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report["regions"][k]["rows"] for k in ("GLOBAL", "IN", "US")}, indent=2))
    print("batch", len(batch), "audit", len(audit))
    print("complete GLOBAL/IN/US", report["regions"]["GLOBAL"]["complete"], report["regions"]["IN"]["complete"], report["regions"]["US"]["complete"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
