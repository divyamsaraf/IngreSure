"""Source registry for bulk ingestion (design §9).

Each source declares a *canonical name* (so dump-file labels like
``open_food_facts`` / ``usda_fdc`` line up with the trust tiers in
``reconcile._SOURCE_TIER``) and a *default knowledge_state* — the state a freshly
ingested row starts in. Low-trust crowd sources land as ``DISCOVERED`` so they
cannot drive a verdict until promoted; nothing bulk-loaded is ever ``VERIFIED``
except the e-number catalog path (LOCKED via dedicated adapter).
"""

# dump label -> canonical source key (must match reconcile._SOURCE_TIER keys)
_CANONICAL = {
    "open_food_facts": "openfoodfacts",
    "off": "openfoodfacts",
    "usda_fdc": "usda",
    "fda_gras": "fda",
    "e_number_catalog": "e_number_catalog",
    "infoods_anfood": "infoods",
    "anfood": "infoods",
    "ontology": "ontology",
    "system": "ontology",
}

# canonical source -> default knowledge_state for newly ingested rows
_DEFAULT_STATE = {
    "regulatory": "AUTO_CLASSIFIED",
    "fssai": "AUTO_CLASSIFIED",
    "fda": "AUTO_CLASSIFIED",
    "usda": "AUTO_CLASSIFIED",
    "ontology": "AUTO_CLASSIFIED",
    "nin": "AUTO_CLASSIFIED",
    "ifct": "AUTO_CLASSIFIED",
    "e_number_catalog": "LOCKED",
    "chebi": "DISCOVERED",
    "wikidata": "DISCOVERED",
    "openfoodfacts": "DISCOVERED",
    "foodex2": "DISCOVERED",
    "pubchem": "DISCOVERED",
    "produce_catalog": "AUTO_CLASSIFIED",
    # Item 1.2 check-in (2026-09-22): more conservative than produce —
    # DISCOVERED can still FAIL on positive animal/allergen flags (Item 34),
    # but cannot assert firm SAFE until promoted.
    "animal_catalog": "DISCOVERED",
    # Item 11: FAO/INFOODS AnFooD2.0 composition table (sheet-inferred flags).
    # Explicit check-in: AUTO_CLASSIFIED / tier 3 — same class as IFCT/USDA,
    # not inherited from produce or animal_catalog.
    "infoods": "AUTO_CLASSIFIED",
    # Item 18: single-name API lookups by the enrichment worker — unreviewed,
    # never firm-SAFE until promoted (positive hazard flags still FAIL).
    "enrichment_api": "DISCOVERED",
}


def canonical_source(name: str) -> str:
    key = (name or "").strip().lower()
    return _CANONICAL.get(key, key)


def default_knowledge_state(canonical: str) -> str:
    # Unknown sources get the most conservative state.
    return _DEFAULT_STATE.get(canonical, "UNCLASSIFIED")
