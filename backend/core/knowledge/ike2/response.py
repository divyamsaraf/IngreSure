from core.knowledge.ike2.verdict import Verdict, to_external

SCHEMA_VERSION = "ike2.v1"

# Single mapping from a profile restriction to the flag that triggers it.
# Shared by compliance and the response audit so the two never disagree.
_RESTRICTION_FLAG = {
    "vegan": "animal_origin",
    "vegetarian": "animal_origin",
    "jain": "animal_origin",
    "peanut": "peanut_source",
    "dairy": "dairy_source",
    "alcohol": "alcohol_role",
}


def is_triggered(resolved, profile) -> bool:
    """True iff this ingredient trips at least one of the profile's restrictions.

    Single source of truth for "did this ingredient matter?" — prevents the
    Yam-class bug where a non-triggering ingredient is shown as flagged.
    """
    restrictions = getattr(profile, "restrictions", {}) or {}
    flags = getattr(resolved, "flags", {}) or {}
    for restriction in restrictions:
        flag = _RESTRICTION_FLAG.get(restriction)
        if flag and flags.get(flag):
            return True
    return False


def assemble(resolved, result, profile, mode: str = "b2c") -> dict:
    audit = [
        {
            "canonical_name": getattr(r, "canonical_name", "?"),
            "triggered": is_triggered(r, profile),
        }
        for r in resolved
    ]
    caution_reasons = list(getattr(result, "caution_reasons", []) or [])

    if mode == "b2b":
        # Strict headline: any contains/may_contain match is treated as a trigger.
        has_match = bool(result.matched_contains or result.matched_may_contain)
        headline = Verdict.FAIL if has_match else result.verdict
        return {
            "schema_version": SCHEMA_VERSION,
            "external_verdict": to_external(headline),
            "audit": audit,
            "caution_reasons": caution_reasons,
            "matched_contains": result.matched_contains,
            "matched_may_contain": result.matched_may_contain,
            "severity": dict(getattr(profile, "restrictions", {}) or {}),
            "verdict": int(result.verdict),
        }

    # b2c: keep the severity-aware verdict from compliance.
    return {
        "schema_version": SCHEMA_VERSION,
        "external_verdict": to_external(result.verdict),
        "audit": audit,
        "caution_reasons": caution_reasons,
    }
