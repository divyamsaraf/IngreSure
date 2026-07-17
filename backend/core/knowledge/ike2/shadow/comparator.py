"""Comparison between the legacy engine and IKE-2 (primary).

IKE-2 is the primary pipeline; legacy now runs only for comparison, and every
divergence is recorded in `ike2_shadow_diffs`. The gate we care about most is
a *false-safe regression*: primary (IKE-2) said SAFE but legacy said something
more severe. That is the one class of disagreement that could harm a user, so
it gets its own flag and must be zero before cutover.
"""

# External 3-tier verdicts, ordered by severity.
_SEVERITY = {"SAFE": 0, "UNCERTAIN": 1, "NOT_SAFE": 2}


def compare(legacy_verdict: str, ike2_verdict: str, raw_input: str) -> dict:
    """Diff a legacy verdict against the primary (IKE-2) verdict.

    Argument order: ``legacy_verdict`` first, ``ike2_verdict`` (primary)
    second. ``false_safe_regression`` is set when primary is SAFE while
    legacy is more severe -- the one disagreement that could harm a user.
    """
    match = legacy_verdict == ike2_verdict
    false_safe_regression = (
        _SEVERITY.get(legacy_verdict, 0) > _SEVERITY.get(ike2_verdict, 0)
        and ike2_verdict == "SAFE"
    )
    return {
        "raw_input": raw_input,
        "legacy_verdict": legacy_verdict,
        "ike2_verdict": ike2_verdict,
        "match": match,
        "false_safe_regression": false_safe_regression,
    }
