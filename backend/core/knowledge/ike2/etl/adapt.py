"""Generic source-dump adapter: raw record -> (ike2 group row, aliases).

The curated dumps in ``data/*.json`` already speak the ike2 flag vocabulary, so
one generic mapper covers OpenFoodFacts / USDA / Wikidata / ChEBI. The mapping's
real job is the *unsafe* edges: it emits **only** real ``ike2_ingredient_groups``
columns (dropping ``derived_from``/``_source``/etc.), folds the legacy generic
``nut_source`` into the conservative ``tree_nut_source``, and normalizes the
``["Global"]`` region marker to ``None`` (GLOBAL).
"""

from core.normalization.normalizer import normalize_ingredient_key

# Boolean origin/allergen/diet columns on ike2_ingredient_groups (migration §5.1).
BOOL_FLAGS = (
    "animal_origin",
    "plant_origin",
    "synthetic",
    "fungal",
    "insect_derived",
    "egg_source",
    "dairy_source",
    "gluten_source",
    "soy_source",
    "sesame_source",
    "peanut_source",
    "tree_nut_source",
    "fish_source",
    "shellfish_source",
    "mustard_source",
    "celery_source",
    "lupin_source",
    "sulphite_source",
    "root_vegetable",
    "onion_source",
    "garlic_source",
    "fermented",
)


def _regions_to_values(regions):
    vals = []
    for r in regions or []:
        vals.append(None if (r is None or str(r).lower() == "global") else r)
    return vals or [None]


def map_record(raw: dict, canonical_source: str, default_state: str):
    row = {flag: bool(raw.get(flag, False)) for flag in BOOL_FLAGS}

    # Legacy generic `nut_source` -> conservative tree-nut allergen flag.
    if raw.get("nut_source"):
        row["tree_nut_source"] = True

    row["canonical_name"] = normalize_ingredient_key(raw.get("canonical_name", ""))
    row["animal_species"] = raw.get("animal_species")
    row["alcohol_content"] = raw.get("alcohol_content")
    row["uncertainty_flags"] = list(raw.get("uncertainty_flags") or [])
    row["knowledge_state"] = default_state
    row["primary_source_url"] = raw.get("primary_source_url") or raw.get("source_url")
    row["classification_method"] = f"bulk:{canonical_source}"

    regions = _regions_to_values(raw.get("regions"))
    aliases = []
    seen = set()
    for raw_alias in [raw.get("canonical_name", "")] + list(raw.get("aliases") or []):
        norm = normalize_ingredient_key(raw_alias)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        for region in regions:
            aliases.append((norm, region))

    return row, aliases
