"""Python mirror of the database CHECK constraints (migration §5.1).

Rows are validated *before* merge so a single bad row is quarantined into
`stg_rejects` instead of aborting the whole batch (fail-closed ingestion).
Keep these predicates in sync with the SQL constraints of the same name.

Also applied to **merged** rows after reconcile (same invariant as Item 12).
"""

from core.knowledge.ike2.reviewed_negatives import illegal_asserted_falses

# Full-boolean dumps (ontology / dataclass / catalog materialization) used to be
# read as "every key deliberately decided," re-polluting asserted_flags twice in
# two days after the 1,698-row repair. More than this many false-valued names in
# asserted_flags is the pollution signature — quarantine at the choke point.
_MAX_ASSERTED_FALSE = 3


def _ok(row, flag):
    return bool(row.get(flag))


def _asserted_false_names(row) -> list[str]:
    return [f for f in (row.get("asserted_flags") or []) if not _ok(row, f)]


def mark_curated_asserted_negatives(row: dict) -> dict:
    """Sole production setter for the deliberate-negative escape hatch.

    Call from the stem-triage inject path only (``bulk_inject --curated-asserted-negatives``).
    Relaxes the ``>3`` backstop only; each false must still be on the
    reviewed-negatives registry.
    """
    out = dict(row)
    out["curated_asserted_negatives"] = True
    return out


def _asserted_false_registry_ok(row) -> bool:
    """Every asserted false must be on the reviewed-negatives registry."""
    return not illegal_asserted_falses(row)


def _asserted_false_pollution_ok(row) -> bool:
    """``>3`` asserted-false backstop (registry checked separately).

    Escape hatch ``curated_asserted_negatives=True`` relaxes only this count.
    """
    if row.get("curated_asserted_negatives"):
        return True
    return len(_asserted_false_names(row)) <= _MAX_ASSERTED_FALSE


# (constraint_name, predicate) — predicate returns True when the row is VALID.
_CHECKS = [
    ("insect_implies_animal", lambda r: not _ok(r, "insect_derived") or _ok(r, "animal_origin")),
    ("egg_implies_animal", lambda r: not _ok(r, "egg_source") or _ok(r, "animal_origin")),
    ("dairy_implies_animal", lambda r: not _ok(r, "dairy_source") or _ok(r, "animal_origin")),
    ("fish_implies_animal", lambda r: not _ok(r, "fish_source") or _ok(r, "animal_origin")),
    ("shellfish_implies_animal", lambda r: not _ok(r, "shellfish_source") or _ok(r, "animal_origin")),
    (
        "enzyme_animal_implies_animal",
        lambda r: not _ok(r, "enzyme_animal_source") or _ok(r, "animal_origin"),
    ),
    (
        "enzyme_origin_not_both",
        lambda r: not (_ok(r, "enzyme_animal_source") and _ok(r, "enzyme_microbial_source")),
    ),
    (
        "verified_requires_source",
        lambda r: r.get("knowledge_state") not in ("VERIFIED", "LOCKED")
        or r.get("primary_source_url") is not None,
    ),
    # Item 1 Prompt 2: only the e-number catalog adapter may mint LOCKED/VERIFIED
    # via bulk. Hard-reject (quarantine) — never silently downgrade.
    (
        "bulk_locked_verified_requires_e_number_catalog",
        lambda r: r.get("knowledge_state") not in ("VERIFIED", "LOCKED")
        or (r.get("classification_method") or "") == "bulk:e_number_catalog",
    ),
    (
        "dual_origin_requires_uncertainty",
        lambda r: not (_ok(r, "animal_origin") and _ok(r, "plant_origin"))
        or bool(r.get("uncertainty_flags")),
    ),
    # Registry invariant: asserted false legal only if (name, flag) reviewed.
    (
        "asserted_flags_unreviewed_negative",
        _asserted_false_registry_ok,
    ),
    # Count backstop (ghee-class slips past registry if keys were registered).
    (
        "asserted_flags_false_pollution",
        _asserted_false_pollution_ok,
    ),
]


def merged_row_for_validate(existing: dict, result) -> dict:
    """Build a validate-shaped row from reconcile output + existing identity."""
    out = dict(existing)
    out.update(result.merged_flags)
    out["asserted_flags"] = list(result.merged_asserted_flags)
    out["knowledge_state"] = result.knowledge_state
    return out


def validate_rows(rows):
    """Split rows into (ok, rejects). Each reject carries `violated_constraint`."""
    ok = []
    rejects = []
    for row in rows:
        violated = next((name for name, pred in _CHECKS if not pred(row)), None)
        if violated:
            rejects.append({**row, "violated_constraint": violated})
        else:
            ok.append(row)
    return ok, rejects
