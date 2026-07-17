"""Python mirror of the database CHECK constraints (migration §5.1).

Rows are validated *before* merge so a single bad row is quarantined into
`stg_rejects` instead of aborting the whole batch (fail-closed ingestion).
Keep these predicates in sync with the SQL constraints of the same name.
"""


def _ok(row, flag):
    return bool(row.get(flag))


# (constraint_name, predicate) — predicate returns True when the row is VALID.
_CHECKS = [
    ("insect_implies_animal", lambda r: not _ok(r, "insect_derived") or _ok(r, "animal_origin")),
    ("egg_implies_animal", lambda r: not _ok(r, "egg_source") or _ok(r, "animal_origin")),
    ("dairy_implies_animal", lambda r: not _ok(r, "dairy_source") or _ok(r, "animal_origin")),
    ("fish_implies_animal", lambda r: not _ok(r, "fish_source") or _ok(r, "animal_origin")),
    ("shellfish_implies_animal", lambda r: not _ok(r, "shellfish_source") or _ok(r, "animal_origin")),
    (
        "verified_requires_source",
        lambda r: r.get("knowledge_state") not in ("VERIFIED", "LOCKED")
        or r.get("primary_source_url") is not None,
    ),
    (
        "dual_origin_requires_uncertainty",
        lambda r: not (_ok(r, "animal_origin") and _ok(r, "plant_origin"))
        or bool(r.get("uncertainty_flags")),
    ),
]


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
