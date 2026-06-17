"""Source registry for bulk ingestion (design §9).

Each source declares a *canonical name* (so dump-file labels like
``open_food_facts`` / ``usda_fdc`` line up with the trust tiers in
``reconcile._SOURCE_TIER``) and a *default knowledge_state* — the state a freshly
ingested row starts in. Low-trust crowd sources land as ``DISCOVERED`` so they
cannot drive a verdict until promoted; nothing bulk-loaded is ever ``VERIFIED``.
"""

# dump label -> canonical source key (must match reconcile._SOURCE_TIER keys)
_CANONICAL = {
    "open_food_facts": "openfoodfacts",
    "off": "openfoodfacts",
    "usda_fdc": "usda",
    "fda_gras": "fda",
}

# canonical source -> default knowledge_state for newly ingested rows
_DEFAULT_STATE = {
    "regulatory": "AUTO_CLASSIFIED",
    "fssai": "AUTO_CLASSIFIED",
    "fda": "AUTO_CLASSIFIED",
    "usda": "AUTO_CLASSIFIED",
    "chebi": "DISCOVERED",
    "wikidata": "DISCOVERED",
    "openfoodfacts": "DISCOVERED",
}


def canonical_source(name: str) -> str:
    key = (name or "").strip().lower()
    return _CANONICAL.get(key, key)


def default_knowledge_state(canonical: str) -> str:
    # Unknown sources get the most conservative state.
    return _DEFAULT_STATE.get(canonical, "UNCLASSIFIED")
