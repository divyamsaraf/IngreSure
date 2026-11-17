"""CI gate: normalized-canonical collisions must agree on hazard bools.

L2 ``local_ontology._build_index`` is first-wins (setdefault). A weak record
listed before a strong one makes the weak flags live for every surface form
that shares the normalized canonical (live Jain false-SAFE on parsnip).

After the root-vegetable collision fix, a new hazard disagreement fails CI.
Reviewed exceptions are explicit below (species fill / xanthan fermented).
"""
from __future__ import annotations

from collections import defaultdict

import pytest

from core.knowledge.ike2.etl.adapt import BOOL_FLAGS, map_record
from core.knowledge.ike2.etl.load_ontology import load_ontology_records
from core.knowledge.ike2.etl.sources import canonical_source, default_knowledge_state

# Hazard bools for collision agreement: everything in BOOL_FLAGS except
# origin/attribute bits that are not Jain/allergen triggers in the same way.
# plant_origin / synthetic / fungal may still disagree under review; fungal is
# allowlisted for xanthan below via fermented focus — fungal stays in the check
# unless allowlisted.
_ATTRIBUTE = frozenset({"plant_origin", "synthetic"})
HAZARD_BOOLS = tuple(f for f in BOOL_FLAGS if f not in _ATTRIBUTE)

# Collision canonical_name (post map_record) → frozenset of fields allowed to
# disagree. Comment each entry; do not grow this without domain review.
_ALLOWLIST: dict[str, frozenset[str]] = {
    # Duplicate id rows: one has animal_species=chicken, one null.
    "l-cysteine": frozenset({"animal_species"}),
    # Singular vs plural shellfish rows: species null vs shellfish.
    "mussel": frozenset({"animal_species"}),
    "scallop": frozenset({"animal_species"}),
    # Duplicate id: fermented / fungal disagree; domain-review (Jain fermentation).
    "xanthan gum": frozenset({"fermented", "fungal"}),
}


def _collision_groups() -> dict[str, list[dict]]:
    src = canonical_source("ontology")
    ks = default_knowledge_state(src)
    by_cn: dict[str, list[dict]] = defaultdict(list)
    for raw in load_ontology_records():
        row, _ = map_record(raw, src, ks)
        cn = row.get("canonical_name")
        if not cn:
            continue
        by_cn[cn].append(
            {
                "id": raw.get("id"),
                "animal_species": row.get("animal_species"),
                **{f: bool(row.get(f)) for f in BOOL_FLAGS},
            }
        )
    return {cn: rows for cn, rows in by_cn.items() if len(rows) > 1}


def test_collision_hazard_bools_agree_except_allowlist():
    failures: list[str] = []
    for cn, members in sorted(_collision_groups().items()):
        allowed = _ALLOWLIST.get(cn, frozenset())
        for field in HAZARD_BOOLS:
            vals = {bool(m.get(field)) for m in members}
            if len(vals) <= 1:
                continue
            if field in allowed:
                continue
            ids = [(m.get("id"), m.get(field)) for m in members]
            failures.append(f"{cn!r} hazard {field} disagrees: {ids}")
        # animal_species treated like a hazard for agreement unless allowlisted
        if "animal_species" not in allowed:
            species = {(m.get("animal_species") or None) for m in members}
            if len(species) > 1:
                ids = [(m.get("id"), m.get("animal_species")) for m in members]
                failures.append(f"{cn!r} animal_species disagrees: {ids}")
    assert not failures, "collision hazard disagreements:\n" + "\n".join(failures)


def test_allowlist_only_covers_known_reviewed_collisions():
    """Prevent silent allowlist drift for collisions that no longer exist."""
    groups = _collision_groups()
    missing = sorted(set(_ALLOWLIST) - set(groups))
    assert not missing, f"allowlist entries with no collision: {missing}"
