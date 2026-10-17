from dataclasses import dataclass

# Source precedence: higher tier overrides lower. Human curation is authoritative.
# Keys must stay aligned with sources._DEFAULT_STATE / canonical_source().
_SOURCE_TIER = {
    "human": 5,
    "regulatory": 4,
    "fssai": 4,
    "fda": 4,
    "ontology": 4,
    "e_number_catalog": 4,  # LOCKED catalog path — must beat crowd sources
    "nin": 3,
    "ifct": 3,
    "usda": 3,
    "chebi": 3,
    "foodex2": 2,
    "pubchem": 2,
    "wikidata": 2,
    "openfoodfacts": 1,
    "produce_catalog": 3,  # curated CC0 plant commodities (Item 1.1)
    "animal_catalog": 2,  # DISCOVERED curated animal seed (Item 1.2); matches foodex2/pubchem
    "infoods": 3,  # FAO/INFOODS AnFooD composition (Item 11); sheet-inferred like IFCT/USDA
    "enrichment_api": 1,  # Item 18 worker single-name API lookups; lowest trust
}

# A protected group can only be changed by an equal-or-higher tier source.
_PROTECTED_STATES = ("VERIFIED", "LOCKED")


@dataclass
class ReconcileResult:
    merged_flags: dict
    knowledge_state: str
    needs_review: bool
    merged_asserted_flags: list


def _tier(source: str) -> int:
    return _SOURCE_TIER.get(source, 0)


def reconcile(
    existing,
    incoming: dict,
    incoming_source: str,
    incoming_asserted: list | None = None,
    incoming_knowledge_state: str | None = None,
) -> ReconcileResult:
    existing_state = getattr(existing, "knowledge_state", "UNCLASSIFIED")
    existing_source = getattr(existing, "source", "")
    protected = existing_state in _PROTECTED_STATES and _tier(incoming_source) < _tier(
        existing_source
    )
    can_assert_negative = _tier(incoming_source) >= _tier(existing_source)

    existing_asserted = set(getattr(existing, "asserted_flags", None) or [])
    incoming_asserted_set = set(incoming_asserted or [])
    # Start from existing asserts only; add incoming asserts when that decision is reflected.
    merged_asserted = set(existing_asserted)

    merged: dict = {}
    needs_review = False
    for flag, incoming_val in incoming.items():
        existing_val = bool(getattr(existing, flag, False))
        if protected:
            merged[flag] = existing_val  # higher-tier fact stands
            continue
        incoming_bool = bool(incoming_val)
        # Equal/higher-tier deliberate asserted-false may clear a sticky OR true
        # (Phase-1 FSSAI synthetic corrections, curated false-friends).
        if (
            flag in incoming_asserted_set
            and not incoming_bool
            and can_assert_negative
        ):
            new_val = False
        else:
            # Most-restrictive wins: a positive safety flag is never silently dropped.
            new_val = existing_val or incoming_bool
        merged[flag] = new_val
        # Curated clear of a positive is a correction, not a demotion trigger.
        curated_clear = (
            flag in incoming_asserted_set
            and not incoming_bool
            and can_assert_negative
            and existing_val
            and not new_val
        )
        if new_val != existing_val and flag in existing_asserted and not curated_clear:
            needs_review = True
        # Incoming asserted decision wins or ties when merged value equals incoming.
        if flag in incoming_asserted_set and new_val == incoming_bool:
            merged_asserted.add(flag)
        if curated_clear:
            merged_asserted.add(flag)

    # A conflicting change demotes the group out of any classified state.
    # Equal/higher-tier AUTO may re-promote a DISCOVERED row when no conflict remains
    # (Phase-1 / pollution demotion restore).
    if needs_review:
        knowledge_state = "DISCOVERED"
    elif (
        existing_state == "DISCOVERED"
        and incoming_knowledge_state == "AUTO_CLASSIFIED"
        and can_assert_negative
    ):
        knowledge_state = "AUTO_CLASSIFIED"
    else:
        knowledge_state = existing_state
    return ReconcileResult(
        merged,
        knowledge_state,
        needs_review,
        sorted(merged_asserted),
    )
