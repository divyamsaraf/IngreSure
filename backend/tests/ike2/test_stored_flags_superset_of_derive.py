"""CI invariant: stored hazard flags must contain every derive-true for that name.

Consumers that read stored rows without going through ``to_compliance_input``
under-report if derive adds a true the row lacks. Runtime compliance ORs derive;
this test keeps the static stores honest.
"""
from __future__ import annotations

from core.knowledge.ike2.flag_derive import derive_identity_flags
from core.knowledge.ike2.truth_anchor import all_anchors
from core.parsing.hazard_lexicon import HAZARD_CLASS_TO_FLAG

_HAZARD_FLAGS = frozenset(HAZARD_CLASS_TO_FLAG.values())


def test_l1_stored_flags_superset_of_derive():
    misses = []
    for key, fact in all_anchors().items():
        name = (fact.canonical_name or key or "").strip()
        if not name:
            continue
        stored = {k for k, v in (fact.flags or {}).items() if v is True and k in _HAZARD_FLAGS}
        derived = derive_identity_flags(name, dict(fact.flags or {}))
        for flag in _HAZARD_FLAGS:
            if derived.get(flag) is True and flag not in stored:
                misses.append((name, flag))
    # Cap the failure message; any miss fails the invariant.
    assert misses == [], (
        f"{len(misses)} L1 rows under-store derive flags (sample): {misses[:20]}"
    )
