from dataclasses import dataclass

# Source precedence: higher tier overrides lower. Human curation is authoritative.
_SOURCE_TIER = {
    "human": 5,
    "regulatory": 4,
    "fssai": 4,
    "fda": 4,
    "usda": 3,
    "chebi": 3,
    "wikidata": 2,
    "openfoodfacts": 1,
}

# A protected group can only be changed by an equal-or-higher tier source.
_PROTECTED_STATES = ("VERIFIED", "LOCKED")


@dataclass
class ReconcileResult:
    merged_flags: dict
    knowledge_state: str
    needs_review: bool


def _tier(source: str) -> int:
    return _SOURCE_TIER.get(source, 0)


def reconcile(existing, incoming: dict, incoming_source: str) -> ReconcileResult:
    existing_state = getattr(existing, "knowledge_state", "UNCLASSIFIED")
    existing_source = getattr(existing, "source", "")
    protected = existing_state in _PROTECTED_STATES and _tier(incoming_source) < _tier(
        existing_source
    )

    merged: dict = {}
    needs_review = False
    for flag, incoming_val in incoming.items():
        existing_val = bool(getattr(existing, flag, False))
        if protected:
            merged[flag] = existing_val  # higher-tier fact stands
            continue
        # Most-restrictive wins: a positive safety flag is never silently dropped.
        new_val = existing_val or bool(incoming_val)
        merged[flag] = new_val
        if new_val != existing_val:
            needs_review = True

    # A conflicting change demotes the group out of any classified state.
    knowledge_state = "DISCOVERED" if needs_review else existing_state
    return ReconcileResult(merged, knowledge_state, needs_review)
