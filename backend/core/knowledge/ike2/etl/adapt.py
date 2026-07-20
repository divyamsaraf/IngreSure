"""Generic source-dump adapter: raw record -> (ike2 group row, aliases).

The curated dumps in ``data/*.json`` already speak the ike2 flag vocabulary, so
one generic mapper covers OpenFoodFacts / USDA / Wikidata / ChEBI. The mapping's
real job is the *unsafe* edges: it emits **only** real ``ike2_ingredient_groups``
columns (dropping ``derived_from``/``_source``/etc.), parses the legacy free-text
``nut_source`` into the specific ``peanut_source``/``tree_nut_source`` flags
(unrecognized -> both, fail-closed), derives ``alcohol_role``, and normalizes the
``["Global"]`` region marker to ``None`` (GLOBAL).
"""

from core.normalization.normalizer import normalize_ingredient_key
from core.knowledge.ike2.flag_derive import derive_identity_flags

# Boolean origin/allergen/diet columns on ike2_ingredient_groups (migration §5.1).
BOOL_FLAGS = (
    "animal_origin",
    "plant_origin",
    "synthetic",
    "fungal",
    "insect_derived",
    "bee_product",
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


# Tree-nut keywords. Note: coconut is deliberately excluded — coconut allergy is
# medically distinct from tree-nut allergy and there is no coconut rule/flag, so it
# is handled as a recognized non-trigger below (see `_map_nut_source`).
_TREE_NUTS = (
    "tree_nut", "tree nut", "almond", "hazelnut", "filbert", "cashew", "walnut",
    "pecan", "pistachio", "macadamia", "brazil", "pine nut", "pine_nut", "pinenut",
    "chestnut", "praline",
)

# Recognized nut strings that map to NO allergen flag (distinct, non-cross-reactive,
# and unmatched by any peanut/tree_nut rule). Being recognized keeps them out of the
# unrecognized -> both-True fail-closed fallback.
_RECOGNIZED_NON_TRIGGER = ("coconut",)


def _map_nut_source(raw, row):
    """Legacy `nut_source` is free-text (e.g. "peanut butter, creamy", "almond
    paste") — NOT a boolean. Parse it into the specific allergen flags. Anything
    truthy but unrecognized over-flags BOTH (a false-Avoid is acceptable;
    under-flagging peanut is a catastrophic false-SAFE)."""
    nut = raw.get("nut_source")
    if not nut:
        return
    val = str(nut).strip().lower()
    if not val:
        return
    matched = False
    if "peanut" in val:
        row["peanut_source"] = True
        matched = True
    if any(k in val for k in _TREE_NUTS):
        # "chestnut" must not fire on "water chestnut"
        if "water chestnut" in val or "coconut" in val or "nutmeg" in val or "butternut" in val:
            if "peanut" in val:
                matched = True
            elif any(k in val for k in _TREE_NUTS if k != "chestnut"):
                row["tree_nut_source"] = True
                matched = True
            else:
                matched = True  # recognized non-trigger phrase
        else:
            row["tree_nut_source"] = True
            matched = True
    if any(k in val for k in _RECOGNIZED_NON_TRIGGER):
        # Recognized but maps to neither flag; suppress the both-True fallback.
        matched = True
    if not matched:
        row["peanut_source"] = True
        row["tree_nut_source"] = True


def _alcohol_role(raw):
    """Populate the §4B alcohol_role so alcohol-restricted users are protected.
    Explicit alcohol => deliberate ingredient (fail-closed strict); fermentation
    may leave residual trace alcohol; otherwise none."""
    ac = raw.get("alcohol_content")
    if ac is not None and ac > 0:
        return "ingredient"
    if raw.get("fermented"):
        return "fermentation_trace"
    return "none"


def map_record(raw: dict, canonical_source: str, default_state: str):
    row = {flag: bool(raw.get(flag, False)) for flag in BOOL_FLAGS}

    if row["insect_derived"]:
        row["animal_origin"] = True
    if row.get("bee_product"):
        row["animal_origin"] = True

    # Legacy free-text `nut_source` -> specific peanut / tree-nut allergen flags.
    _map_nut_source(raw, row)

    row["canonical_name"] = normalize_ingredient_key(raw.get("canonical_name", ""))
    row["animal_species"] = raw.get("animal_species")
    row["alcohol_content"] = raw.get("alcohol_content")
    row["alcohol_role"] = _alcohol_role(raw)
    row["uncertainty_flags"] = list(raw.get("uncertainty_flags") or [])
    # Curated "never firm-SAFE" caps must survive Tier-2/bulk ingestion.
    if raw.get("verdict_cap"):
        row["verdict_cap"] = raw.get("verdict_cap")
    # Prefer explicit curated knowledge_state when present; never invent LOCKED.
    raw_ks = (raw.get("knowledge_state") or "").strip()
    if raw_ks in (
        "UNKNOWN", "DISCOVERED", "AUTO_CLASSIFIED", "CLASSIFIED", "VERIFIED", "LOCKED",
    ):
        row["knowledge_state"] = raw_ks
    else:
        row["knowledge_state"] = default_state
    row["primary_source_url"] = raw.get("primary_source_url") or raw.get("source_url")
    row["classification_method"] = f"bulk:{canonical_source}"

    # Systemic allergen derivation from species + name (closes under-flagged seeds).
    derived = derive_identity_flags(
        row["canonical_name"],
        row,
        animal_species=row.get("animal_species"),
    )
    for flag in BOOL_FLAGS:
        if derived.get(flag):
            row[flag] = True
    if derived.get("animal_species") and not row.get("animal_species"):
        row["animal_species"] = derived["animal_species"]

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
